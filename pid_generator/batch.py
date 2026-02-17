"""Batch dataset generation pipeline (§26).

Generates N P&ID diagrams, splits them into train/val/test subsets,
writes YOLO label files, graph JSON files, and a manifest CSV.

Public API
----------
generate_dataset(n, dataset_root, base_seed, apply_noise) -> str  (manifest path)
generate_one(args)                                         -> dict (one record)
set_global_seed(seed)                                      -> None
"""

from __future__ import annotations

import csv
import os
import random

import numpy as np

from pid_generator.constants import CANVAS_W, MARGIN, TITLE_BLOCK_W
from pid_generator.graph_builder import create_logical_system
from pid_generator.layout import assign_grid_positions
from pid_generator.random_topology import create_random_topology
from pid_generator.renderer import render_diagram
from pid_generator.serialiser import export_graph, graph_filename
from pid_generator.title_block import generate_title_block_metadata
from pid_generator.validator import validate_pid_logic
from pid_generator.yolo import export_yolo_labels, image_filename, label_filename, write_data_yaml

# Split ratios (§26)

SPLIT_RATIOS: dict[str, float] = {
    "train": 0.80,
    "val": 0.10,
    "test": 0.10,
}

MANIFEST_FIELDS = [
    "idx",
    "seed",
    "topology",
    "sheet_count",
    "node_count",
    "edge_count",
    "split",
    "image_path",
    "label_path",
    "graph_path",
]


# Seed control


def set_global_seed(seed: int) -> None:
    """Set both Python random and NumPy seeds for reproducibility (§26)."""
    random.seed(seed)
    np.random.seed(seed)


# Single-diagram worker


def generate_one(
    idx: int,
    seed: int,
    split: str,
    dataset_root: str,
    topology: str = "logical",
    apply_noise: bool = True,
    n_nodes: int | None = None,
) -> dict:
    """Generate, validate, render, and export one diagram.

    Args:
        idx:          1-based diagram index.
        seed:         Per-diagram RNG seed (base_seed + idx).
        split:        ``'train'``, ``'val'``, or ``'test'``.
        dataset_root: Root directory of the dataset.
        topology:     ``'logical'`` (domain-constrained) or ``'random'``.
        apply_noise:  Whether to apply Stage 9 noise augmentations.
        n_nodes:      Target node count; ``None`` picks randomly in [10, 50].

    Returns:
        A manifest row dict.
    """
    set_global_seed(seed)

    # Stage 1 — build
    G = create_random_topology() if topology == "random" else create_logical_system(seed=seed, n_nodes=n_nodes)

    # Stage 2 — validate (non-fatal; log but continue)
    errors = validate_pid_logic(G)
    if errors:
        # Print warnings but don't abort — random topology may trigger some
        for _e in errors:
            pass

    # Stage 2.5 — title block metadata (determines layout x_right_fraction)
    metadata = generate_title_block_metadata(idx=idx, seed=seed)
    x_right_fraction = (
        TITLE_BLOCK_W / (CANVAS_W - 2 * MARGIN)
        if metadata.get("position") == "right"
        else 0.0
    )

    # Stage 3 — layout
    pos = assign_grid_positions(G, x_right_fraction=x_right_fraction)

    # File paths
    img_fname = image_filename(idx)
    lbl_fname = label_filename(idx)
    grph_fname = graph_filename(idx)

    img_path = os.path.join(dataset_root, "images", split, img_fname)
    lbl_path = os.path.join(dataset_root, "labels", split, lbl_fname)
    grph_path = os.path.join(dataset_root, "graphs", split, grph_fname)

    # Stages 4–9 — render
    render_diagram(G, pos, img_path, metadata=metadata, apply_noise=apply_noise, idx=idx, seed=seed)

    # Stage 10 — YOLO labels
    export_yolo_labels(G, pos, lbl_path)

    # Graph JSON
    export_graph(G, grph_path)

    return {
        "idx": idx,
        "seed": seed,
        "topology": topology,
        "sheet_count": 1,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "split": split,
        "image_path": img_path,
        "label_path": lbl_path,
        "graph_path": grph_path,
    }


# Batch driver


def generate_dataset(
    n: int = 10,
    dataset_root: str = "output/dataset",
    base_seed: int = 42,
    topology: str = "logical",
    apply_noise: bool = True,
    n_nodes: int | None = None,
) -> str:
    """Generate *n* diagrams and organise them into a YOLO dataset (§26).

    Folder structure produced::

        dataset/
        ├── data.yaml
        ├── images/{train,val,test}/pid_XXXX.png
        ├── labels/{train,val,test}/pid_XXXX.txt
        ├── graphs/{train,val,test}/pid_XXXX_graph.json
        └── manifest.csv

    Args:
        n:            Total number of diagrams to generate.
        dataset_root: Output root directory.
        base_seed:    Base RNG seed; each diagram uses ``base_seed + idx``.
        topology:     ``'logical'`` or ``'random'``.
        apply_noise:  Apply Stage 9 noise to every image.
        n_nodes:      Target node count per diagram; ``None`` picks randomly in [10, 50].

    Returns:
        Absolute path to the manifest CSV.
    """
    # Determine split boundaries
    n_train = max(1, round(n * SPLIT_RATIOS["train"]))
    n_val = max(1, round(n * SPLIT_RATIOS["val"]))
    n_test = n - n_train - n_val
    if n_test < 1:
        n_test = 1
        n_train = n - n_val - n_test

    def _split_for(idx: int) -> str:
        if idx <= n_train:
            return "train"
        if idx <= n_train + n_val:
            return "val"
        return "test"

    # Create folder tree
    for subset in ("train", "val", "test"):
        for kind in ("images", "labels", "graphs"):
            os.makedirs(os.path.join(dataset_root, kind, subset), exist_ok=True)

    # data.yaml
    write_data_yaml(dataset_root)

    # Generate diagrams
    manifest_path = os.path.join(dataset_root, "manifest.csv")
    rows: list[dict] = []

    for idx in range(1, n + 1):
        split = _split_for(idx)
        seed = base_seed + idx
        row = generate_one(idx, seed, split, dataset_root, topology, apply_noise, n_nodes)
        rows.append(row)

    # Write manifest CSV
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return os.path.abspath(manifest_path)
