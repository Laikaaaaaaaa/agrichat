"""domain_guard.py

ML + rule-first detector for out-of-domain questions.

User requirement
- Detect questions outside agriculture/environment domain.
- Refuse to answer (do NOT route to OpenAI) and ask the user to rephrase within scope.

Dataset
- dataset/domain_guard.json   (text,label)
  label 0 = in_domain (agriculture/environment)
  label 1 = out_of_domain

Model
- model/domain_guard.pkl

Env vars (optional)
- DOMAIN_GUARD_MODEL_SOURCE=auto|off|local (default: auto)
- DOMAIN_GUARD_THRESHOLD=0.65              (default: 0.65)  # threshold on P(out_of_domain)

Design notes
- Greeting-only is handled elsewhere; this module focuses on domain.
- We intentionally bias to refuse when the message has *no* agri/environment hints.
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
from typing import Any, Dict, List, Optional


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "domain_guard.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "domain_guard.pkl")


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


_STOPWORDS = {
    # ultra-common VN words that become ambiguous after accent stripping
    "la",  # "là" collides with "lá"
    "gi",
    "nao",
    "co",
    "cua",
    "toi",
    "ban",
    "minh",
    "cho",
    "voi",
    "va",
    "hay",
    "neu",
    "khi",
    "the",
    "sao",
    "o",
    "tai",
    "vi",
}


# Agriculture hints (VN + a few EN). Keep this set *specific* to avoid false positives.
_AGRI_HINT_TOKENS = {
    # crop
    "trong",
    "gieo",
    "ruong",
    "vuon",
    "cay",
    "lua",
    "gao",
    "ngo",
    "rau",
    "ot",
    "dua",
    "sau",
    "rep",
    "bo tri",
    "benh",
    "nam",
    "phan",
    "bon",
    "npk",
    "thuoc",
    "phun",
    "ipm",
    # livestock
    "heo",
    "lon",
    "ga",
    "vit",
    "bo",
    "de",
    "chuong",
    "vaccine",
    # aquaculture
    "tom",
    "ca",
    "ao",
    "be",
    "ph",
    "kiem",
    "nh3",
    "no2",
    "h2s",
    # english
    "farm",
    "crop",
    "livestock",
    "aquaculture",
}


# Environment hints
_ENV_HINT_TOKENS = {
    "moi truong",
    "o nhiem",
    "rac thai",
    "nuoc thai",
    "khi thai",
    "chat luong khong khi",
    "pm2",
    "pm10",
    "nuoc sach",
    "nuoc uong",
    "bien doi khi hau",
    "khi hau",
    "phat thai",
    "nha kinh",
    "carbon",
    "co2",
    "phu sa",
    "xam nhap man",
    "han man",
    "xoi mon",
    "dat phèn",
    "dat phen",
    "dat man",
    "rung",
    "da dang sinh hoc",
    "he sinh thai",
}


# High-precision out-of-domain keywords (short list)
_OOD_KEYWORDS = {
    # IT
    "python",
    "javascript",
    "typescript",
    "react",
    "nodejs",
    "flutter",
    "kotlin",
    "java",
    "c#",
    "dotnet",
    "sql",
    "docker",
    "kubernetes",
    "api",
    "laptop",
    "windows",
    # finance/legal/medical
    "chung khoan",
    "co phieu",
    "bitcoin",
    "crypto",
    "vay",
    "lai suat",
    "thue",
    "hop dong",
    "phap ly",
    "luat",
    "bac si",
    "benh vien",
    "don thuoc",
    # entertainment/relationships
    "tinh yeu",
    "nguoi yeu",
    "chia tay",
    "phim",
    "am nhac",
    "game",
}


_CODE_PATTERNS = [
    r"\bdef\s+\w+\s*\(",
    r"\bclass\s+\w+\s*\(",
    r"\bimport\s+\w+",
    r"\bfrom\s+\w+\s+import\b",
    r"\bconsole\.log\b",
    r"\bSELECT\b.*\bFROM\b",
    r"\bCREATE\s+TABLE\b",
    r"==|!=|<=|>=|=>",
]


_SMALLTALK_TOKENS = {
    # greetings
    "xin",
    "chao",
    "hello",
    "hi",
    "hey",
    "alo",
    "good",
    "morning",
    "afternoon",
    "evening",
    "night",
    "buoi",
    "sang",
    "trua",
    "toi",
    # address / filler
    "ban",
    "minh",
    "toi",
    "anh",
    "chi",
    "em",
    "ad",
    "admin",
    # thanks
    "cam",
    "on",
    "thanks",
    "thank",
    "you",
    # bye
    "bye",
    "goodbye",
    "tam",
    "biet",
    "hen",
    "gap",
    "lai",
    "chuc",
    "ngu",
    "ngon",
    # acknowledgement
    "ok",
    "oke",
    "okay",
    "da",
    "roi",
    "vang",
    "duoc",
}


_GENERIC_HELP_PHRASES = {
    "giup",
    "giup voi",
    "giup minh",
    "giup toi",
    "can giup",
    "can ho tro",
    "ho tro",
    "support",
    "help",
    "pls help",
    "plz help",
    "tu van",
    "tu van giup",
    "cho hoi",
    "cho minh hoi",
    "minh hoi",
    "hoi chut",
    "hoi cai",
    "cau gi giup",
}


_GENERIC_HELP_EXCLUDE_PHRASES = {
    # common school/homework/general OOD phrases (keep phrase-based to avoid VN accent collisions)
    "giai toan",
    "lam van",
    "viet van",
    "lam bai",
    "bai tap",
    "tieng anh",
    "vat ly",
    "hoa hoc",
    "homework",
    "essay",
}


_GENERIC_HELP_EXCLUDE_TOKENS = {
    # keep token exclusions very conservative
    "code",
    "lap",
    "trinh",
}


def _is_generic_help_request(text_norm: str) -> bool:
    """Return True for vague generic "help me" asks.

    Product requirement:
    - Do NOT refuse these.
    - Let the app ask a clarification like "Bạn cần giúp gì về nông nghiệp?".
    """

    if not text_norm:
        return False

    t = text_norm.strip()
    if not t:
        return False

    if len(t) > 90:
        return False

    toks = _tokenize(t)
    if not toks:
        return False

    # Avoid turning obvious OOD requests into "clarify".
    if any(p in t for p in _GENERIC_HELP_EXCLUDE_PHRASES):
        return False
    if any(tok in _GENERIC_HELP_EXCLUDE_TOKENS for tok in toks):
        return False

    # Phrase match first.
    if any(p in t for p in _GENERIC_HELP_PHRASES):
        return True

    # Token-based fallback.
    if any(tok in {"giup", "help", "support"} for tok in toks):
        return True

    # "hỗ trợ" -> "ho tro"
    if "ho" in toks and "tro" in toks:
        return True

    return False


def _is_smalltalk_only(text_norm: str) -> bool:
    """Return True for short greeting/thanks/bye messages.

    This avoids refusing harmless smalltalk even if the greeting detector
    upstream misses.
    """

    if not text_norm:
        return False
    t = text_norm.strip()
    if not t:
        return False

    # Keep it conservative: only short messages.
    if len(t) > 80:
        return False

    toks = _tokenize(t)
    if not toks:
        return False

    if len(toks) > 10:
        return False

    core = {"chao", "hello", "hi", "hey", "alo", "cam", "thanks", "thank", "bye", "tam", "ok", "oke", "okay"}
    if not any(tok in core for tok in toks):
        return False

    return all(tok in _SMALLTALK_TOKENS for tok in toks)


def _contains_any_phrase(text_norm: str, phrases: set[str]) -> bool:
    return any(p in text_norm for p in phrases)


def is_in_domain(text: str) -> bool:
    if not isinstance(text, str):
        return False
    norm = _normalize(text)
    if not norm:
        return False

    toks = [t for t in _tokenize(norm) if t and t not in _STOPWORDS]

    # token-based
    if any(t in _AGRI_HINT_TOKENS for t in toks):
        return True

    # phrase-based (multiword env hints)
    if _contains_any_phrase(norm, _ENV_HINT_TOKENS):
        return True

    # common shorthand for environment
    if re.search(r"\b(pm2\.5|pm10|co2)\b", norm):
        return True

    return False


def should_refuse_rule(text: str) -> bool:
    """Heuristic out-of-domain detector.

    Returns True when the message is outside agriculture/environment.
    """

    if not isinstance(text, str):
        return False

    msg = text.strip()
    if not msg:
        return False

    norm = _normalize(msg)

    # Do not refuse greetings/thanks/bye.
    if _is_smalltalk_only(norm):
        return False

    # If it's in-domain, don't refuse.
    if is_in_domain(norm):
        return False

    # Code-like prompts: refuse.
    if any(re.search(p, norm, flags=re.IGNORECASE) for p in _CODE_PATTERNS):
        return True

    # Strong out-of-domain keywords: refuse.
    if any(kw in norm for kw in _OOD_KEYWORDS):
        return True

    # Vague generic "help me" requests: do NOT refuse; downstream can ask clarification.
    if _is_generic_help_request(norm):
        return False

    # Otherwise: if it looks like a normal question/request but has no domain hint, refuse.
    # (This matches the user's requirement: outside agriculture/environment => refuse.)
    if "?" in norm:
        return True

    # Short generic asks like "giup minh" / "tu van" without domain hint => refuse.
    toks = _tokenize(norm)
    if len(toks) <= 6:
        return True

    return True


@lru_cache(maxsize=1)
def _load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        for row in data:
            if isinstance(row, dict) and "text" in row and "label" in row:
                out.append(row)
        return out
    except Exception:
        return []


def _resolve_model_path() -> Optional[str]:
    source = (os.environ.get("DOMAIN_GUARD_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "off", "local"}:
        source = "auto"

    if source == "off":
        return None

    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH

    return None


def _predict_proba_out_of_domain_ml(text: str) -> Optional[float]:
    """Return P(out_of_domain) if model is available."""

    try:
        model_path = _resolve_model_path()
        if not model_path:
            return None

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        clf = model.get("classifier")
        if clf is None:
            return None

        from sklearn.feature_extraction.text import HashingVectorizer

        vec_cfg = model.get("vectorizer") or {}
        vectorizer = HashingVectorizer(
            n_features=int(vec_cfg.get("n_features", 2**16)),
            alternate_sign=False,
            ngram_range=tuple(vec_cfg.get("ngram_range", (1, 2))),
            norm=str(vec_cfg.get("norm", "l2")),
        )

        X = vectorizer.transform([str(text)])

        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X)[0]
            classes = list(getattr(clf, "classes_", []))
            if 1 in classes:
                idx = classes.index(1)
                return float(proba[idx])

        if hasattr(clf, "decision_function"):
            s = float(clf.decision_function(X)[0])
            import math

            return 1.0 / (1.0 + math.exp(-s))

        return None
    except Exception:
        return None


def should_refuse(text: str) -> bool:
    """Final decision: refuse if out-of-domain."""

    try:
        norm = _normalize(str(text))
    except Exception:
        norm = ""

    # Never refuse greetings/thanks/bye.
    if _is_smalltalk_only(norm):
        return False

    # Never refuse vague generic help requests; steer to clarification instead.
    if _is_generic_help_request(norm):
        return False

    # Rule-first: high confidence.
    if should_refuse_rule(text):
        return True

    # ML fallback (only when model exists)
    p = _predict_proba_out_of_domain_ml(text)
    if p is None:
        return False

    try:
        thr = float(os.environ.get("DOMAIN_GUARD_THRESHOLD") or "0.65")
    except Exception:
        thr = 0.65

    return p >= thr


def generate_refusal_reply(user_text: str = "") -> str:
    """Generate a short, polite refusal message."""

    # Keep it short and consistent.
    variants = [
        "Xin lỗi bạn, mình chỉ hỗ trợ các câu hỏi thuộc lĩnh vực nông nghiệp và môi trường.",
        "Mình không thể hỗ trợ chủ đề này vì nằm ngoài phạm vi nông nghiệp/môi trường.",
        "Chủ đề này ngoài phạm vi nông nghiệp và môi trường nên mình xin phép từ chối trả lời.",
    ]
    follow = (
        "\n\nBạn có thể hỏi theo hướng nông nghiệp/môi trường, ví dụ: bệnh cây, dinh dưỡng, kỹ thuật trồng/nuôi, "
        "hoặc chất lượng nước/ô nhiễm/biến đổi khí hậu."
    )
    return random.choice(variants) + follow


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
        raise ValueError("Empty domain_guard dataset")

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
                "type": "hashing_sgd_domain_guard_v1",
                "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
                "classifier": clf,
                "label_meaning": {"0": "in_domain", "1": "out_of_domain"},
            },
            f,
        )

    print(f"✅ samples: {len(texts)}")
    print(f"✅ train_acc (sanity): {acc:.3f}")
    print(f"💾 saved: {os.path.abspath(args.model_out)}")
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Domain guard (agriculture/environment only)")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--seed", type=int, default=42)

    sub = p.add_subparsers(dest="cmd")

    p_train = sub.add_parser("train", help="Train domain guard model")
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
