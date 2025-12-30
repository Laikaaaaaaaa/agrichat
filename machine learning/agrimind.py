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
import logging
import os
import pickle
import random
import re
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "dataset.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "agrimind_textclf.pkl")

# Optional: host the (potentially large) sklearn pickle on Hugging Face Hub.
# Recommended for Heroku: DO NOT bundle the model in the slug. Instead, download
# on-demand from Hugging Face and cache in /tmp.
#
# Env vars:
# - AGRIMIND_MODEL_SOURCE=auto|hf|local   (default: auto)
#     * auto: prefer HF if AGRIMIND_HF_REPO is set; else use local if exists
#     * hf: always use HF (ignore local file)
#     * local: only use local file (ignore HF)
# - AGRIMIND_HF_REPO=Coffee2307/agrimind-1
# - AGRIMIND_HF_FILENAME=agrimind_textclf.pkl
# - AGRIMIND_HF_REVISION=main (or a tag/commit)
# - AGRIMIND_HF_TOKEN=hf_... (optional; required for private repos)
#
# Note: even when "using HF", the file must still be downloaded to run locally.
# This code caches it in a writable directory so the download doesn't repeat every request.



LOGGER = logging.getLogger("agrimind")


def _get_cache_dir() -> str:
    # Heroku slug is read-only; /tmp is writable.
    env = os.environ.get("AGRIMIND_CACHE_DIR")
    if env and env.strip():
        return os.path.abspath(env)
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir and tmpdir.strip():
        return os.path.abspath(tmpdir)
    return os.path.abspath(tempfile.gettempdir())


def _download_file(url: str, dest_path: str, timeout_s: int = 60, headers: Optional[Dict[str, str]] = None) -> None:
    import requests

    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    tmp_path = dest_path + ".part"

    with requests.get(url, stream=True, timeout=timeout_s, headers=headers) as r:
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    os.replace(tmp_path, dest_path)


def _resolve_model_path(local_model_path: str) -> Optional[str]:
    """Return a usable local path for the sklearn pickle.

    Priority depends on AGRIMIND_MODEL_SOURCE:
    - local: local only
    - hf: HF only
    - auto: HF if configured, else local
    """

    source = (os.environ.get("AGRIMIND_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "hf", "local"}:
        source = "auto"

    repo = (os.environ.get("AGRIMIND_HF_REPO") or "").strip()
    use_hf = bool(repo) and source in {"auto", "hf"}
    use_local = source in {"auto", "local"}

    if use_hf:
        filename = (os.environ.get("AGRIMIND_HF_FILENAME") or "agrimind_textclf.pkl").strip()
        if not filename:
            return None

        revision = (os.environ.get("AGRIMIND_HF_REVISION") or "main").strip() or "main"

        cache_dir = os.path.join(_get_cache_dir(), "agrimind", "models", repo.replace("/", "__"), revision)
        cached_path = os.path.join(cache_dir, filename)
        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
            return cached_path

        token = (os.environ.get("AGRIMIND_HF_TOKEN") or "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else None

        # Hugging Face direct resolve URL.
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{filename}?download=true"
        try:
            LOGGER.warning("Downloading model from Hugging Face: %s -> %s", url, cached_path)
            _download_file(url, cached_path, headers=headers)
            return cached_path
        except Exception as e:
            LOGGER.warning("Failed to download model from HF (%s): %s", repo, e)
            if source == "hf":
                return None
            # fall back to local in auto mode

    if use_local and local_model_path and os.path.exists(local_model_path):
        return local_model_path

    return None


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # Dataset often uses underscores (e.g., 'dâu_tây'); users usually type spaces.
    # Normalize separators to improve matching.
    text = text.replace("_", " ")
    text = text.replace("/", " ")
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
    bad = [e for e in entries if not e.id or not e.specie or not e.season or not e.disease]
    if bad:
        raise ValueError(f"Dataset has {len(bad)} invalid entries missing id/specie/season/disease")

    # ID uniqueness matters for matching + ML labels
    seen: set[str] = set()
    dup: List[str] = []
    for e in entries:
        if e.id in seen:
            dup.append(e.id)
        seen.add(e.id)
    if dup:
        dup_preview = ", ".join(sorted(set(dup))[:20])
        raise ValueError(f"Dataset has duplicate ids ({len(set(dup))}): {dup_preview}")
    return entries


def _maybe_log_event(event: Dict[str, Any]) -> None:
    """Optional JSONL logging for monitoring.

    Enable by setting AGRIMIND_LOG_PATH to a file path.
    """

    log_path = os.environ.get("AGRIMIND_LOG_PATH")
    if not log_path:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Never break the app because logging fails.
        return


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
        # Note: "lợn" and "lớn" both normalize to "lon"; handle "lon" with extra context rules.
        "heo": ["heo", "lon"],
        "ga": ["ga", "ga ta", "ga cong nghiep"],
        "bo": ["bo", "bo sua", "bo thit"],
        "tom": ["tom", "tom the", "tom su"],
        "lua": ["lua", "ruong lua"],
        "tằm": ["tam", "tam to", "tam to", "tam tua"],
        # disambiguation: don't let 'bắp' map to 'ngô' when user means cabbage
        "bắp cải": ["bap cai", "cai bap"],
        "ngô": ["ngo", "bap ngo", "bap my", "corn", "maize", "bap"],
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


def _tokenize_norm(text_norm: str) -> List[str]:
    # Very lightweight tokenizer; keep it deterministic.
    if not text_norm:
        return []
    parts = re.split(r"[^\w]+", text_norm)
    toks = [p for p in parts if p and len(p) >= 2]
    return toks


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_find_best(text_norm: str, choices: List[str], min_ratio: float = 0.86) -> Optional[str]:
    """Lightweight fuzzy matching fallback.

    Useful for long questions where exact word-boundary match misses because of punctuation,
    minor typos, or users mixing spacing.
    """

    if not text_norm or not choices:
        return None

    best_choice: Optional[str] = None
    best_ratio = 0.0
    for c in choices:
        c_norm = _normalize(c)
        if not c_norm:
            continue
        # Fast-path exact substring for phrases.
        if c_norm in text_norm:
            return c
        r = _fuzzy_ratio(text_norm, c_norm)
        if r > best_ratio:
            best_ratio = r
            best_choice = c

    if best_choice and best_ratio >= float(min_ratio):
        return best_choice
    return None


@dataclass(frozen=True)
class KBIndex:
    token_to_entry_idxs: Dict[str, Tuple[int, ...]]
    entry_tokens: Tuple[Tuple[str, ...], ...]


def _build_kb_index(entries: List[KBEntry]) -> KBIndex:
    token_to: Dict[str, List[int]] = {}
    entry_tokens: List[Tuple[str, ...]] = []

    for idx, e in enumerate(entries):
        tok_set: set[str] = set()
        tok_set.update(_tokenize_norm(_normalize(e.domain)))
        tok_set.update(_tokenize_norm(_normalize(e.specie)))
        tok_set.update(_tokenize_norm(_normalize(e.season)))
        tok_set.update(_tokenize_norm(_normalize(e.disease)))
        for s in e.symptoms:
            tok_set.update(_tokenize_norm(_normalize(s)))
        # Keep a stable order for debugging
        toks = tuple(sorted(tok_set))
        entry_tokens.append(toks)

        for t in toks:
            token_to.setdefault(t, []).append(idx)

    frozen = {k: tuple(v) for k, v in token_to.items()}
    return KBIndex(token_to_entry_idxs=frozen, entry_tokens=tuple(entry_tokens))


@lru_cache(maxsize=8)
def _get_resources(dataset_path: str) -> Tuple[List[KBEntry], Dict[str, Any], KBIndex]:
    entries = load_dataset(dataset_path)
    lex = _build_lexicons(entries)
    index = _build_kb_index(entries)
    return entries, lex, index


def _find_first_match(text_norm: str, candidates: List[str]) -> Optional[str]:
    for cand in candidates:
        cand_norm = _normalize(cand)
        if cand_norm and re.search(rf"\b{re.escape(cand_norm)}\b", text_norm):
            return cand
    return None


def _has_term(text_norm: str, term: str) -> bool:
    term_norm = _normalize(term)
    if not term_norm:
        return False
    # Ensure we don't match inside other words (e.g., 'ga' inside 'gan')
    return re.search(rf"(?<!\w){re.escape(term_norm)}(?!\w)", text_norm) is not None


def _has_pig_lon_with_context(text_norm: str) -> bool:
    """Return True if "lon" likely means pig (lợn), not "lớn".

    Because we strip accents, "lớn" (big) and "lợn" (pig) both become "lon".
    We therefore require a small context word near "lon" to treat it as pig.
    """

    # Examples we want to match: "con lon", "dan lon", "nuoi lon", "chuong lon".
    # Examples we must avoid: "mua lon", "qua lon", "rat lon".
    return re.search(r"(?<!\w)(con|dan|nuoi|chuong)\s+lon(?!\w)", text_norm) is not None


def _extract_symptoms(text_norm: str, symptom_list: List[str]) -> List[str]:
    found: List[str] = []
    symptom_lex = {_normalize(s) for s in symptom_list if s}
    for s in symptom_list:
        s_norm = _normalize(s)
        if not s_norm:
            continue
        # Avoid spurious matches for very short symptoms (e.g. "ho" appears inside many words)
        if len(s_norm) < 3:
            continue

        # Use boundary-safe match for single-token symptoms; allow substring for multiword phrases.
        if " " in s_norm:
            if s_norm in text_norm:
                found.append(s)
        else:
            if _has_term(text_norm, s_norm):
                found.append(s)

    # Extra VN-friendly symptom patterns (context understanding)
    # These help when the dataset doesn't contain an exact phrase, or users write variants.
    symptom_patterns = {
        "nôn ói": ["non oi", "oi", "oi mua"],
        "đau bụng": ["dau bung", "dau quan", "quan quai"],
        "kén ăn": ["ken an"],
        "bỏ ăn": ["bo an", "chan an", "khong an", "giam an"],
        "chướng bụng": ["chuong bung", "bung chuong", "day hoi"],
        "phân sâu trong nõn": ["phan sau trong non", "trong non co phan sau", "phan sau o non"],
        "nõn bị rách": ["non bi rach", "rach non", "an non", "sau an non"],
    }
    for canonical, variants in symptom_patterns.items():
        canon_norm = _normalize(canonical)
        if not canon_norm:
            continue
        matched = False
        for v in variants:
            v_norm = _normalize(v)
            if not v_norm:
                continue
            if re.search(rf"(?<!\w){re.escape(v_norm)}(?!\w)", text_norm):
                matched = True
                break

        if matched:
            # Only add if canonical exists in dataset lexicon
            if canon_norm in symptom_lex:
                found.append(canonical)

    # de-dup preserving order
    dedup: List[str] = []
    seen = set()
    for s in found:
        key = _normalize(s)
        if key not in seen:
            seen.add(key)
            dedup.append(s)
    return dedup


def _infer_domain_hint(q_norm: str) -> Optional[str]:
    """Heuristic domain hint when specie is missing."""
    if not q_norm:
        return None

    # aquaculture
    if any(w in q_norm for w in ["ao", "nuoi ca", "ca", "tom", "be", "nuoc", "phan trang", "mang"]):
        if any(w in q_norm for w in ["tom", "ca", "ao", "nuoi ca", "nuoi tom"]):
            return "aquaculture"

    # livestock
    if any(w in q_norm for w in ["con vat", "vat nuoi", "gia suc", "gia cam", "chuong", "thuc an", "tieu chay", "sot"]):
        return "livestock"

    # crop
    if any(w in q_norm for w in ["cay", "la", "than", "re", "ruong", "vun", "trai", "qua"]):
        return "crop"

    return None


def _try_ml_predict_entry_id(question: str, model_path: str = DEFAULT_MODEL_PATH) -> Optional[Dict[str, Any]]:
    """Try to predict a KB entry id from free-text question using a trained sklearn model."""
    try:
        resolved = _resolve_model_path(model_path)
        if not resolved or not os.path.exists(resolved):
            return None
        with open(resolved, "rb") as f:
            model = pickle.load(f)

        classes = model.get("classes") or []
        clf = model.get("classifier")
        vec_cfg = model.get("vectorizer") or {}
        if not classes or clf is None:
            return None

        from sklearn.feature_extraction.text import HashingVectorizer

        vectorizer = HashingVectorizer(
            n_features=int(vec_cfg.get("n_features", 2**18)),
            alternate_sign=False,
            ngram_range=tuple(vec_cfg.get("ngram_range", (1, 2))),
            norm=vec_cfg.get("norm", "l2"),
        )

        X = vectorizer.transform([question])
        proba = None
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X)[0]
            best_idx = int(proba.argmax())
            return {
                "id": classes[best_idx],
                "prob": float(proba[best_idx]),
                "type": str(model.get("type") or "unknown"),
            }

        pred = clf.predict(X)[0]
        return {"id": str(pred), "prob": None, "type": str(model.get("type") or "unknown")}
    except Exception:
        return None


def extract_entities(question: str, entries: List[KBEntry], lex: Dict[str, Any]) -> Dict[str, Any]:
    q_norm = _normalize(question)

    domain_hint = _infer_domain_hint(q_norm)

    # 1) Specie (dictionary + aliases)
    specie: Optional[str] = None
    for canonical, aliases in lex.get("specie_aliases", {}).items():
        for alias in aliases:
            alias_norm = _normalize(alias)
            if canonical == "heo" and alias_norm == "lon":
                hit = _has_pig_lon_with_context(q_norm)
            else:
                hit = _has_term(q_norm, alias)

            if hit:
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
            if _has_term(q_norm, alias):
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
    if not disease:
        # Fuzzy fallback (avoid being too eager; diseases are often longer phrases)
        disease = _fuzzy_find_best(q_norm, lex["diseases"], min_ratio=0.88)

    # 4) Symptoms
    symptoms_found = _extract_symptoms(q_norm, lex["symptoms"])

    return {
        "question": question,
        "domain_hint": domain_hint,
        "specie": specie,
        "season": season,
        "disease": disease,
        "symptoms": symptoms_found,
    }


def _score_entry(extracted: Dict[str, Any], entry: KBEntry) -> float:
    score = 0.0

    if extracted.get("domain_hint") and _normalize(extracted["domain_hint"]) == _normalize(entry.domain):
        score += 1.0

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


def match_kb_indexed(extracted: Dict[str, Any], entries: List[KBEntry], index: KBIndex) -> Tuple[Optional[KBEntry], float]:
    """Match KB using a token index to avoid O(n) full scan for large datasets."""

    q_norm = _normalize(extracted.get("question") or "")
    tokens = set(_tokenize_norm(q_norm))

    # Prefer extracted fields (more precise) when present.
    for k in ("specie", "season", "disease"):
        v = extracted.get(k)
        if v:
            tokens.update(_tokenize_norm(_normalize(str(v))))
    for s in (extracted.get("symptoms") or []):
        tokens.update(_tokenize_norm(_normalize(str(s))))

    # Collect candidates by token hits.
    hit_counts: Dict[int, int] = {}
    for t in tokens:
        idxs = index.token_to_entry_idxs.get(t)
        if not idxs:
            continue
        for i in idxs:
            hit_counts[i] = hit_counts.get(i, 0) + 1

    # If nothing hits (very generic question), fall back to full scan.
    if not hit_counts:
        return match_kb(extracted, entries)

    # Take top candidates by token-hit count to keep scoring bounded.
    top = sorted(hit_counts.items(), key=lambda kv: kv[1], reverse=True)
    candidate_idxs = [i for i, _ in top[:800]]

    best: Optional[KBEntry] = None
    best_score = -1.0
    for i in candidate_idxs:
        e = entries[i]
        s = _score_entry(extracted, e)
        if s > best_score:
            best = e
            best_score = s

    confidence = max(0.0, min(1.0, best_score / 10.0))
    return best, confidence


def _choose_best_entry(
    question: str,
    extracted: Dict[str, Any],
    entries: List[KBEntry],
) -> Tuple[Optional[KBEntry], float, Optional[Dict[str, Any]]]:
    """Hybrid chooser: rule-based KB scoring first, ML fallback if missing disease/symptoms."""

    # Note: prefer indexed matching when possible.
    kb_entry, kb_conf = match_kb(extracted, entries)
    ml_pred = _try_ml_predict_entry_id(question)

    id_map = {e.id: e for e in entries}
    ml_entry = id_map.get(ml_pred["id"]) if ml_pred and ml_pred.get("id") else None
    ml_prob = float(ml_pred.get("prob")) if ml_pred and ml_pred.get("prob") is not None else None

    # If we extracted strong signals, trust KB scoring.
    has_disease = bool(extracted.get("disease"))
    has_symptoms = bool(extracted.get("symptoms"))

    if has_disease or has_symptoms:
        return kb_entry, kb_conf, ml_pred

    # Otherwise, if KB confidence is low but ML has a confident prediction, use ML.
    if ml_entry and ml_prob is not None and ml_prob >= 0.45 and kb_conf < 0.45:
        return ml_entry, max(kb_conf, ml_prob), ml_pred

    return kb_entry, kb_conf, ml_pred


def _choose_best_entry_indexed(
    question: str,
    extracted: Dict[str, Any],
    entries: List[KBEntry],
    index: KBIndex,
) -> Tuple[Optional[KBEntry], float, Optional[Dict[str, Any]]]:
    kb_entry, kb_conf = match_kb_indexed(extracted, entries, index)
    ml_pred = _try_ml_predict_entry_id(question)

    id_map = {e.id: e for e in entries}
    ml_entry = id_map.get(ml_pred["id"]) if ml_pred and ml_pred.get("id") else None
    ml_prob = float(ml_pred.get("prob")) if ml_pred and ml_pred.get("prob") is not None else None

    has_disease = bool(extracted.get("disease"))
    has_symptoms = bool(extracted.get("symptoms"))
    if has_disease or has_symptoms:
        return kb_entry, kb_conf, ml_pred

    if ml_entry and ml_prob is not None and ml_prob >= 0.45 and kb_conf < 0.45:
        return ml_entry, max(kb_conf, ml_prob), ml_pred

    return kb_entry, kb_conf, ml_pred


def _topk_accuracy_from_decision(decision, y_true: List[str], classes: List[str], k: int = 3) -> float:
    import numpy as np

    # decision: (n_samples, n_classes)
    if decision is None:
        return 0.0
    arr = np.asarray(decision)
    if arr.ndim != 2 or arr.shape[1] != len(classes):
        return 0.0
    topk = np.argsort(-arr, axis=1)[:, :k]
    class_arr = np.asarray(classes)
    hits = 0
    for i, yi in enumerate(y_true):
        if yi in set(class_arr[topk[i]].tolist()):
            hits += 1
    return hits / max(1, len(y_true))


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


def generate_preview_prompt(question: str, extracted: Dict[str, Any], entry: Optional[KBEntry]) -> str:
    """Generate a human-reviewable prompt (input) in the exact style the user requested."""

    # Enrich missing fields from KB match (avoid null/empty in preview when we have a match)
    disease = extracted.get("disease")
    if not disease and entry:
        disease = entry.disease

    symptoms = extracted.get("symptoms") or []
    if (not symptoms) and entry:
        # Use a short list of typical symptoms when extraction is uncertain
        symptoms = list(entry.symptoms[:6])

    payload: Dict[str, Any] = {
        "question": question,
        "specie": extracted.get("specie") or (entry.specie if entry else None),
        "season": extracted.get("season"),
        "disease": disease,
        "symptoms": symptoms,
        "causes": list(entry.causes) if entry else [],
        "advice": list(entry.advice) if entry else [],
    }

    header = (
        "Bạn là AgriSense AI – chuyên gia tư vấn nông nghiệp thông minh và thân thiện của Việt Nam 🌾🐟.\n"
        "Nhiệm vụ: nhận dữ liệu JSON về câu hỏi nông nghiệp, phân tích và sinh ra **văn bản trả lời thân thiện**, "
        "bao gồm emoji, nêu triệu chứng, nguyên nhân, và khuyến nghị hành động.\n"
    )

    json_block = json.dumps(payload, ensure_ascii=False, indent=2)

    instruction = "Hãy xuất ra văn bản dạng thân thiện, dễ đọc cho người nông dân"
    return f"{header}\n{json_block}\n\n{instruction}".strip()


def _build_training_samples(entries: List[KBEntry]) -> Tuple[List[str], List[str]]:
    texts: List[str] = []
    labels: List[str] = []
    for e in entries:
        if e.examples:
            for ex in e.examples:
                if ex and str(ex).strip():
                    texts.append(str(ex).strip())
                    labels.append(e.id)
        else:
            # Fallback so every entry contributes at least one sample
            texts.append(f"{e.specie} {e.disease} {e.season}")
            labels.append(e.id)

        # Light canonical sample (helps stabilize training)
        canonical = f"{e.specie} bị {e.disease} ({e.season}). Triệu chứng: {', '.join(e.symptoms[:3])}."
        texts.append(canonical)
        labels.append(e.id)

    return texts, labels


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def cli_train(args: argparse.Namespace) -> int:
    """Train a lightweight text classifier from dataset examples.

    This is intentionally simple and dependency-light (scikit-learn).
    """

    entries = load_dataset(args.dataset)
    texts, labels = _build_training_samples(entries)

    if not texts:
        raise ValueError("No training samples found in dataset (examples empty)")

    # Import lazily to keep non-train use-cases lightweight.
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier

    vectorizer = HashingVectorizer(
        n_features=2**18,
        alternate_sign=False,
        ngram_range=(1, 2),
        norm="l2",
    )

    classes = sorted(set(labels))
    clf = SGDClassifier(
        loss="log_loss",
        alpha=1e-4,
        max_iter=1,
        tol=None,
        random_state=args.seed,
    )

    rnd = random.Random(args.seed)
    indices = list(range(len(texts)))

    for epoch in range(int(args.epoch)):
        rnd.shuffle(indices)
        first_fit = epoch == 0
        for start in range(0, len(indices), int(args.batch_size)):
            batch = indices[start : start + int(args.batch_size)]
            Xb = vectorizer.transform([texts[i] for i in batch])
            yb = [labels[i] for i in batch]
            if first_fit and start == 0:
                clf.partial_fit(Xb, yb, classes=classes)
            else:
                clf.partial_fit(Xb, yb)

    # quick training-set accuracy (sanity only)
    X_all = vectorizer.transform(texts)
    pred = clf.predict(X_all)
    acc = sum(1 for p, y in zip(pred, labels) if p == y) / max(1, len(labels))

    model = {
        "type": "hashing_sgd_v1",
        "trained_at": time.time(),
        "dataset_path": os.path.abspath(args.dataset),
        "classes": classes,
        "vectorizer": {
            "n_features": 2**18,
            "ngram_range": (1, 2),
            "norm": "l2",
        },
        "classifier": clf,
    }

    out_path = args.model_out or DEFAULT_MODEL_PATH
    _ensure_dir(out_path)
    with open(out_path, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Trained samples: {len(texts)}")
    print(f"✅ Classes (kb ids): {len(classes)}")
    print(f"✅ Train accuracy (sanity): {acc:.3f}")
    print(f"💾 Saved model: {out_path}")
    return 0


def cli_check_dataset(args: argparse.Namespace) -> int:
    entries = load_dataset(args.dataset)
    print(f"✅ entries: {len(entries)}")
    print("✅ json ok, ids unique")
    return 0


def cli_eval(args: argparse.Namespace) -> int:
    """Basic offline evaluation for the text classifier.

    This gives a real test split metric (not just train sanity acc).
    """

    entries = load_dataset(args.dataset)
    texts, labels = _build_training_samples(entries)
    if not texts:
        raise ValueError("No training samples found in dataset (examples empty)")

    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.model_selection import train_test_split

    classes = sorted(set(labels))
    n_classes = len(classes)
    n_samples = len(texts)

    # With many classes, a naive test_size (e.g. 0.2) can be too small to contain
    # at least one sample per class, which breaks stratified splitting.
    test_size: int | float = float(args.test_size)
    stratify = labels if n_classes > 1 else None
    if isinstance(test_size, float):
        desired = int(round(test_size * n_samples))
        if desired < n_classes:
            # Prefer an integer test set size that can include all classes.
            desired = n_classes
        # Ensure train still has at least 1 sample per class when stratifying.
        if stratify is not None and (n_samples - desired) < n_classes:
            # Can't satisfy stratification; fall back to non-stratified split.
            stratify = None
        test_size = desired

    X_train_texts, X_test_texts, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=int(args.seed),
        stratify=stratify,
    )

    vectorizer = HashingVectorizer(
        n_features=2**18,
        alternate_sign=False,
        ngram_range=(1, 2),
        norm="l2",
    )
    X_train = vectorizer.transform(X_train_texts)
    X_test = vectorizer.transform(X_test_texts)

    clf = SGDClassifier(
        loss="log_loss",
        alpha=1e-4,
        max_iter=5,
        tol=1e-3,
        random_state=int(args.seed),
    )
    clf.fit(X_train, y_train)

    pred = clf.predict(X_test)
    acc = sum(1 for p, y in zip(pred, y_test) if p == y) / max(1, len(y_test))

    top3 = 0.0
    try:
        decision = clf.decision_function(X_test)
        top3 = _topk_accuracy_from_decision(decision, list(y_test), classes, k=3)
    except Exception:
        top3 = 0.0

    print(f"✅ samples: {len(texts)}")
    print(f"✅ classes: {len(classes)}")
    print(f"✅ test_size: {len(y_test)}")
    print(f"📈 accuracy@1: {acc:.3f}")
    print(f"📈 accuracy@3: {top3:.3f}")
    return 0


def cli_model_info(args: argparse.Namespace) -> int:
    resolved = _resolve_model_path(DEFAULT_MODEL_PATH)
    print(
        json.dumps(
            {
                "default_model_path": os.path.abspath(DEFAULT_MODEL_PATH),
                "resolved_model_path": os.path.abspath(resolved) if resolved else None,
                "exists": bool(resolved and os.path.exists(resolved)),
                "model_source": (os.environ.get("AGRIMIND_MODEL_SOURCE") or "auto").strip() or "auto",
                "hf_repo": (os.environ.get("AGRIMIND_HF_REPO") or "").strip() or None,
                "hf_filename": (os.environ.get("AGRIMIND_HF_FILENAME") or "").strip() or None,
                "hf_revision": (os.environ.get("AGRIMIND_HF_REVISION") or "main").strip() or "main",
                "hf_token_set": bool((os.environ.get("AGRIMIND_HF_TOKEN") or "").strip()),
                "cache_dir": _get_cache_dir(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


@lru_cache(maxsize=1024)
def _cached_extract(question: str, dataset_path: str) -> Dict[str, Any]:
    entries, lex, index = _get_resources(dataset_path)
    extracted = extract_entities(question, entries, lex)
    entry, confidence, ml_pred = _choose_best_entry_indexed(question, extracted, entries, index)

    # Optional: if we matched an entry, backfill disease for downstream consumers
    if entry and not extracted.get("disease"):
        extracted = dict(extracted)
        extracted["disease"] = entry.disease
    rules = rule_engine(extracted, entry, confidence)

    _maybe_log_event(
        {
            "ts": time.time(),
            "question": question,
            "extracted": {
                "domain_hint": extracted.get("domain_hint"),
                "specie": extracted.get("specie"),
                "season": extracted.get("season"),
                "disease": extracted.get("disease"),
                "symptoms": extracted.get("symptoms"),
            },
            "matched_id": entry.id if entry else None,
            "confidence": float(confidence),
            "ml_pred": ml_pred,
            "allow_answer": bool(rules.get("allow_answer")),
        }
    )
    return {
        "extracted": extracted,
        "matched": (entry.__dict__ if entry else None),
        "confidence": confidence,
        "ml_pred": ml_pred,
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


def cli_answer(args: argparse.Namespace) -> int:
    result = _cached_extract(args.text, args.dataset)
    extracted = result["extracted"]
    entry_raw = result["matched"]
    entry = KBEntry(**entry_raw) if entry_raw else None
    prompt = generate_preview_prompt(args.text, extracted, entry)
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
    p.add_argument("--mode", choices=["train"], default=None, help="Run a special mode (e.g. train)")
    p.add_argument("--epoch", type=int, default=5, help="Epochs for --mode train")
    p.add_argument("--batch-size", type=int, default=32, help="Batch size for --mode train")
    p.add_argument("--seed", type=int, default=42, help="Random seed for --mode train")
    p.add_argument("--model-out", default=DEFAULT_MODEL_PATH, help="Output path for trained model")

    sub = p.add_subparsers(dest="cmd")

    p_extract = sub.add_parser("extract", help="Extract entities + match KB")
    p_extract.add_argument("text", help="User question")
    p_extract.set_defaults(func=cli_extract)

    p_prompt = sub.add_parser("prompt", help="Generate LLM prompt (app-style)")
    p_prompt.add_argument("text", help="User question")
    p_prompt.set_defaults(func=cli_prompt)

    p_answer = sub.add_parser("answer", help="Generate preview prompt (header + JSON + instruction)")
    p_answer.add_argument("text", help="User question")
    p_answer.set_defaults(func=cli_answer)

    p_serve = sub.add_parser("serve", help="Run REST API (Flask)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8011)
    p_serve.set_defaults(func=cli_serve)

    p_check = sub.add_parser("check-dataset", help="Validate dataset.json (json + schema + unique ids)")
    p_check.set_defaults(func=cli_check_dataset)

    p_eval = sub.add_parser("eval", help="Evaluate text classifier with a held-out split")
    p_eval.add_argument("--seed", type=int, default=42)
    p_eval.add_argument("--test-size", type=float, default=0.2)
    p_eval.set_defaults(func=cli_eval)

    p_info = sub.add_parser("model-info", help="Show where the ML model is loaded from (local vs Hugging Face)")
    p_info.set_defaults(func=cli_model_info)

    return p


def main() -> int:
    # Windows consoles may default to legacy codepages; this avoids UnicodeEncodeError
    # when printing Vietnamese text.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    logging.basicConfig(level=os.environ.get("AGRIMIND_LOG_LEVEL", "WARNING"))

    parser = build_argparser()
    args = parser.parse_args()

    if args.mode == "train":
        return int(cli_train(args))

    if hasattr(args, "func"):
        return int(args.func(args))

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
