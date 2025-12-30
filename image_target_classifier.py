"""image_target_classifier.py

Multiclass ML classifier to identify *what* image the user wants.
This is separate from `image_intent_classifier.py` (which detects whether the user wants images at all).

Design goals:
- Vietnamese-friendly (diacritics normalization)
- Lightweight, fast inference (TF-IDF + LogisticRegression)
- Outputs: (label, confidence, canonical_query)

If the trained model file is missing, it will bootstrap-train from the bundled dataset.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


class DiacriticsNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return text
        nfd = unicodedata.normalize("NFD", text)
        return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


@dataclass(frozen=True)
class TargetPrediction:
    label: str
    confidence: float
    canonical_query: str


class ImageTargetClassifier:
    def __init__(
        self,
        model_path: Optional[str] = None,
        dataset_path: Optional[str] = None,
    ):
        base_dir = os.path.dirname(__file__)
        self.model_path = model_path or os.path.join(base_dir, "models", "image_target_classifier.pkl")
        self.dataset_path = dataset_path or os.path.join(base_dir, "datasets", "image_target_cases.jsonl")

        self.normalizer = DiacriticsNormalizer()
        self.pipeline: Optional[Pipeline] = None
        self.label_to_query: Dict[str, str] = {}

        if os.path.exists(self.model_path):
            self._load()
        else:
            self._bootstrap_train_and_save()

    def _preprocess(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = self.normalizer.normalize(text)
        return text

    def _iter_dataset(self) -> Iterable[Tuple[str, str, str]]:
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                text = row.get("text", "")
                label = row.get("label", "")
                canonical_query = row.get("canonical_query", "")
                if not text or not label:
                    continue
                yield text, label, canonical_query

    def _bootstrap_train_and_save(self) -> None:
        try:
            texts: List[str] = []
            labels: List[str] = []
            label_to_query: Dict[str, str] = {}

            for text, label, canonical_query in self._iter_dataset():
                texts.append(self._preprocess(text))
                labels.append(label)
                if canonical_query and label not in label_to_query:
                    label_to_query[label] = canonical_query

            if len(set(labels)) < 2:
                raise ValueError("Need at least 2 classes to train image target classifier")

            self.pipeline = Pipeline(
                steps=[
                    (
                        "tfidf",
                        TfidfVectorizer(
                            ngram_range=(1, 2),
                            max_features=5000,
                            lowercase=True,
                            token_pattern=r"(?u)\\b\\w+\\b",
                        ),
                    ),
                    (
                        "clf",
                        LogisticRegression(
                            max_iter=2000,
                            class_weight="balanced",
                            n_jobs=None,
                            multi_class="auto",
                        ),
                    ),
                ]
            )

            logging.info(f"🤖 Training image target classifier with {len(texts)} examples...")
            self.pipeline.fit(texts, labels)
            self.label_to_query = label_to_query
            self._save()
            logging.info("✅ Image target classifier trained and saved")
        except Exception as e:
            logging.warning(f"⚠️ Failed to bootstrap-train image target classifier: {e}")
            self.pipeline = None
            self.label_to_query = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        payload = {
            "pipeline": self.pipeline,
            "label_to_query": self.label_to_query,
        }
        with open(self.model_path, "wb") as f:
            pickle.dump(payload, f)

    def _load(self) -> None:
        with open(self.model_path, "rb") as f:
            payload = pickle.load(f)
        self.pipeline = payload.get("pipeline")
        self.label_to_query = payload.get("label_to_query", {})

    def predict(self, text: str) -> TargetPrediction:
        if not self.pipeline:
            return TargetPrediction(label="unknown", confidence=0.0, canonical_query="")

        processed = self._preprocess(text)

        if not processed:
            return TargetPrediction(label="unknown", confidence=0.0, canonical_query="")

        # predict_proba is available for LogisticRegression
        probs = self.pipeline.predict_proba([processed])[0]
        classes = list(self.pipeline.classes_)
        best_idx = int(probs.argmax())
        label = str(classes[best_idx])
        confidence = float(probs[best_idx])

        canonical_query = self.label_to_query.get(label, "")
        return TargetPrediction(label=label, confidence=confidence, canonical_query=canonical_query)


# Singleton instance
image_target_classifier = ImageTargetClassifier()
