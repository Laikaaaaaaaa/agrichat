"""agrimind.py

AgriMind (AgriChat) - Hybrid NLP + KB + Safety Rules

Goals (practical MVP):
- Multi-label entity extraction (specie/season/disease/symptoms) directly from user question.
- Safe KB matching + rule engine to avoid hallucinating new info.
- Prompt generator (app-style: friendly Vietnamese + icons) to send to LLM later.
- CLI + REST API with caching.

Notes:
- Runs without heavy ML dependencies by default.
- Optional: Transformers / Torch can be plugged in later.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "dataset.json")


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass(frozen=True)
class KBEntry:
    id: str
    domain: str
    specie: str
    season: str
    disease: str
    symptoms: Tuple[str, ...]
    causes: Tuple[str, ...]
    advice: Tuple[str, ...]
    examples: Tuple[str, ...]
    safety_urgent: bool
    safety_notes: Tuple[str, ...]


def load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[KBEntry]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    entries: List[KBEntry] = []
    for item in raw:
        safety = item.get("safety") or {}
        entries.append(
            KBEntry(
                id=str(item.get("id") or ""),
                domain=str(item.get("domain") or "unknown"),
                specie=str(item.get("specie") or "").strip(),
                season=str(item.get("season") or "").strip(),
                disease=str(item.get("disease") or "").strip(),
                symptoms=tuple(item.get("symptoms") or []),
                causes=tuple(item.get("causes") or []),
                advice=tuple(item.get("advice") or []),
                examples=tuple(item.get("examples") or []),
                safety_urgent=bool(safety.get("urgent", False)),
                safety_notes=tuple(safety.get("notes") or []),
            )
        )

    # Basic validation
    bad = [e for e in entries if not e.specie or not e.season or not e.disease]
    if bad:
        raise ValueError(f"Dataset has {len(bad)} invalid entries missing specie/season/disease")
    return entries


def _build_lexicons(entries: List[KBEntry]) -> Dict[str, Any]:
    species = sorted({e.specie for e in entries})
    seasons = sorted({e.season for e in entries})
    diseases = sorted({e.disease for e in entries})

    all_symptoms: List[str] = []
    for e in entries:
        all_symptoms.extend(list(e.symptoms))
    symptoms = sorted({s for s in all_symptoms if s})

    # Simple aliases (expand as needed)
    season_aliases = {
        "mua": ["mua", "mua mua", "troi mua", "mua lon", "am uot"],
        "nang": ["nang", "troi nang", "kho", "kho han"],
        "bat_ky": ["bat ky", "quanh nam", "luc nao"],
    }

    specie_aliases = {
        "heo": ["heo", "lon"],
        "ga": ["ga", "ga ta", "ga cong nghiep"],
        "bo": ["bo", "bo sua", "bo thit"],
        "tom": ["tom", "tom the", "tom su"],
        "lua": ["lua", "ruong lua"],
        "ca chua": ["ca chua", "tomato"],
        "ot": ["ot", "ot hiem"],
        "xoai": ["xoai", "mango"],
        "cam": ["cam", "quyt", "citrus"],
    }

    return {
        "species": species,
        "seasons": seasons,
        "diseases": diseases,
        "symptoms": symptoms,
        "season_aliases": season_aliases,
        "specie_aliases": specie_aliases,
    }


def _find_first_match(text_norm: str, candidates: List[str]) -> Optional[str]:
    for cand in candidates:
        cand_norm = _normalize(cand)
        if cand_norm and re.search(rf"\b{re.escape(cand_norm)}\b", text_norm):
            return cand
    return None


def _extract_symptoms(text_norm: str, symptom_list: List[str]) -> List[str]:
    found: List[str] = []
    for s in symptom_list:
        s_norm = _normalize(s)
        if not s_norm:
            continue
        # allow partial match (symptoms are often phrases)
        if s_norm in text_norm:
            found.append(s)
    # de-dup preserving order
    dedup: List[str] = []
    seen = set()
    for s in found:
        key = _normalize(s)
        if key not in seen:
            seen.add(key)
            dedup.append(s)
    return dedup


def extract_entities(question: str, entries: List[KBEntry], lex: Dict[str, Any]) -> Dict[str, Any]:
    q_norm = _normalize(question)

    # 1) Specie (dictionary + aliases)
    specie: Optional[str] = None
    for canonical, aliases in lex.get("specie_aliases", {}).items():
        for alias in aliases:
            if _normalize(alias) and _normalize(alias) in q_norm:
                # map back to canonical specie label present in dataset when possible
                for s in lex["species"]:
                    if _normalize(s) == canonical:
                        specie = s
                        break
                specie = specie or canonical
                break
        if specie:
            break
    if not specie:
        specie = _find_first_match(q_norm, lex["species"])

    # 2) Season
    season: Optional[str] = None
    for canonical, aliases in lex.get("season_aliases", {}).items():
        for alias in aliases:
            if _normalize(alias) and _normalize(alias) in q_norm:
                for s in lex["seasons"]:
                    if _normalize(s) == canonical:
                        season = s
                        break
                season = season or canonical
                break
        if season:
            break
    if not season:
        season = _find_first_match(q_norm, [s for s in lex["seasons"] if s != "bat_ky"]) or None

    # 3) Disease
    disease = _find_first_match(q_norm, lex["diseases"])

    # 4) Symptoms
    symptoms_found = _extract_symptoms(q_norm, lex["symptoms"])

    return {
        "question": question,
        "specie": specie,
        "season": season,
        "disease": disease,
        "symptoms": symptoms_found,
    }


def _score_entry(extracted: Dict[str, Any], entry: KBEntry) -> float:
    score = 0.0

    if extracted.get("specie") and _normalize(extracted["specie"]) == _normalize(entry.specie):
        score += 3.0
    if extracted.get("season") and _normalize(extracted["season"]) == _normalize(entry.season):
        score += 2.0
    if extracted.get("disease") and _normalize(extracted["disease"]) == _normalize(entry.disease):
        score += 4.0

    ex_symptoms = extracted.get("symptoms") or []
    if ex_symptoms:
        entry_sym = {_normalize(s) for s in entry.symptoms}
        overlap = sum(1 for s in ex_symptoms if _normalize(s) in entry_sym)
        score += min(3.0, overlap * 1.0)

    # small bias toward urgent if user uses alarming words
    qn = _normalize(extracted.get("question") or "")
    if entry.safety_urgent and any(w in qn for w in ["chet", "kho tho", "ra mau", "soc", "ngat"]):
        score += 0.5
    return score


def match_kb(extracted: Dict[str, Any], entries: List[KBEntry]) -> Tuple[Optional[KBEntry], float]:
    best: Optional[KBEntry] = None
    best_score = -1.0
    for e in entries:
        s = _score_entry(extracted, e)
        if s > best_score:
            best = e
            best_score = s

    # Normalize to [0,1] with a simple cap (heuristic)
    confidence = max(0.0, min(1.0, best_score / 10.0))
    return best, confidence


def rule_engine(extracted: Dict[str, Any], entry: Optional[KBEntry], confidence: float) -> Dict[str, Any]:
    warnings: List[str] = []
    actions: List[str] = []
    allow_answer = True

    # If no KB match or too low confidence -> ask clarifying questions
    if not entry or confidence < 0.35:
        allow_answer = False
        actions.append("ask_clarify")
        warnings.append("Chưa đủ thông tin để kết luận. Cần hỏi thêm loài/mùa/triệu chứng cụ thể.")

    # Safety: urgent entries -> recommend contacting specialist
    if entry and entry.safety_urgent:
        warnings.append("Dấu hiệu có thể nghiêm trọng. Nên theo dõi sát và liên hệ chuyên gia/thú y/kỹ thuật địa phương nếu nặng.")

    # Never hallucinate: advice must come from KB
    return {
        "allow_answer": allow_answer,
        "warnings": warnings,
        "actions": actions,
    }


def suggest_next_question(extracted: Dict[str, Any], entry: Optional[KBEntry], confidence: float) -> str:
    # Rule-first (works now). LSTM can be added later.
    missing = []
    if not extracted.get("specie"):
        missing.append("loài/cây nuôi–trồng")
    if not extracted.get("season"):
        missing.append("mùa/thời tiết gần đây")
    if not extracted.get("symptoms"):
        missing.append("triệu chứng cụ thể")
    if missing:
        return f"Bạn cho mình xin thêm {', '.join(missing)} nhé?"

    if entry and confidence < 0.65:
        return "Bạn cho mình biết tình trạng kéo dài bao lâu và mức độ nặng/nhẹ (có sốt, bỏ ăn, chết rải rác không)?"
    return "Bạn muốn mình hướng dẫn phòng ngừa tái phát và cách theo dõi tiếp theo không?"


def _format_list(items: Tuple[str, ...] | List[str], bullet: str = "- ") -> str:
    return "\n".join(f"{bullet}{x}" for x in items if x)


def generate_prompt(question: str, extracted: Dict[str, Any], entry: Optional[KBEntry], confidence: float, rules: Dict[str, Any]) -> str:
    # This prompt is meant to be fed to a generative model later.
    # Keep it strict: use KB only, ask clarifying if uncertain.
    specie = extracted.get("specie") or "(chưa rõ)"
    season = extracted.get("season") or "(chưa rõ)"
    disease = extracted.get("disease") or "(chưa rõ)"
    symptoms = extracted.get("symptoms") or []

    kb_block = ""
    if entry:
        kb_block = (
            "\n📚 DỮ LIỆU THAM CHIẾU (Knowledge Base)\n"
            f"- Domain: {entry.domain}\n"
            f"- Loài/Cây: {entry.specie}\n"
            f"- Mùa: {entry.season}\n"
            f"- Vấn đề/Bệnh: {entry.disease}\n"
            "\n🔎 Triệu chứng thường gặp:\n"
            f"{_format_list(entry.symptoms)}\n"
            "\n🧩 Nguyên nhân có thể:\n"
            f"{_format_list(entry.causes)}\n"
            "\n✅ Khuyến nghị an toàn:\n"
            f"{_format_list(entry.advice)}\n"
        )

    warnings = rules.get("warnings") or []
    warning_block = ""
    if warnings:
        warning_block = "\n⚠️ LƯU Ý AN TOÀN\n" + "\n".join(f"- {w}" for w in warnings)

    # App-style: friendly, short paragraphs, icons, ask follow-up.
    next_q = suggest_next_question(extracted, entry, confidence)

    prompt = f"""
Bạn là AgriSense AI 🌱 — trợ lý nông nghiệp thân thiện.

YÊU CẦU TRẢ LỜI:
- Trả lời bằng tiếng Việt, thân thiện, dễ hiểu.
- Không bịa thông tin. Nếu thiếu dữ liệu thì hỏi lại cho rõ.
- Chỉ dùng thông tin trong KB phía dưới khi đưa khuyến nghị.
- Luôn nhắc an toàn khi có dấu hiệu nghiêm trọng.

👤 CÂU HỎI NGƯỜI DÙNG:
{question}

🧠 TRÍCH XUẤT TỪ CÂU HỎI (ước lượng):
- Loài/Cây: {specie}
- Mùa: {season}
- Bệnh/Vấn đề: {disease}
- Triệu chứng: {', '.join(symptoms) if symptoms else '(chưa rõ)'}
- Độ tin cậy khớp KB: {confidence:.2f}
{kb_block}
{warning_block}

✅ Hãy trả lời theo cấu trúc:
1) Nhận định ngắn gọn (1–2 câu)
2) Việc cần làm ngay (bullet)
3) Theo dõi thêm dấu hiệu nào
4) Câu hỏi tiếp theo để chẩn đoán chính xác hơn: {next_q}
""".strip()

    return prompt


@lru_cache(maxsize=1024)
def _cached_extract(question: str, dataset_path: str) -> Dict[str, Any]:
    entries = load_dataset(dataset_path)
    lex = _build_lexicons(entries)
    extracted = extract_entities(question, entries, lex)
    entry, confidence = match_kb(extracted, entries)
    rules = rule_engine(extracted, entry, confidence)
    return {
        "extracted": extracted,
        "matched": (entry.__dict__ if entry else None),
        "confidence": confidence,
        "rules": rules,
    }


@lru_cache(maxsize=512)
def _cached_prompt(question: str, dataset_path: str) -> str:
    result = _cached_extract(question, dataset_path)
    extracted = result["extracted"]
    entry_raw = result["matched"]
    entry = KBEntry(**entry_raw) if entry_raw else None
    confidence = float(result["confidence"])
    rules = result["rules"]
    return generate_prompt(question, extracted, entry, confidence, rules)


def cli_extract(args: argparse.Namespace) -> int:
    out = _cached_extract(args.text, args.dataset)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cli_prompt(args: argparse.Namespace) -> int:
    prompt = _cached_prompt(args.text, args.dataset)
    print(prompt)
    return 0


def cli_serve(args: argparse.Namespace) -> int:
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "agrimind", "ts": time.time()})

    @app.post("/agrimind/extract")
    def api_extract():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "text is required"}), 400
        return jsonify({"success": True, "result": _cached_extract(text, args.dataset)})

    @app.post("/agrimind/prompt")
    def api_prompt():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "text is required"}), 400
        return jsonify({"success": True, "prompt": _cached_prompt(text, args.dataset)})

    app.run(host=args.host, port=args.port, debug=False)
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AgriMind - entity extraction + KB + safety + prompt generator")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH, help="Path to dataset.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract entities + match KB")
    p_extract.add_argument("text", help="User question")
    p_extract.set_defaults(func=cli_extract)

    p_prompt = sub.add_parser("prompt", help="Generate LLM prompt (app-style)")
    p_prompt.add_argument("text", help="User question")
    p_prompt.set_defaults(func=cli_prompt)

    p_serve = sub.add_parser("serve", help="Run REST API (Flask)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8011)
    p_serve.set_defaults(func=cli_serve)

    return p


def main() -> int:
    # Windows consoles may default to legacy codepages; this avoids UnicodeEncodeError
    # when printing Vietnamese text.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = build_argparser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
