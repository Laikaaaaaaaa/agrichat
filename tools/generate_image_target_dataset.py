"""Generate a larger Vietnamese dataset for image target classification.

This creates datasets/image_target_cases.generated.jsonl from a small template file.

Usage:
  python tools/generate_image_target_dataset.py

You can then train:
  python tools/train_image_target_classifier.py --dataset datasets/image_target_cases.generated.jsonl
"""

from __future__ import annotations

import itertools
import json
import os
import random
from typing import Dict, List


def load_templates(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    here = os.path.dirname(__file__)
    repo = os.path.abspath(os.path.join(here, ".."))

    template_path = os.path.join(repo, "datasets", "image_target_templates.json")
    out_path = os.path.join(repo, "datasets", "image_target_cases.generated.jsonl")

    tpl = load_templates(template_path)
    actions: List[str] = tpl["actions"]
    objects: List[str] = tpl["objects"]
    suffixes: List[str] = tpl["suffixes"]
    labels = tpl["labels"]
    negatives: List[str] = tpl["negatives"]

    rng = random.Random(42)

    rows = []

    # Positive examples
    for item in labels:
        label = item["label"]
        canonical_query = item["canonical_query"]
        synonyms: List[str] = item["synonyms"]

        # Core short forms
        for s in synonyms:
            rows.append({"text": f"ảnh {s}", "label": label, "canonical_query": canonical_query})
            rows.append({"text": f"hình {s}", "label": label, "canonical_query": canonical_query})

        # Composed requests
        combos = list(itertools.product(actions, objects, synonyms, suffixes))
        rng.shuffle(combos)
        for a, o, s, suf in combos[:120]:  # cap per label to keep file size reasonable
            text = f"{a} {o} {s} {suf}".replace("  ", " ").strip()
            rows.append({"text": text, "label": label, "canonical_query": canonical_query})

    # Negative examples
    for n in negatives:
        rows.append({"text": n, "label": "not_image", "canonical_query": ""})
        rows.append({"text": f"tìm hiểu {n}", "label": "not_image", "canonical_query": ""})
        rows.append({"text": f"giải thích {n}", "label": "not_image", "canonical_query": ""})

    # Deduplicate
    seen = set()
    deduped = []
    for r in rows:
        key = (r["text"].strip().lower(), r["label"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    with open(out_path, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote: {out_path}")
    print(f"Total rows: {len(deduped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
