#!/usr/bin/env python3
"""Download the Digitize-PID YOLO dataset from Hugging Face."""

import os
import sys

def main():
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installing huggingface_hub...")
        os.system(f"{sys.executable} -m pip install --user huggingface_hub")
        from huggingface_hub import snapshot_download

    repo_id = "hamzas/digitize-pid-yolo"
    dest = os.path.join(os.path.dirname(__file__), "..", "data")
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    print(f"Downloading {repo_id} to {dest} ...")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=dest,
        ignore_patterns=["*.md", ".gitattributes"],
    )

    # Verify structure
    dataset_dir = os.path.join(dest, "DigitizePID_Dataset")
    for split in ("train", "val"):
        img_dir = os.path.join(dataset_dir, "images", split)
        lbl_dir = os.path.join(dataset_dir, "labels", split)
        n_imgs = len([f for f in os.listdir(img_dir) if f.endswith(".jpg")]) if os.path.isdir(img_dir) else 0
        n_lbls = len([f for f in os.listdir(lbl_dir) if f.endswith(".txt")]) if os.path.isdir(lbl_dir) else 0
        print(f"  {split}: {n_imgs} images, {n_lbls} labels")

    print("Done.")


if __name__ == "__main__":
    main()
