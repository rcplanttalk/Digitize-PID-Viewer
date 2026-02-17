#!/usr/bin/env python3
"""Generate manifest.json mapping every image to its label file."""

import json
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
DATASET = os.path.join(BASE, "data", "DigitizePID_Dataset")
OUTPUT = os.path.join(BASE, "manifest.json")


def scan_split(split):
    """Return sorted list of {image, label, id} dicts for a split."""
    img_dir = os.path.join(DATASET, "images", split)
    lbl_dir = os.path.join(DATASET, "labels", split)
    entries = []
    if not os.path.isdir(img_dir):
        return entries
    for fname in sorted(os.listdir(img_dir)):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        stem = os.path.splitext(fname)[0]
        label_file = os.path.join(lbl_dir, stem + ".txt")
        entries.append(
            {
                "id": stem,
                "split": split,
                "image": f"data/DigitizePID_Dataset/images/{split}/{fname}",
                "label": f"data/DigitizePID_Dataset/labels/{split}/{stem}.txt" if os.path.isfile(label_file) else None,
            }
        )
    return entries


def main():
    train = scan_split("train")
    val = scan_split("val")
    generated = scan_split("generated")
    manifest = {
        "total": len(train) + len(val) + len(generated),
        "train_count": len(train),
        "val_count": len(val),
        "generated_count": len(generated),
        "items": train + val + generated,
    }
    with open(OUTPUT, "w") as f:
        json.dump(manifest, f, indent=2)
    parts = [f"{manifest['train_count']} train", f"{manifest['val_count']} val"]
    if manifest["generated_count"]:
        parts.append(f"{manifest['generated_count']} generated")
    print(f"Wrote {OUTPUT} with {manifest['total']} entries ({', '.join(parts)})")


if __name__ == "__main__":
    main()
