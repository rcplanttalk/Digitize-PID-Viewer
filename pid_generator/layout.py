"""Stage 3 — Graph layout engine (§6.2, §16, §22).

Public API
----------
assign_grid_positions(G)        -> dict[node, (float, float)]
snap_to_grid(px, py)            -> (int, int)
to_pixel(norm_x, norm_y)        -> (int, int)
route_orthogonal(p1, p2)        -> list of (start, end) segment pairs
"""

from __future__ import annotations

import math

import networkx as nx

from pid_generator.constants import CANVAS_H, CANVAS_W, GRID, MARGIN

# Re-export so existing importers of layout.CANVAS_W etc. still work.
__all__ = [
    "CANVAS_W", "CANVAS_H", "MARGIN", "GRID",
    "to_pixel", "snap_to_grid", "route_orthogonal", "assign_grid_positions",
]


def to_pixel(norm_x: float, norm_y: float) -> tuple[int, int]:
    """Convert normalised (0–1) coordinates to canvas pixel coordinates (§16)."""
    usable_w = CANVAS_W - 2 * MARGIN
    usable_h = CANVAS_H - 2 * MARGIN
    return (
        int(MARGIN + norm_x * usable_w),
        int(MARGIN + norm_y * usable_h),
    )


def snap_to_grid(px: int, py: int) -> tuple[int, int]:
    """Round pixel coordinates to the nearest grid cell (§16)."""
    return (round(px / GRID) * GRID, round(py / GRID) * GRID)


def route_orthogonal(
    p1: tuple[int, int],
    p2: tuple[int, int],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Return (start, end) segment pairs forming an orthogonal path (§22).

    Cases handled:
    - A: same row  → single horizontal segment
    - B: same column → single vertical segment
    - C: L-shape → one H + one V segment via waypoint at (x2, y1)
    - D: same point → empty list
    """
    x1, y1 = p1
    x2, y2 = p2

    if p1 == p2:
        return []
    if y1 == y2:
        return [(p1, p2)]
    if x1 == x2:
        return [(p1, p2)]

    wp = (x2, y1)
    return [(p1, wp), (wp, p2)]


def assign_grid_positions(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Assign normalised grid positions to every node using topological order (§6.2).

    Algorithm:
    1. BFS topological generations on the process-only subgraph give each
       node an x-column corresponding to its depth from sources.
    2. Nodes in the same column are spread vertically.
    3. Signal-only nodes (instruments with no process edges) are offset
       above their nearest process neighbour.
    4. Positions are written back into each node's ``pos`` attribute.

    Falls back to a circular layout for graphs with cycles.
    """
    process_edges = [
        (u, v) for u, v, d in G.edges(data=True)
        if d.get("type", "process") == "process"
    ]
    P = nx.DiGraph()
    P.add_nodes_from(G.nodes())
    P.add_edges_from(process_edges)

    try:
        generations: list[set] = list(nx.topological_generations(P))
    except nx.NetworkXUnfeasible:
        return _fallback_positions(G)

    num_cols = len(generations)
    x_margin = 0.05
    y_margin = 0.10
    pos: dict[str, tuple[float, float]] = {}

    for col_idx, gen in enumerate(generations):
        nodes_in_col = sorted(gen)
        n = len(nodes_in_col)
        norm_x = x_margin + (col_idx / max(num_cols - 1, 1)) * (1 - 2 * x_margin)
        for row_idx, node in enumerate(nodes_in_col):
            norm_y = 0.5 if n == 1 else y_margin + row_idx / (n - 1) * (1 - 2 * y_margin)
            pos[node] = (round(norm_x, 4), round(norm_y, 4))

    signal_offset_y = 0.12
    placed_signal: dict[str, tuple[float, float]] = {}

    for node in G.nodes():
        if node in pos:
            continue
        signal_nbrs = [
            v for _, v, d in G.out_edges(node, data=True)
            if d.get("type") in ("signal_electric", "signal_pneumatic") and v in pos
        ] + [
            u for u, _, d in G.in_edges(node, data=True)
            if d.get("type") in ("signal_electric", "signal_pneumatic") and u in pos
        ]
        if signal_nbrs:
            ref_x, ref_y = pos[signal_nbrs[0]]
            cand_x = round(ref_x + 0.04, 4)
            cand_y = round(max(y_margin, min(1 - y_margin, ref_y - signal_offset_y)), 4)
            placed_signal[node] = (cand_x, cand_y)
        else:
            placed_signal[node] = (0.5, 0.05)

    pos.update(placed_signal)
    _resolve_collisions(pos)

    for node, (nx_, ny_) in pos.items():
        G.nodes[node]["pos"] = [nx_, ny_]

    return pos


def _fallback_positions(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Circular fallback when topological sort fails (cyclic graph)."""
    nodes = list(G.nodes())
    n = len(nodes)
    return {
        node: (
            round(0.5 + 0.4 * math.cos(2 * math.pi * i / max(n, 1)), 4),
            round(0.5 + 0.4 * math.sin(2 * math.pi * i / max(n, 1)), 4),
        )
        for i, node in enumerate(nodes)
    }


def _resolve_collisions(
    pos: dict[str, tuple[float, float]],
    min_gap: float = 0.06,
) -> None:
    """Nudge nodes that share the same grid cell to prevent W002 overlaps."""
    nodes = list(pos.keys())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            ax, ay = pos[a]
            bx, by = pos[b]
            if abs(ax - bx) < min_gap and abs(ay - by) < min_gap:
                pos[b] = (bx, min(0.95, by + min_gap))
