"""clarify_intent.py

ML + rule-first detector for unclear/underspecified agriculture questions.

Goal:
- Detect when a user's question is too vague to answer confidently (missing key details)
- Ask for the missing details using a friendly clarification prompt
- Avoid calling LLM APIs for these cases (optional integration in app.py)

Datasets:
- dataset/clarify_intent.json   (text,label)  label 0 = unclear, 1 = clear
- dataset/clarify_replies.json  (list of clarification replies)

Model:
- model/clarify_intent.pkl

Env vars:
- CLARIFY_INTENT_MODEL_SOURCE=auto|off|local (default: auto)
- CLARIFY_INTENT_THRESHOLD=0.65             (default: 0.65)  # threshold on P(unclear)
- CLARIFY_REPLY_MODE=sample|mixed           (default: sample)
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import random
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "clarify_intent.json")
DEFAULT_REPLIES_PATH = os.path.join(HERE, "dataset", "clarify_replies.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "clarify_intent.pkl")


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def _tokenize(text_norm: str) -> List[str]:
    if not text_norm:
        return []
    parts = re.split(r"[^\w]+", text_norm)
    return [p for p in parts if p]


# High-level agriculture hints
_AGRI_HINT_TOKENS = {
    # crop
    "trong",
    "gieo",
    "vuon",
    "ruong",
    "cay",
    "la",
    "re",
    "than",
    "hoa",
    "trai",
    "hat",
    "phan",
    "bon",
    "npk",
    "thuoc",
    "sau",
    "benh",
    "nam",
    "dao",
    "on",
    # livestock
    "heo",
    "lon",
    "ga",
    "vit",
    "bo",
    "de",
    "chuong",
    # aquaculture
    "tom",
    "ca",
    "ao",
    "be",
    "nuoc",
    "ph",
    "kiem",
    "do",
}


# Patterns that often indicate a generic request (likely needs clarification)
_GENERIC_PATTERNS = [
    r"\btu van\b",
    r"\bhuong dan\b",
    r"\bchi\s*dan\b",
    r"\bcach\b",
    r"\bphong\s*benh\b",
    r"\btri\s*benh\b",
    r"\bthuoc\b",
    r"\bphan\b",
    r"\bkhau\s*phan\b",
    r"\bcong\s*thuc\b",
]


_DETAIL_HINT_TOKENS = {
    # time / stage
    "ngay",
    "tuan",
    "thang",
    "nam",
    "giai",
    "doan",
    "sau",
    "truoc",
    # quantities
    "kg",
    "g",
    "gam",
    "lit",
    "l",
    "ml",
    "ha",
    "m2",
    "m3",
    "%",
    # environment
    "ph",
    "kiem",
    "do",
    "nh3",
    "no2",
    "nhiet",
    "doam",
    "ec",
    # symptoms (detail-ish)
    "vang",
    "heo",
    "kho",
    "khe",
    "tieu",
    "chay",
    "noi",
    "dau",
    "loet",
    "dom",
    "he",
    "ru",
    "rot",
    "mui",
}


def _looks_like_question(text_norm: str) -> bool:
    if not text_norm:
        return False
    # if it contains question mark or typical VN question words
    if "?" in text_norm:
        return True
    return any(w in text_norm.split() for w in ["khong", "sao", "the", "gi", "nao", "bao", "nhu", "vi", "tai"])


def _has_agri_hint(tokens: List[str]) -> bool:
    return any(t in _AGRI_HINT_TOKENS for t in tokens)


def _has_detail(text_norm: str, tokens: List[str]) -> bool:
    if any(ch.isdigit() for ch in text_norm):
        return True
    if any(t in _DETAIL_HINT_TOKENS for t in tokens):
        return True
    # contains units/measure-like strings
    if re.search(r"\b(\d+(?:[\.,]\d+)?)\s*(kg|g|gam|lit|l|ml|ha|m2|m3|ppm|%|°c|c)\b", text_norm):
        return True
    return False


def needs_clarification_rule(text: str) -> bool:
    """Heuristic detector for unclear questions.

    Returns True if message is likely agriculture-related but underspecified.
    """

    if not isinstance(text, str):
        return False

    msg = text.strip()
    if not msg:
        return False

    # Skip very long prompts (already detailed)
    if len(msg) > 450:
        return False

    norm = _normalize(msg)
    tokens = _tokenize(norm)

    # If it doesn't look like a question/request, don't intercept.
    if not _looks_like_question(norm):
        return False

    # If not agriculture-related, don't intercept.
    if not _has_agri_hint(tokens):
        return False

    # Extremely short requests are almost always unclear.
    if len(tokens) <= 3:
        return True

    # If generic request pattern AND no detail, treat as unclear.
    if any(re.search(pat, norm) for pat in _GENERIC_PATTERNS) and not _has_detail(norm, tokens):
        return True

    # If message is short-ish and lacks details, treat as unclear.
    if len(tokens) <= 7 and not _has_detail(norm, tokens):
        return True

    return False


@lru_cache(maxsize=1)
def _load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            out: List[Dict[str, Any]] = []
            for row in data:
                if isinstance(row, dict) and "text" in row and "label" in row:
                    out.append(row)
            return out
        return []
    except Exception:
        return []


@lru_cache(maxsize=1)
def _load_clarify_replies(path: str = DEFAULT_REPLIES_PATH) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        out: List[str] = []
        for row in data:
            if isinstance(row, str):
                t = row.strip()
            elif isinstance(row, dict):
                t = str(row.get("text") or "").strip()
            else:
                continue
            if t:
                out.append(t)
        return out
    except Exception:
        return []


def _resolve_model_path() -> Optional[str]:
    source = (os.environ.get("CLARIFY_INTENT_MODEL_SOURCE") or "auto").strip().lower()
    if source == "off":
        return None
    if source == "local":
        return DEFAULT_MODEL_PATH if os.path.exists(DEFAULT_MODEL_PATH) else None
    # auto
    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH
    return None


def _predict_proba_unclear_ml(text: str) -> Optional[float]:
    """Return P(unclear) if model available.

    Dataset convention: label 0 = unclear, label 1 = clear.
    """
    try:
        model_path = _resolve_model_path()
        if not model_path:
            return None

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        clf = model.get("classifier")
        vec_cfg = model.get("vectorizer") or {}
        if clf is None:
            return None

        from sklearn.feature_extraction.text import HashingVectorizer

        vectorizer = HashingVectorizer(
            n_features=int(vec_cfg.get("n_features", 2**16)),
            alternate_sign=False,
            ngram_range=tuple(vec_cfg.get("ngram_range", (1, 2))),
            norm=vec_cfg.get("norm", "l2"),
        )

        X = vectorizer.transform([text])
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X)[0]
            classes = list(getattr(clf, "classes_", []))
            if 0 in classes:
                idx = classes.index(0)
                return float(proba[idx])
            # fallback if something is odd
            return float(proba[0])

        return None
    except Exception:
        return None


def needs_clarification(text: str) -> bool:
    """Rule-first, ML-fallback ambiguous question detector."""

    if needs_clarification_rule(text):
        return True

    proba = _predict_proba_unclear_ml(text)
    if proba is None:
        return False

    try:
        thr = float(os.environ.get("CLARIFY_INTENT_THRESHOLD", "0.65"))
    except Exception:
        thr = 0.65

    return proba >= thr


def _detect_domain(text: str) -> str:
    norm = _normalize(text)
    toks = set(_tokenize(norm))

    aqua = {"tom", "ca", "ao", "be", "nuoc", "kiem", "ph", "no2", "nh3"}
    live = {"heo", "lon", "ga", "vit", "bo", "de", "chuong"}

    # NOTE: after _normalize, "phân" and "phần" both become "phan".
    # So we must special-case phrases like "khẩu phần" to avoid misclassifying as crop.
    feed_phrases = ["khau phan", "cong thuc", "phoi tron", "thuc an"]

    crop = {
        "trong",
        "gieo",
        "cay",
        "la",
        "re",
        "than",
        "vuon",
        "ruong",
        "dat",
        # common crops / keywords
        "rau",
        "lua",
        "sau",
        "rieng",
        "caphe",
        "ca",
        "phe",
        "hotieu",
        "ho",
        "tieu",
        "cam",
        "chanh",
        "mit",
        "dua",
        "ot",
        "cachua",
        "ca",
        "chua",
    }
    feed = {"khau", "phan", "cong", "thuc", "phoitr", "tron", "thucan"}

    if toks.intersection(aqua):
        return "aqua"
    if toks.intersection(live):
        return "livestock"
    # If user clearly talks about feed formula/portion, domain is unknown unless explicit animal/aqua tokens exist.
    if any(phrase in norm for phrase in feed_phrases):
        if toks.intersection(aqua):
            return "aqua"
        if toks.intersection(live):
            return "livestock"
        return "unknown"

    if toks.intersection(crop):
        return "crop"

    # If we cannot tell the domain (e.g., "khẩu phần ăn"), treat as unknown.
    if toks.intersection(feed):
        return "unknown"

    return "unknown"


def _detect_topic(domain: str, text: str) -> str:
    """Coarse topic detection to ask the right follow-up questions.

    Returns one of: disease, nutrition, water, odor, technique, unknown
    """

    norm = _normalize(text)
    toks = set(_tokenize(norm))

    # shared
    if any(k in toks for k in {"mui", "hoi"}):
        return "odor"

    if any(k in toks for k in {"khau", "phan", "cong", "thuc", "phoitr", "tron", "thucan", "thuc", "an"}):
        # a bit broad; refined by domain below
        return "nutrition"

    if domain == "unknown":
        return "unknown"

    if domain == "aqua":
        if any(k in toks for k in {"ph", "kiem", "do", "nh3", "no2", "tao", "mau", "nuoc", "bot", "duc"}):
            return "water"
        if any(k in toks for k in {"phan", "trang", "ruot", "dut", "khuc", "mem", "vo", "dom", "loet", "nam"}):
            return "disease"
        return "technique"

    if domain == "livestock":
        if any(k in toks for k in {"ho", "kho", "khe", "tho", "sot", "tieu", "chay", "phan", "bo", "an", "chet"}):
            return "disease"
        return "technique"

    # crop
    if any(k in toks for k in {"phan", "bon", "npk", "vi", "luong", "canxi", "bo", "kali", "dam", "lan"}):
        return "nutrition"
    # IMPORTANT: after normalization, "sầu" and "sâu" both become "sau".
    # So we avoid using bare token "sau" as a disease signal.
    symptom_tokens = {"rep", "nhay", "tri", "ray", "nam", "benh", "dom", "he", "vang", "ru", "rot", "thoi", "xoan", "chay", "ximumu"}
    pest_phrases = ["bi sau", "con sau", "sau an", "sau cuon la", "sau ve bo"]
    if any(k in toks for k in symptom_tokens) or any(p in norm for p in pest_phrases) or any(k in norm for k in ["phun thuoc", "thuoc tri", "tri benh", "phong benh"]):
        return "disease"
    return "technique"


def _is_prefix_safe(domain: str, reply: str) -> bool:
    """Hard filter to prevent obviously off-topic prefixes."""

    r = _normalize(reply)

    crop_terms = ["la ", " re ", " than ", "vuon", "ruong", "cay", "bon phan", "npk", "phun thuoc", "thuoc tri"]
    aqua_terms = ["ao", "be", "do", "kiem", "nh3", "no2", "tao", "mau nuoc", "p h", "ph "]
    live_terms = ["chuong", "dan", "tiem", "tiem phong", "ho", "kho khe", "phan", "bo an"]

    if domain == "livestock":
        # Do not show crop-only wording
        if any(t in r for t in crop_terms):
            return False
        # Avoid water-chem metrics for livestock
        if any(t in r for t in aqua_terms):
            return False

    if domain == "aqua":
        # Avoid crop-only wording
        if any(t in r for t in crop_terms):
            return False

    if domain == "crop":
        # Avoid fish-pond / livestock-specific wording
        if any(t in r for t in aqua_terms):
            return False
        if any(t in r for t in live_terms):
            return False

    return True


def _score_prefix_reply(domain: str, reply: str) -> int:
    """Score a prefix reply to avoid off-topic prompts."""

    r = _normalize(reply)
    score = 0

    # Penalize domain-mismatching nouns.
    if domain != "aqua" and any(x in r for x in ["ao", "be", "tao", "do", "kiem", "nh3", "no2", "mau nuoc"]):
        score -= 4
    if domain != "livestock" and any(x in r for x in ["chuong", "dan", "tiem", "tiem phong", "tieu chay", "ho", "kho khe"]):
        score -= 3
    if domain != "crop" and any(x in r for x in ["la", "re", "than", "vuon", "ruong", "cay"]):
        score -= 3

    # Prefer generic, safe prompts.
    if any(x in r for x in ["doi tuong", "trieu chung", "thoi gian", "khu vuc", "anh"]):
        score += 2
    if "pH" in reply or "EC" in reply or "DO" in reply:
        score += 1 if domain == "aqua" else -2

    return score


_BASE_FALLBACK_REPLIES = [
    "Mình có thể hỗ trợ, nhưng bạn cho mình thêm vài chi tiết để tư vấn đúng nhé.",
    "Bạn mô tả giúp mình rõ hơn (đang trồng/nuôi gì, tình trạng như thế nào, xuất hiện bao lâu rồi) nhé.",
]


_PREFIX_BY_DOMAIN: Dict[str, List[str]] = {
    "unknown": [
        "Mình có thể hỗ trợ, nhưng bạn cho mình thêm vài chi tiết để tư vấn đúng nhé.",
        "Bạn nói rõ giúp mình đối tượng và tình trạng hiện tại nhé.",
        "Cho mình xin thêm 1–2 thông tin để mình tư vấn sát hơn nha.",
    ],
    "crop": [
        "Mình hỗ trợ được. Bạn cho mình xin thêm vài chi tiết để tư vấn đúng cây và đúng giai đoạn nhé.",
        "Bạn mô tả kỹ hơn một chút để mình không tư vấn sai hướng nha.",
        "Bạn cho mình thêm thông tin (hoặc ảnh) để mình chẩn đoán sát hơn nhé.",
    ],
    "livestock": [
        "Mình hỗ trợ được. Bạn cho mình thêm vài chi tiết về đàn và triệu chứng để mình tư vấn đúng nhé.",
        "Bạn mô tả rõ hơn một chút (độ tuổi, triệu chứng, tỉ lệ con bị) để mình chẩn đoán sát hơn nha.",
        "Để tránh tư vấn sai, bạn bổ sung giúp mình vài thông tin quan trọng nhé.",
    ],
    "aqua": [
        "Mình hỗ trợ được. Bạn cho mình thêm vài thông tin về ao/bể và hiện tượng để mình tư vấn đúng nhé.",
        "Bạn mô tả rõ hơn một chút (loài nuôi, tuổi ngày nuôi, biểu hiện) để mình tư vấn sát hơn nha.",
        "Cho mình xin thêm dữ kiện về nước và tình trạng tôm/cá để mình chẩn đoán nhanh nhé.",
    ],
}


def generate_clarify_reply(user_text: Optional[str] = None) -> str:
    """Generate a context-aware clarification prompt.

    Key goals:
    - Avoid off-topic questions (no asking pH/EC for pigs, etc.)
    - Ask only the most relevant missing details for the detected domain/topic
    - Keep phrasing friendly and short
    """

    text = user_text or ""
    domain = _detect_domain(text)
    topic = _detect_topic(domain, text)

    # Use curated domain-specific prefixes to avoid off-topic questions.
    prefix_pool = _PREFIX_BY_DOMAIN.get(domain) or _PREFIX_BY_DOMAIN["unknown"]
    prefix = random.choice(prefix_pool)

    # Build a targeted checklist by domain/topic.
    if domain == "unknown":
        if topic == "nutrition":
            ask = (
                "\n\nBạn cho mình xin thêm: bạn cần khẩu phần/công thức cho đối tượng nào (heo/gà/bò hay tôm/cá), "
                "giai đoạn (con giống/tăng trọng/đẻ; hoặc ngày nuôi), và mục tiêu (tăng trọng/đẻ/giữ sức)."
            )
        else:
            ask = (
                "\n\nBạn cho mình xin thêm: bạn đang hỏi về cây trồng hay vật nuôi/ao nuôi? Nêu rõ đối tượng + tình trạng + thời gian xuất hiện để mình tư vấn đúng."
            )

    elif domain == "aqua":
        if topic == "water":
            norm = _normalize(text)
            is_green_water = any(k in norm for k in ["nuoc ao xanh", "xanh reu", "tao xanh", "tao day", "nuoc xanh", "rong tao"])

            # Water-first questions should ask water context/parameters FIRST.
            # Only ask about tôm/cá if the user is actually stocking (optional).
            if is_green_water:
                ask = (
                    "\n\nBạn cho mình xin thêm về NƯỚC AO: màu xanh kiểu gì (xanh rêu/xanh đậm), độ trong (ước cm), có bọt/mùi không, "
                    "và nếu có thì pH sáng/chiều, kiềm, DO (đặc biệt lúc 4–6h sáng), NH3/NO2, nhiệt độ. "
                    "Ao có quạt/ sục khí không và gần đây có mưa/tạt vôi/diệt tảo/thay nước không? (Nếu ao đang nuôi gì thì nói thêm giúp mình.)"
                )
            else:
                ask = (
                    "\n\nBạn cho mình xin thêm về NƯỚC AO: diện tích/độ sâu ao, màu nước (xanh/đục/nâu), có mùi/bọt không, "
                    "và nếu có thì pH sáng/chiều, kiềm, DO, NH3/NO2, nhiệt độ/độ mặn. "
                    "Gần đây bạn có thay nước/tạt vôi/vi sinh/hoá chất gì không? (Nếu ao đang nuôi gì thì nói thêm giúp mình.)"
                )
        elif topic == "nutrition":
            ask = (
                "\n\nBạn cho mình xin thêm: loài nuôi, tuổi ngày nuôi, lượng cho ăn/ngày (mấy cữ), biểu hiện đường ruột/phân (nếu có), "
                "và gần đây có đổi cám/men/vi sinh gì không."
            )
        else:
            ask = (
                "\n\nBạn cho mình xin thêm: loài nuôi (tôm/cá), tuổi ngày nuôi, triệu chứng chính, và các thông số nước cơ bản (pH–kiềm–DO–nhiệt) nếu có."
            )

    elif domain == "livestock":
        if topic == "odor":
            ask = (
                "\n\nBạn cho mình xin thêm: loại chuồng (kín/hở), nền khô hay ướt, có rò nước uống không, số lượng con, "
                "và bạn đang dùng đệm lót/men vi sinh/khử mùi gì rồi."
            )
        elif topic == "nutrition":
            ask = (
                "\n\nBạn cho mình xin thêm: con gì (heo/gà/bò...), lứa tuổi/giai đoạn (con giống/thịt/đẻ), mục tiêu (tăng trọng/đẻ), "
                "khẩu phần hiện tại (loại cám/tỉ lệ phối trộn) và biểu hiện (gầy/yếu/tiêu chảy...) nếu có."
            )
        else:  # disease/technique
            ask = (
                "\n\nBạn cho mình xin thêm: con gì, độ tuổi/trọng lượng, triệu chứng chính (ho/khò khè/tiêu chảy/bỏ ăn/sốt), "
                "tỉ lệ con bị, và đã tiêm phòng/dùng thuốc gì gần đây chưa."
            )

    else:  # crop
        if topic == "nutrition":
            ask = (
                "\n\nBạn cho mình xin thêm: cây gì/giống gì, giai đoạn (cây con/ra hoa/đậu trái), triệu chứng (vàng lá gân xanh/cháy mép/rụng bông...), "
                "và lịch bón gần đây (tên phân + liều). Nếu có pH đất/EC càng tốt."
            )
        elif topic == "disease":
            ask = (
                "\n\nBạn cho mình xin thêm: cây gì, giai đoạn, dấu hiệu cụ thể (đốm dạng gì, có sâu/rệp nhìn thấy không, mặt trên/dưới lá), "
                "thời gian xuất hiện và bạn đã phun/bón gì gần đây. Nếu có ảnh cận cảnh + tổng quan càng tốt."
            )
        else:  # technique
            ask = (
                "\n\nBạn cho mình xin thêm: bạn định trồng cây gì, trồng ở đâu (chậu/luống/vườn), điều kiện (nắng/mưa, đất/cát/phèn), "
                "và mục tiêu (trồng ăn lá/lấy trái/quy mô) để mình hướng dẫn đúng." 
            )

    return prefix + ask


def cli_train(args: argparse.Namespace) -> int:
    data = _load_dataset(args.dataset)

    texts: List[str] = []
    labels: List[int] = []

    for row in data:
        t = str(row.get("text") or "").strip()
        y = row.get("label")
        if not t:
            continue
        if y not in (0, 1, True, False):
            continue
        texts.append(t)
        labels.append(int(bool(y)))

    if not texts:
        raise ValueError("Empty clarify dataset")

    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier

    vectorizer = HashingVectorizer(
        n_features=2**16,
        alternate_sign=False,
        ngram_range=(1, 2),
        norm="l2",
    )

    X = vectorizer.transform(texts)

    clf = SGDClassifier(
        loss="log_loss",
        alpha=1e-4,
        max_iter=30,
        tol=1e-3,
        random_state=int(args.seed),
    )
    clf.fit(X, labels)

    pred = clf.predict(X)
    acc = sum(1 for p, y in zip(pred, labels) if int(p) == int(y)) / max(1, len(labels))

    os.makedirs(os.path.dirname(os.path.abspath(args.model_out)), exist_ok=True)
    with open(args.model_out, "wb") as f:
        pickle.dump(
            {
                "type": "hashing_sgd_clarify_intent_v1",
                "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
                "classifier": clf,
                "label_meaning": {"0": "unclear", "1": "clear"},
            },
            f,
        )

    print(f"✅ samples: {len(texts)}")
    print(f"✅ train_acc (sanity): {acc:.3f}")
    print(f"💾 saved: {os.path.abspath(args.model_out)}")
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Clarify intent detector + clarification replies")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--seed", type=int, default=42)

    sub = p.add_subparsers(dest="cmd")

    p_train = sub.add_parser("train", help="Train clarify intent model")
    p_train.add_argument("--model-out", default=DEFAULT_MODEL_PATH)
    p_train.set_defaults(func=cli_train)

    return p


def main() -> int:
    parser = build_argparser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        return int(args.func(args))

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
