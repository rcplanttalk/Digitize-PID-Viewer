"""Stage 10 — YOLO label export and dataset manifest utilities (§18, §25, §26).

Public API
----------
export_yolo_labels(G, pos, out_path)   -> None
write_data_yaml(dataset_root)          -> None
label_filename(idx)                    -> str
image_filename(idx)                    -> str
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pid_generator.layout import CANVAS_H, CANVAS_W, snap_to_grid, to_pixel
from pid_generator.renderer import SYMBOL_BOX

if TYPE_CHECKING:
    import networkx as nx

# Class name registry (§25 data.yaml)

CLASS_NAMES: dict[int, str] = {
    0: "ball_valve",
    1: "butterfly_valve",
    2: "check_valve",
    3: "control_valve",
    4: "gate_valve",
    5: "globe_valve",
    6: "needle_valve",
    7: "plug_valve",
    8: "relief_valve",
    9: "pressure_reducing_valve",
    10: "diaphragm_valve",
    11: "angle_valve",
    12: "pressure_transmitter",
    13: "pressure_indicator",
    14: "pressure_controller",
    15: "temperature_transmitter",
    16: "temperature_indicator",
    17: "flow_transmitter",
    18: "flow_indicator",
    19: "flow_controller",
    20: "level_transmitter",
    21: "level_indicator",
    22: "level_controller",
    23: "analyser_transmitter",
    24: "centrifugal_pump",
    25: "reciprocating_pump",
    26: "compressor",
    27: "heat_exchanger",
    28: "vertical_vessel",
    29: "horizontal_vessel",
    30: "storage_tank",
    31: "agitator",
    32: "reducer_concentric",
    33: "reducer_eccentric",
    34: "strainer",
    35: "spectacle_blind",
    36: "expansion_joint",
    37: "flame_arrestor",
    38: "off_page_connector",
    39: "instrument_bubble",
    40: "junction_tee",
    41: "pipe_crossing",
}

# Symbol bounding-box size in pixels (§16 — default 96×96; renderer uses SYMBOL_BOX*2)
_BBOX_PX: int = SYMBOL_BOX * 2  # 128 px


# File naming helpers (§26)


def image_filename(idx: int) -> str:
    """Return the canonical image filename for diagram index *idx*."""
    return f"pid_{idx:04d}.png"


def label_filename(idx: int) -> str:
    """Return the canonical YOLO label filename for diagram index *idx*."""
    return f"pid_{idx:04d}.txt"


# Stage 10 — YOLO label export


def export_yolo_labels(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    out_path: str,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
) -> None:
    """Write a YOLO-format label file for every node in *G* (§18, Stage 10).

    One line per node:  ``<class_id> <cx> <cy> <w> <h>``
    All values are normalised to [0, 1] relative to canvas size.
    Nodes without a ``class_id`` attribute are skipped.

    Args:
        G:        Directed graph with node attributes (class_id, pos).
        pos:      Node position dict ``{node: (norm_x, norm_y)}``.
        out_path: Destination ``.txt`` file path.
        canvas_w: Canvas width in pixels (default 4096).
        canvas_h: Canvas height in pixels (default 2896).
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    lines: list[str] = []

    nw = _BBOX_PX / canvas_w
    nh = _BBOX_PX / canvas_h

    for node, data in G.nodes(data=True):
        cid = data.get("class_id")
        if cid is None or node not in pos:
            continue
        px, py = snap_to_grid(*to_pixel(*pos[node]))
        cx_norm = px / canvas_w
        cy_norm = py / canvas_h
        lines.append(f"{cid} {cx_norm:.6f} {cy_norm:.6f} {nw:.6f} {nh:.6f}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


# data.yaml writer


def write_data_yaml(dataset_root: str) -> None:
    """Write a YOLOv8-compatible ``data.yaml`` to *dataset_root* (§25).

    Args:
        dataset_root: Path to the dataset directory (must already exist or
                      will be created).
    """
    os.makedirs(dataset_root, exist_ok=True)
    out = os.path.join(dataset_root, "data.yaml")

    lines = [
        f"path: {os.path.abspath(dataset_root)}",
        "train: images/train",
        "val:   images/val",
        "test:  images/test",
        "",
        f"nc: {len(CLASS_NAMES)}",
        "names:",
    ]
    for cid, name in sorted(CLASS_NAMES.items()):
        lines.append(f"  {cid}: {name}")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
