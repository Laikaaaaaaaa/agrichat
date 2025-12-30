"""Train the image target classifier from datasets/image_target_cases.jsonl.

Usage (Windows / PowerShell):
  python tools/train_image_target_classifier.py

It will create/update models/image_target_classifier.pkl
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter

from image_target_classifier import ImageTargetClassifier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate datasets/image_target_cases.generated.jsonl from templates before training",
    )
    parser.add_argument(
        "--dataset",
        default=None,
    )
    parser.add_argument(
        "--model",
        default=os.path.join(os.path.dirname(__file__), "..", "models", "image_target_classifier.pkl"),
    )
    args = parser.parse_args()

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if args.generate:
        from generate_image_target_dataset import main as generate_main

        generate_main()

    default_generated = os.path.join(repo, "datasets", "image_target_cases.generated.jsonl")
    default_small = os.path.join(repo, "datasets", "image_target_cases.jsonl")
    dataset_path = os.path.abspath(args.dataset or (default_generated if os.path.exists(default_generated) else default_small))
    model_path = os.path.abspath(args.model)

    # Quick stats
    labels = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            label = row.get("label")
            if label:
                labels.append(label)

    counts = Counter(labels)
    print(f"Dataset: {dataset_path}")
    print(f"Total examples: {len(labels)}")
    print(f"Classes: {len(counts)}")
    for k, v in counts.most_common():
        print(f"  - {k}: {v}")

    # Train + save
    clf = ImageTargetClassifier(model_path=model_path, dataset_path=dataset_path)
    # Ensure retrain
    clf._bootstrap_train_and_save()

    print(f"Saved model: {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
