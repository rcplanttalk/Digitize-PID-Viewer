"""Stage 3 — Graph layout engine (§6.2, §16, §22).

Public API
----------
assign_grid_positions(G, x_right_fraction) -> dict[node, (float, float)]
compute_edge_waypoints(G, pos)             -> dict[(u,v), int | None]
snap_to_grid(px, py)                       -> (int, int)
to_pixel(norm_x, norm_y)                   -> (int, int)
route_orthogonal(p1, p2)                   -> list of (start, end) segment pairs
route_edge(p1, p2, wp_x)                   -> list of (start, end) segment pairs
"""

from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx

from pid_generator.constants import CANVAS_H, CANVAS_W, GRID, MARGIN

# Re-export so existing importers of layout.CANVAS_W etc. still work.
__all__ = [
    "CANVAS_H",
    "CANVAS_W",
    "GRID",
    "MARGIN",
    "assign_grid_positions",
    "compute_edge_waypoints",
    "route_edge",
    "route_orthogonal",
    "snap_to_grid",
    "to_pixel",
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
    return route_edge(p1, p2, wp_x=None)


def route_edge(
    p1: tuple[int, int],
    p2: tuple[int, int],
    wp_x: int | None = None,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Orthogonal routing with an optional explicit waypoint x (§22).

    - If ``wp_x`` is *None* or equal to ``x2``: standard L-shape via (x2, y1).
    - Otherwise: Z-shape ``p1 → (wp_x, y1) → (wp_x, y2) → p2``, which lets
      fan-out edges from the same source avoid overlapping horizontal segments.
    """
    x1, y1 = p1
    x2, y2 = p2

    if p1 == p2:
        return []
    if y1 == y2:
        return [(p1, p2)]
    if x1 == x2:
        return [(p1, p2)]

    if wp_x is None or wp_x == x2:
        wp = (x2, y1)
        return [(p1, wp), (wp, p2)]

    # Z-shape: horizontal to wp_x, vertical to y2, horizontal to x2
    segs: list[tuple] = []
    wp1 = (wp_x, y1)
    wp2 = (wp_x, y2)
    if p1 != wp1:
        segs.append((p1, wp1))
    if wp1 != wp2:
        segs.append((wp1, wp2))
    if wp2 != p2:
        segs.append((wp2, p2))
    return segs or [(p1, p2)]


def compute_edge_waypoints(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> dict[tuple[str, str], int | None]:
    """Return a waypoint x-pixel for every process edge to prevent fan-out overlaps.

    When multiple process edges leave the same source node heading to targets in
    the same x-column, ``route_edge`` with the default waypoint would send all of
    them through the same ``(x_target, y_source)`` point, producing identical
    overlapping horizontal segments.  This function assigns each such edge a
    distinct intermediate x-position (evenly spaced between source and target),
    yielding non-overlapping Z-shaped paths.

    All other edges (same row / column, or single fan-out) receive ``None``,
    which lets ``route_edge`` fall back to the standard L-shape.
    """
    waypoints: dict[tuple[str, str], int | None] = {}

    # Group L-shape process edges by (source_pixel, target_x_pixel)
    groups: dict[tuple, list] = defaultdict(list)

    for u, v, edata in G.edges(data=True):
        if edata.get("type", "process") != "process":
            waypoints[(u, v)] = None
            continue
        if u not in pos or v not in pos:
            waypoints[(u, v)] = None
            continue

        p1 = snap_to_grid(*to_pixel(*pos[u]))
        p2 = snap_to_grid(*to_pixel(*pos[v]))

        if p1[0] == p2[0] or p1[1] == p2[1]:
            waypoints[(u, v)] = None  # straight line, no waypoint needed
        else:
            groups[(p1, p2[0])].append((u, v, p1, p2))

    for (p1, tgt_x), edges in groups.items():
        n = len(edges)
        for i, (u, v, src_p, _) in enumerate(edges):
            if n == 1:
                waypoints[(u, v)] = tgt_x  # standard L-routing
            else:
                # Distribute waypoints evenly between source_x and target_x
                raw_x = src_p[0] + (tgt_x - src_p[0]) * (i + 1) / (n + 1)
                waypoints[(u, v)] = round(raw_x / GRID) * GRID

    return waypoints


def assign_grid_positions(
    G: nx.DiGraph,
    x_right_fraction: float = 0.0,
) -> dict[str, tuple[float, float]]:
    """Assign normalised grid positions to every node using topological order (§6.2).

    Algorithm:
    1. BFS topological generations on the process-only subgraph give each
       node an x-column corresponding to its depth from sources.
    2. Nodes in the same column are spread vertically.
    3. Signal-only nodes (instruments with no process edges) are offset
       above their nearest process neighbour.
    4. Positions are written back into each node's ``pos`` attribute.

    Args:
        G:                The P&ID graph.
        x_right_fraction: Fraction of usable canvas width to reserve on the
                          right side (e.g. 0.16 when the title block is on the
                          right).  Nodes are confined to
                          ``[x_margin, 1 - x_margin - x_right_fraction]``.

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
    x_span   = 1.0 - 2 * x_margin - x_right_fraction
    pos: dict[str, tuple[float, float]] = {}

    for col_idx, gen in enumerate(generations):
        nodes_in_col = sorted(gen)
        n = len(nodes_in_col)
        norm_x = x_margin + (col_idx / max(num_cols - 1, 1)) * x_span
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
