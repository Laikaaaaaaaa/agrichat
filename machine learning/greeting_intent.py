"""greeting_intent.py

Lightweight greeting intent detector + canned greeting replies.

Goal:
- Detect when user only greets ("xin chào", "hello", "hi", ...)
- Reply with a friendly, pre-written greeting WITHOUT calling LLM APIs

Design:
- Rule-first (fast, deterministic, no dependencies).
- Optional ML classifier (sklearn) for fuzzy detection if a trained model exists.

Files:
- Dataset: dataset/greeting_intent.json
- Model:   model/greeting_intent.pkl

Env vars (optional):
- GREETING_INTENT_MODEL_SOURCE=auto|off|local   (default: auto)
- GREETING_INTENT_THRESHOLD=0.65               (default: 0.65)
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import random
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "greeting_intent.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "greeting_intent.pkl")


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
    # Keep VN words and ascii words; split on non-word.
    parts = re.split(r"[^\w]+", text_norm)
    return [p for p in parts if p]


_GREET_PHRASES = {
    "xin chao",
    "chao",
    "chao ban",
    "chao ban nhe",
    "chao ad",
    "chao admin",
    "hello",
    "hi",
    "hey",
    "yo",
    "alo",
    "good morning",
    "good afternoon",
    "good evening",
    "morning",
    "evening",
}

# Tokens allowed to appear together with greetings without being treated as a "real question"
_ALLOWED_FILLER_TOKENS = {
    "xin",
    "chao",
    "hello",
    "hi",
    "hey",
    "yo",
    "alo",
    "good",
    "morning",
    "afternoon",
    "evening",
    "ban",
    "b",
    "ad",
    "admin",
    "ai",
    "agrisense",
    "agrichat",
    "sense",
    "oi",
    "a",
    "ah",
    "ha",
    "da",
    "d",
    "nhe",
    "nha",
    "a",
    "ạ",
    "ak",
    "kk",
}

# If these appear, it's very likely not a pure greeting.
_AGRI_HINT_TOKENS = {
    "heo",
    "ga",
    "bo",
    "tom",
    "ca",
    "lua",
    "cay",
    "benh",
    "trieu",
    "chung",
    "dau",
    "chan",
    "mua",
    "thuoc",
    "phun",
    "phan",
    "tieu",
    "chay",
    "sot",
}


def is_greeting_rule(text: str) -> bool:
    """Return True if the message looks like a greeting-only message."""

    t = _normalize(text)
    if not t:
        return False

    # Strip common punctuation/emoji wrappers.
    t_clean = re.sub(r"[\!\?\.,:;\-_/\\()\[\]{}\"'`~]+", " ", t)
    t_clean = re.sub(r"\s+", " ", t_clean).strip()
    if not t_clean:
        return False

    # Fast phrase match.
    if t_clean in _GREET_PHRASES:
        return True

    toks = _tokenize(t_clean)
    if not toks:
        return False

    # If message is long, assume it's not just a greeting.
    if len(t_clean) > 40 and len(toks) > 6:
        return False

    # Must contain at least one greeting signal.
    has_greet_signal = any(tok in {"chao", "hello", "hi", "hey", "alo"} for tok in toks) or (
        "xin" in toks and "chao" in toks
    )
    if not has_greet_signal:
        return False

    # If agriculture hint tokens appear, treat as non-greeting (likely a real question).
    if any(tok in _AGRI_HINT_TOKENS for tok in toks):
        return False

    # Allow only filler tokens + greeting tokens.
    unknown = [tok for tok in toks if tok not in _ALLOWED_FILLER_TOKENS]
    if not unknown:
        return True

    # If there are unknown tokens, still allow if it's basically just "chào" + name.
    # Example: "chào Quang" / "hello Minh"
    if len(toks) <= 4 and len(unknown) <= 1:
        return True

    return False


def _load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Greeting dataset must be a JSON list")
    return data


def _resolve_model_path() -> Optional[str]:
    source = (os.environ.get("GREETING_INTENT_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "off", "local"}:
        source = "auto"

    if source == "off":
        return None

    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH

    return None


def _predict_proba_ml(text: str) -> Optional[float]:
    """Return P(greeting) if model is available."""
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
            # classes are [0,1] where 1 means greeting
            # Find index of class 1
            classes = list(getattr(clf, "classes_", []))
            if 1 in classes:
                idx = classes.index(1)
                return float(proba[idx])
            return float(proba[-1])

        # Fallback: decision function -> sigmoid-ish
        if hasattr(clf, "decision_function"):
            import math

            score = float(clf.decision_function(X)[0])
            return 1.0 / (1.0 + math.exp(-score))

        return None
    except Exception:
        return None


def is_greeting(text: str) -> bool:
    """Rule-first greeting detection with optional ML fallback."""

    if is_greeting_rule(text):
        return True

    proba = _predict_proba_ml(text)
    if proba is None:
        return False

    try:
        thr = float(os.environ.get("GREETING_INTENT_THRESHOLD", "0.65"))
    except Exception:
        thr = 0.65

    # Extra guard: if agriculture hints exist, do not treat as greeting.
    toks = _tokenize(_normalize(text))
    if any(tok in _AGRI_HINT_TOKENS for tok in toks):
        return False

    return proba >= thr


_GREET_REPLIES = [
    "👋 Chào bạn! Mình là AgriSense AI. Bạn cần mình hỗ trợ vấn đề nông nghiệp nào hôm nay?",
    "Xin chào! 🌾 Bạn đang cần tư vấn cây trồng hay vật nuôi vậy?",
    "Hello bạn! 👋 Mình sẵn sàng hỗ trợ. Bạn mô tả tình trạng/triệu chứng giúp mình nhé.",
    "Chào bạn 😊 Bạn muốn hỏi về bệnh, dinh dưỡng hay kỹ thuật chăm sóc?",
    "Chào bạn! 🐟🐔🌱 Bạn đang nuôi/trồng gì để mình tư vấn đúng hơn?",
    "Hi! 👋 Có vấn đề gì về mùa mưa/nắng, sâu bệnh hay môi trường nuôi không bạn?",
    "Xin chào bạn ạ! 😊 Bạn cho mình biết khu vực (tỉnh/thành) để tư vấn sát thực tế hơn nhé.",
    "Chào bạn! 🌿 Mình có thể giúp chẩn đoán sơ bộ và gợi ý xử lý. Bạn nói rõ tình trạng hiện tại nha.",
    "Hello! 🌾 Bạn cần lịch thời vụ, cách bón phân hay xử lý bệnh/sâu hại?",
    "Chào bạn 👋 Bạn cứ hỏi tự nhiên, mình trả lời ngắn gọn – dễ làm theo nhé!",
]


def generate_greeting_reply() -> str:
    return random.choice(_GREET_REPLIES)


def cli_train(args: argparse.Namespace) -> int:
    """Train a tiny intent classifier (greeting vs other)."""

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
        raise ValueError("Empty greeting dataset")

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

    # quick sanity
    pred = clf.predict(X)
    acc = sum(1 for p, y in zip(pred, labels) if int(p) == int(y)) / max(1, len(labels))

    os.makedirs(os.path.dirname(os.path.abspath(args.model_out)), exist_ok=True)
    with open(args.model_out, "wb") as f:
        pickle.dump(
            {
                "type": "hashing_sgd_intent_v1",
                "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
                "classifier": clf,
            },
            f,
        )

    print(f"✅ samples: {len(texts)}")
    print(f"✅ train_acc (sanity): {acc:.3f}")
    print(f"💾 saved: {os.path.abspath(args.model_out)}")
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Greeting intent detector + canned replies")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--seed", type=int, default=42)

    sub = p.add_subparsers(dest="cmd")

    p_train = sub.add_parser("train", help="Train greeting intent model")
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
