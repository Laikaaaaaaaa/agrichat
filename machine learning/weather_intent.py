"""weather_intent.py

Rule-first + optional ML intent detector for weather/climate questions.

Goal
- Detect when the user is asking about weather / climate ("thời tiết", "khí hậu", "hôm nay mưa không", ...)
- Used to route the request to WeatherAPI (instead of LLM).

Dataset
- dataset/weather_intent.json
  label 0 = not weather
  label 1 = weather/climate

Model
- model/weather_intent.pkl

Env vars (optional)
- WEATHER_INTENT_MODEL_SOURCE=auto|off|local   (default: auto)
- WEATHER_INTENT_THRESHOLD=0.65               (default: 0.65)  # threshold on P(weather)

Notes
- We keep rule-first detection fairly strict to avoid stealing agriculture queries.
- ML is a fallback to catch paraphrases.
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
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "weather_intent.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "weather_intent.pkl")

_AUTO_TRAIN_TRIED = False


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


_WEATHER_KEYWORDS = {
    # keep phrases specific to weather to avoid VN collisions like "mua" (buy)
    "thoi tiet",
    "thoi tiet hom nay",
    "du bao",
    "du bao thoi tiet",
    "khi hau",
    "bien doi khi hau",
    "forecast",
    "weather",
    "ap thap",
    "ap thap nhiet doi",
    "mua rao",
    "mua bao",
    "mua lon",
    "troi mua",
    "troi nang",
    "troi lanh",
    "troi nong",
    "troi ret",
    "troi am u",
    "co mua",
    "mua khong",
    "nhiet do",
    "bao nhieu do",
    "bao nhieu do c",
    "do am",
    "chi so uv",
    "uv index",
    "suong mu",
    "gio mua",
}

_WEATHER_HINT_TOKENS = {
    "thoi",
    "tiet",
    "khi",
    "hau",
    "du",
    "bao",
    "mua",
    "nang",
    "nhiet",
    "am",
    "gio",
    "uv",
    "ap",
    "thap",
    "suong",
    "mu",
    "ret",
    "nong",
    "lanh",
    "dông",
    "dong",
    "troi",
}

# If these appear, it's likely agriculture/aquaculture water, not weather intent.
_AGRI_WATER_TOKENS = {
    "ao",
    "be",
    "tom",
    "ca",
    "ph",
    "kiem",
    "nh3",
    "no2",
    "h2s",
    "tảo",
    "tao",
    "nuoc ao",
    "nuoc",
}


def is_weather_intent_rule(text: str) -> bool:
    t = _normalize(text)
    if not t:
        return False

    # Keep greetings etc out.
    if len(t) <= 3:
        return False

    # Fast phrase checks
    for p in _WEATHER_KEYWORDS:
        if p in t:
            # Avoid stealing typical aquaculture water-quality prompts like "nước ao xanh".
            toks = set(_tokenize(t))
            if "ao" in toks and "nuoc" in toks and "thoi" not in toks and "tiet" not in toks:
                return False
            return True

    toks = _tokenize(t)
    if not toks:
        return False

    # Basic heuristic: must contain at least 2 weather-ish tokens
    hit = sum(1 for tok in toks if tok in _WEATHER_HINT_TOKENS)
    if hit >= 2:
        # But if it looks like aquaculture water quality (ao/pH/kiềm/...) and no explicit weather phrase, ignore.
        if any(tok in _AGRI_WATER_TOKENS for tok in toks) and not ("thoi" in toks and "tiet" in toks):
            return False
        return True

    return False


def _load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("weather_intent dataset must be a JSON list")
    return data


def _resolve_model_path() -> Optional[str]:
    source = (os.environ.get("WEATHER_INTENT_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "off", "local"}:
        source = "auto"

    if source == "off":
        return None

    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH

    # Many deployments ignore *.pkl; allow an opt-in runtime auto-train to keep ML enabled.
    auto_train = (os.environ.get("WEATHER_INTENT_AUTO_TRAIN") or "1").strip().lower()
    if auto_train in {"0", "false", "no", "off"}:
        return None

    global _AUTO_TRAIN_TRIED
    if _AUTO_TRAIN_TRIED:
        return None
    _AUTO_TRAIN_TRIED = True

    try:
        data = _load_dataset(DEFAULT_DATASET_PATH)

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
            return None

        from sklearn.feature_extraction.text import HashingVectorizer
        from sklearn.linear_model import SGDClassifier

        vectorizer = HashingVectorizer(
            n_features=2**16,
            alternate_sign=False,
            ngram_range=(1, 2),
            norm="l2",
        )

        X = vectorizer.transform(texts)
        clf = SGDClassifier(loss="log_loss", alpha=1e-5, random_state=42, max_iter=2000, tol=1e-3)
        clf.fit(X, labels)

        os.makedirs(DEFAULT_MODEL_DIR, exist_ok=True)
        payload = {
            "classifier": clf,
            "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
            "meta": {"samples": len(texts), "seed": 42, "auto_trained": True},
        }

        with open(DEFAULT_MODEL_PATH, "wb") as f:
            pickle.dump(payload, f)

        if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
            return DEFAULT_MODEL_PATH
    except Exception:
        return None

    return None


def _predict_proba_ml(text: str) -> Optional[float]:
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


def _has_weather_signal(text_norm: str) -> bool:
    """Quick guard so ML doesn't misclassify generic chat as weather."""

    if not text_norm:
        return False

    # If any specific weather phrase appears, treat as signal.
    for p in _WEATHER_KEYWORDS:
        if p in text_norm:
            return True

    toks = _tokenize(text_norm)
    if not toks:
        return False

    core = {
        "thoi",
        "tiet",
        "khi",
        "hau",
        "du",
        "bao",
        "mua",  # rain (can also be buy, but as a single signal it's okay; rule handles phrase collisions)
        "nang",
        "troi",
        "nhiet",
        "am",
        "gio",
        "uv",
        "ap",
        "thap",
        "suong",
        "ret",
        "lanh",
        "nong",
        "dong",
    }

    return any(t in core for t in toks)


def is_weather_intent(text: str) -> bool:
    if is_weather_intent_rule(text):
        return True

    norm = _normalize(text)
    if not _has_weather_signal(norm):
        return False

    p = _predict_proba_ml(text)
    if p is None:
        return False

    try:
        thr = float(os.environ.get("WEATHER_INTENT_THRESHOLD") or "0.65")
    except Exception:
        thr = 0.65

    return p >= thr


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
        raise ValueError("Empty weather_intent dataset")

    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier

    vectorizer = HashingVectorizer(
        n_features=2**16,
        alternate_sign=False,
        ngram_range=(1, 2),
        norm="l2",
    )

    X = vectorizer.transform(texts)
    clf = SGDClassifier(loss="log_loss", alpha=1e-5, random_state=42, max_iter=2000, tol=1e-3)
    clf.fit(X, labels)

    # sanity train acc
    train_acc = float(clf.score(X, labels))

    os.makedirs(DEFAULT_MODEL_DIR, exist_ok=True)
    payload = {
        "classifier": clf,
        "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
        "meta": {
            "samples": len(texts),
            "train_acc": train_acc,
            "seed": 42,
        },
    }

    with open(args.model, "wb") as f:
        pickle.dump(payload, f)

    print(f"✅ weather_intent trained | samples={len(texts)} | train_acc(sanity)={train_acc:.3f} | saved={args.model}")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Weather intent detector")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--model", default=DEFAULT_MODEL_PATH)
    p.add_argument("--train", action="store_true")
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()
    if args.train:
        return cli_train(args)

    # quick smoke test
    samples = [
        "Thời tiết hôm nay thế nào?",
        "Nhiệt độ bao nhiêu độ C?",
        "nước ao xanh",
        "tư vấn mua điện thoại",
    ]
    for s in samples:
        print(s, "->", is_weather_intent(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
