"""weather_timeframe.py

Optional ML + light rules to infer timeframe for weather questions.

Goal
- Given a user message (already determined to be weather-related), infer *when* they mean:
  - current (now/today)
  - forecast for a specific near day (tomorrow, day-after-tomorrow)
  - history (yesterday, day-before-yesterday)
  - coarse ranges (this week, next week, last week)

This module is designed to be safe:
- It can run without an ML model (returns None unless obvious rule matches).
- If ML is available, it only returns a timeframe when confidence is high.

Dataset
- dataset/weather_timeframe.json
  label is a string class name:
    current | forecast_tomorrow | forecast_day_after | history_yesterday | history_day_before
    forecast_range | history_range

Model
- model/weather_timeframe.pkl

Env vars (optional)
- WEATHER_TIMEFRAME_MODEL_SOURCE=auto|off|local (default: auto)
- WEATHER_TIMEFRAME_THRESHOLD=0.55             (default: 0.55)

"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import unicodedata
from typing import Any, Dict, List, Optional


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "weather_timeframe.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "weather_timeframe.pkl")

_AUTO_TRAIN_TRIED = False


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def _load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("weather_timeframe dataset must be a JSON list")
    return data


def _resolve_model_path() -> Optional[str]:
    source = (os.environ.get("WEATHER_TIMEFRAME_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "off", "local"}:
        source = "auto"

    if source == "off":
        return None

    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH

    auto_train = (os.environ.get("WEATHER_TIMEFRAME_AUTO_TRAIN") or "1").strip().lower()
    if auto_train in {"0", "false", "no", "off"}:
        return None

    global _AUTO_TRAIN_TRIED
    if _AUTO_TRAIN_TRIED:
        return None
    _AUTO_TRAIN_TRIED = True

    try:
        data = _load_dataset(DEFAULT_DATASET_PATH)
        texts: List[str] = []
        labels: List[str] = []

        allowed = {
            "current",
            "forecast_tomorrow",
            "forecast_day_after",
            "history_yesterday",
            "history_day_before",
            "forecast_range",
            "history_range",
        }

        for row in data:
            t = str(row.get("text") or "").strip()
            y = str(row.get("label") or "").strip()
            if not t or not y:
                continue
            if y not in allowed:
                continue
            texts.append(t)
            labels.append(y)

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
            "labels": sorted(set(labels)),
            "meta": {"samples": len(texts), "seed": 42, "auto_trained": True},
        }

        with open(DEFAULT_MODEL_PATH, "wb") as f:
            pickle.dump(payload, f)

        if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
            return DEFAULT_MODEL_PATH
    except Exception:
        return None

    return None


def _rule_timeframe(text_norm: str) -> Optional[Dict[str, Any]]:
    """Return a timeframe dict if an obvious rule matches, else None."""

    if not text_norm:
        return None

    # NOTE: numeric ranges are handled in app.py first; we keep only coarse phrases here.

    # Past
    if "tuan truoc" in text_norm:
        return {"type": "history_range", "start_offset": -7, "days": 7, "label": "tuần trước"}
    if "hom qua" in text_norm:
        return {"type": "history_day", "day_offset": -1, "label": "hôm qua"}
    if "hom kia" in text_norm or "bua hom" in text_norm or "hom truoc" in text_norm:
        return {"type": "history_day", "day_offset": -2, "label": "hôm kia"}

    # Future
    if "tuan toi" in text_norm or "tuan sau" in text_norm:
        return {"type": "forecast_range", "start_offset": 1, "days": 7, "label": "tuần tới"}

    # Day-after-tomorrow variants (check before generic "mai")
    if "ngay kia" in text_norm or "ngay mot" in text_norm or "mai mot" in text_norm:
        return {"type": "forecast_day", "day_offset": 2, "label": "ngày kia"}

    if "ngay mai" in text_norm or re.search(r"\bmai\b", text_norm) or "du bao" in text_norm or "forecast" in text_norm:
        return {"type": "forecast_day", "day_offset": 1, "label": "ngày mai"}

    # Current-ish
    if "hom nay" in text_norm or "bay gio" in text_norm or "hien tai" in text_norm:
        return {"type": "current"}

    return None


def _predict_ml(text: str) -> Optional[Dict[str, Any]]:
    try:
        model_path = _resolve_model_path()
        if not model_path:
            return None

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        clf = model.get("classifier")
        if clf is None:
            return None

        labels = model.get("labels") or []

        from sklearn.feature_extraction.text import HashingVectorizer

        vec_cfg = model.get("vectorizer") or {}
        vectorizer = HashingVectorizer(
            n_features=int(vec_cfg.get("n_features", 2**16)),
            alternate_sign=False,
            ngram_range=tuple(vec_cfg.get("ngram_range", (1, 2))),
            norm=str(vec_cfg.get("norm", "l2")),
        )

        X = vectorizer.transform([str(text)])

        if not hasattr(clf, "predict_proba"):
            return None

        proba = clf.predict_proba(X)[0]
        classes = list(getattr(clf, "classes_", []))
        if not classes:
            return None

        best_idx = int(max(range(len(proba)), key=lambda i: proba[i]))
        best_class = classes[best_idx]
        best_p = float(proba[best_idx])

        try:
            thr = float(os.environ.get("WEATHER_TIMEFRAME_THRESHOLD") or "0.55")
        except Exception:
            thr = 0.55

        if best_p < thr:
            return None

        label_name = str(best_class)
        if labels and label_name in labels:
            # ok
            pass

        # Map class -> timeframe dict
        if label_name == "current":
            return {"type": "current"}
        if label_name == "forecast_tomorrow":
            return {"type": "forecast_day", "day_offset": 1, "label": "ngày mai"}
        if label_name == "forecast_day_after":
            return {"type": "forecast_day", "day_offset": 2, "label": "ngày kia"}
        if label_name == "history_yesterday":
            return {"type": "history_day", "day_offset": -1, "label": "hôm qua"}
        if label_name == "history_day_before":
            return {"type": "history_day", "day_offset": -2, "label": "hôm kia"}
        if label_name == "forecast_range":
            return {"type": "forecast_range", "start_offset": 1, "days": 7, "label": "tuần tới"}
        if label_name == "history_range":
            return {"type": "history_range", "start_offset": -7, "days": 7, "label": "tuần trước"}

        return None
    except Exception:
        return None


def predict_timeframe(text: str) -> Optional[Dict[str, Any]]:
    """Return timeframe dict or None (unknown)."""

    norm = _normalize(text)
    # If rules already know, return immediately.
    rule = _rule_timeframe(norm)
    if rule is not None:
        return rule

    return _predict_ml(text)


def cli_train(args: argparse.Namespace) -> int:
    data = _load_dataset(args.dataset)

    texts: List[str] = []
    labels: List[str] = []

    allowed = {
        "current",
        "forecast_tomorrow",
        "forecast_day_after",
        "history_yesterday",
        "history_day_before",
        "forecast_range",
        "history_range",
    }

    for row in data:
        t = str(row.get("text") or "").strip()
        y = str(row.get("label") or "").strip()
        if not t or not y:
            continue
        if y not in allowed:
            continue
        texts.append(t)
        labels.append(y)

    if not texts:
        raise ValueError("Empty weather_timeframe dataset")

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

    train_acc = float(clf.score(X, labels))

    os.makedirs(DEFAULT_MODEL_DIR, exist_ok=True)
    payload = {
        "classifier": clf,
        "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
        "labels": sorted(set(labels)),
        "meta": {
            "samples": len(texts),
            "train_acc": train_acc,
            "seed": 42,
        },
    }

    with open(args.model, "wb") as f:
        pickle.dump(payload, f)

    print(
        f"✅ weather_timeframe trained | samples={len(texts)} | train_acc(sanity)={train_acc:.3f} | saved={args.model}"
    )
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Weather timeframe detector")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--model", default=DEFAULT_MODEL_PATH)
    p.add_argument("--train", action="store_true")
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()
    if args.train:
        return cli_train(args)

    samples = [
        "Hôm qua trời có mưa không?",
        "Ngày kia có nắng không?",
        "Tuần trước thời tiết thế nào?",
        "Dự báo thời tiết tuần tới",
        "Thời tiết bây giờ",
    ]

    for s in samples:
        print(s, "->", predict_timeframe(s))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
