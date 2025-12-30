"""complexity_scope.py

ML + rule-first router for complex questions **within agriculture/environment**.

Goal
- Detect prompts that are complex/analytical (multi-part, planning, comparison, "phân tích", ...)
    so we can skip local clarification heuristics and go straight to the LLM.

Important
- Out-of-domain prompts (NOT agriculture/environment) should be handled by `domain_guard.py`
    (refuse locally). Therefore, this module intentionally does NOT route out-of-domain prompts.

Dataset
- dataset/complexity_scope.json   (text,label)
    label 0 = not complex
    label 1 = complex (within agriculture/environment)

Model
- model/complexity_scope.pkl

Env vars (optional)
- COMPLEXITY_SCOPE_MODEL_SOURCE=auto|off|local (default: auto)
- COMPLEXITY_SCOPE_THRESHOLD=0.65              (default: 0.65)  # threshold on P(route_to_llm)

Notes
- This is intentionally conservative: it should only force-routing when fairly confident.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET_PATH = os.path.join(HERE, "dataset", "complexity_scope.json")
DEFAULT_MODEL_DIR = os.path.join(HERE, "model")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "complexity_scope.pkl")


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
    # "là" -> "la" collides with "lá". Avoid using it as a signal.
    "la",
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


# Minimal agriculture hints (keep *specific* to avoid false positives).
_AGRI_HINT_TOKENS = {
    # crop
    "lua",
    "gao",
    "cay",
    "vuon",
    "ruong",
    "trong",
    "gieo",
    "phan",
    "bon",
    "npk",
    "thuoc",
    "sau",
    "benh",
    "nam",
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
    "nuoc",
    "ph",
    "kiem",
    "nh3",
    "no2",
    "h2s",
}


_ENV_HINT_PHRASES = {
    "moi truong",
    "o nhiem",
    "rac thai",
    "nuoc thai",
    "khi thai",
    "pm2",
    "pm10",
    "bien doi khi hau",
    "khi hau",
    "phat thai",
    "nha kinh",
    "carbon",
    "co2",
    "xam nhap man",
    "han man",
    "dat phen",
    "dat man",
    "he sinh thai",
}


# Complex/analytical verbs (used softly; combined with length/structure checks)
_COMPLEX_VERBS = {
    "phan tich",
    "so sanh",
    "danh gia",
    "toi uu",
    "mo hinh",
    "du bao",
    "chien luoc",
    "ke hoach",
    "tinh toan",
    "thuat toan",
    "chung minh",
    "lap luan",
    "nghien cuu",
}


def _is_in_domain(text_norm: str) -> bool:
    if not text_norm:
        return False
    toks = [t for t in _tokenize(text_norm) if t and t not in _STOPWORDS]
    if any(t in _AGRI_HINT_TOKENS for t in toks):
        return True
    if any(p in text_norm for p in _ENV_HINT_PHRASES):
        return True
    if re.search(r"\b(pm2\.5|pm10|co2)\b", text_norm):
        return True
    return False


def _is_complex_structure(text_norm: str) -> bool:
    if not text_norm:
        return False

    # Multiple questions in one message.
    qmarks = text_norm.count("?")
    if qmarks >= 2:
        return True

    # Enumerations / multi-part requirements.
    if re.search(r"\b(1\)|2\)|3\)|-\s|\*\s)\b", text_norm):
        return True

    # Many clauses/sentences.
    sentence_like = len(re.findall(r"[\.!?]", text_norm))
    if sentence_like >= 3:
        return True

    # Soft: complex verbs + sufficient length.
    if len(text_norm) >= 90:
        for v in _COMPLEX_VERBS:
            if v in text_norm:
                return True

    return False


def should_route_to_llm_rule(text: str) -> bool:
    """Heuristic router.

    Returns True if the prompt is obviously code/IT, out-of-scope, or complex enough
    that we should skip local clarification models.
    """

    if not isinstance(text, str):
        return False

    msg = text.strip()
    if not msg:
        return False

    norm = _normalize(msg)

    # Only consider complexity routing within agriculture/environment.
    # Out-of-domain prompts should be refused by domain_guard.
    if not _is_in_domain(norm):
        return False

    # Very long in-domain prompts are already detailed/complex; route.
    if len(norm) >= 280:
        return True

    # Complex structure / analytical intent: route.
    if _is_complex_structure(norm):
        return True

    return False


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
    source = (os.environ.get("COMPLEXITY_SCOPE_MODEL_SOURCE") or "auto").strip().lower()
    if source not in {"auto", "off", "local"}:
        source = "auto"

    if source == "off":
        return None

    if os.path.exists(DEFAULT_MODEL_PATH) and os.path.getsize(DEFAULT_MODEL_PATH) > 0:
        return DEFAULT_MODEL_PATH

    return None


def _predict_proba_route_to_llm_ml(text: str) -> Optional[float]:
    """Return P(route_to_llm) if model is available."""

    try:
        model_path = _resolve_model_path()
        if not model_path:
            return None

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        clf = model.get("classifier")
        if clf is None:
            return None

        # training uses HashingVectorizer; keep same transform config.
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
            # class index mapping can vary; detect index for label=1
            classes = list(getattr(clf, "classes_", []))
            if 1 in classes:
                idx = classes.index(1)
                return float(proba[idx])

        # fallback: decision_function + sigmoid-ish mapping
        if hasattr(clf, "decision_function"):
            s = float(clf.decision_function(X)[0])
            # logistic
            import math

            return 1.0 / (1.0 + math.exp(-s))

        return None
    except Exception:
        return None


def should_route_to_llm(text: str) -> bool:
    """Return True if we should route straight to LLM and skip local clarification."""

    # Rule-first: high precision.
    if should_route_to_llm_rule(text):
        return True

    # ML fallback: only if model exists.
    p = _predict_proba_route_to_llm_ml(text)
    if p is None:
        return False

    try:
        thr = float(os.environ.get("COMPLEXITY_SCOPE_THRESHOLD") or "0.65")
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
        raise ValueError("Empty complexity_scope dataset")

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
                "type": "hashing_sgd_complexity_scope_v1",
                "vectorizer": {"n_features": 2**16, "ngram_range": (1, 2), "norm": "l2"},
                "classifier": clf,
                "label_meaning": {"0": "in_scope_simple", "1": "route_to_llm"},
            },
            f,
        )

    print(f"✅ samples: {len(texts)}")
    print(f"✅ train_acc (sanity): {acc:.3f}")
    print(f"💾 saved: {os.path.abspath(args.model_out)}")
    return 0


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Complexity/out-of-scope router")
    p.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    p.add_argument("--seed", type=int, default=42)

    sub = p.add_subparsers(dest="cmd")

    p_train = sub.add_parser("train", help="Train complexity/scope router model")
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
