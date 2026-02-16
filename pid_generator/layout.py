"""Stage 3 — Graph layout engine (§6.2, §16, §22).

Assigns normalised (0–1) grid positions to every node in a directed graph
and resolves edges to orthogonal pixel-space segments ready for the renderer.

Public API
----------
assign_grid_positions(G)        -> dict[node, (float, float)]
snap_to_grid(px, py)            -> (int, int)
to_pixel(norm_x, norm_y)        -> (int, int)
route_orthogonal(p1, p2)        -> list of (start, end) segment pairs
"""

from __future__ import annotations

import networkx as nx

# ---------------------------------------------------------------------------
# Canvas constants (§16)
# ---------------------------------------------------------------------------

CANVAS_W: int = 4096
CANVAS_H: int = 2896
MARGIN:   int = 40
GRID:     int = 128   # px per grid cell


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def to_pixel(norm_x: float, norm_y: float) -> tuple[int, int]:
    """Convert normalised (0–1) coordinates to canvas pixel coordinates (§16).

    Args:
        norm_x: Horizontal position in [0, 1].
        norm_y: Vertical position in [0, 1].

    Returns:
        ``(px, py)`` integer pixel coordinates within the drawable area.
    """
    usable_w = CANVAS_W - 2 * MARGIN
    usable_h = CANVAS_H - 2 * MARGIN
    return (
        int(MARGIN + norm_x * usable_w),
        int(MARGIN + norm_y * usable_h),
    )


def snap_to_grid(px: int, py: int) -> tuple[int, int]:
    """Round pixel coordinates to the nearest grid cell (§16).

    Args:
        px: Raw pixel x.
        py: Raw pixel y.

    Returns:
        Snapped ``(px, py)`` coordinates aligned to ``GRID`` boundaries.
    """
    return (round(px / GRID) * GRID, round(py / GRID) * GRID)


# ---------------------------------------------------------------------------
# Orthogonal routing
# ---------------------------------------------------------------------------

def route_orthogonal(
    p1: tuple[int, int],
    p2: tuple[int, int],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Return a list of (start, end) segment pairs forming an orthogonal path (§22).

    Handles four cases:
    - A: same row  → single horizontal segment
    - B: same column → single vertical segment
    - C: L-shape → one H + one V segment via waypoint at ``(x2, y1)``
    - D: degenerate same-point → empty list

    Args:
        p1: Start point ``(x, y)`` in pixels.
        p2: End point ``(x, y)`` in pixels.

    Returns:
        List of ``((x1,y1), (x2,y2))`` segment tuples.
    """
    x1, y1 = p1
    x2, y2 = p2

    if p1 == p2:
        return []
    if y1 == y2:            # Case A — horizontal
        return [(p1, p2)]
    if x1 == x2:            # Case B — vertical
        return [(p1, p2)]

    # Case C — L-shape via waypoint at (x2, y1)
    wp = (x2, y1)
    return [(p1, wp), (wp, p2)]


# ---------------------------------------------------------------------------
# Automatic grid position assignment
# ---------------------------------------------------------------------------

def assign_grid_positions(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Assign normalised grid positions to every node using topological order (§6.2).

    The algorithm:
    1. Compute topological generations (BFS layers) so nodes in the same
       generation share the same x-column.
    2. Spread nodes vertically within each column to avoid overlap.
    3. Signal-line nodes (instruments connected only via signal edges) are
       offset vertically above the process node they serve.

    Positions are normalised to [0.05, 0.95] to keep nodes inside the canvas
    margin.  The result is also written back into each node's ``pos`` attribute
    so the graph carries its own layout.

    Args:
        G: A directed graph (may contain both process and signal edges).

    Returns:
        A ``{node_id: (norm_x, norm_y)}`` dictionary.
    """
    # Work on a process-only subgraph for topological layering so that
    # signal edges do not distort the left-to-right flow layout.
    process_edges = [
        (u, v) for u, v, d in G.edges(data=True)
        if d.get("type", "process") == "process"
    ]
    P = nx.DiGraph()
    P.add_nodes_from(G.nodes())
    P.add_edges_from(process_edges)

    # --- topological generation (column = depth from sources) ---
    try:
        generations: list[set] = list(nx.topological_generations(P))
    except nx.NetworkXUnfeasible:
        # Cycle in process graph — fall back to random layout
        return _fallback_positions(G)

    num_cols = len(generations)
    pos: dict[str, tuple[float, float]] = {}

    x_margin = 0.05
    y_margin = 0.10

    for col_idx, gen in enumerate(generations):
        nodes_in_col = sorted(gen)  # stable order
        n = len(nodes_in_col)

        # x: evenly spaced columns
        norm_x = x_margin + (col_idx / max(num_cols - 1, 1)) * (1 - 2 * x_margin)

        # y: evenly spaced rows within column
        for row_idx, node in enumerate(nodes_in_col):
            if n == 1:
                norm_y = 0.5
            else:
                norm_y = y_margin + (row_idx / (n - 1)) * (1 - 2 * y_margin)
            pos[node] = (round(norm_x, 4), round(norm_y, 4))

    # --- place signal-only nodes (instruments not on process graph) ---
    # These nodes have no process edges; place them adjacent to the node
    # they signal from/to.
    signal_offset_y = 0.12  # normalised vertical offset above process node
    placed_signal: dict[str, tuple[float, float]] = {}

    for node in G.nodes():
        if node in pos:
            continue
        # Find the closest process node via signal edges
        signal_nbrs = [
            v for _, v, d in G.out_edges(node, data=True)
            if d.get("type") in ("signal_electric", "signal_pneumatic")
            and v in pos
        ] + [
            u for u, _, d in G.in_edges(node, data=True)
            if d.get("type") in ("signal_electric", "signal_pneumatic")
            and u in pos
        ]
        if signal_nbrs:
            ref_x, ref_y = pos[signal_nbrs[0]]
            # Offset upward; shift x slightly to avoid exact overlap
            cand_x = round(ref_x + 0.04, 4)
            cand_y = round(ref_y - signal_offset_y, 4)
            cand_y = max(y_margin, min(1 - y_margin, cand_y))
            placed_signal[node] = (cand_x, cand_y)
        else:
            placed_signal[node] = (0.5, 0.05)  # top-centre fallback

    pos.update(placed_signal)

    # Resolve collisions: if two nodes share the same grid cell, nudge one
    _resolve_collisions(pos)

    # Write pos back into graph node attributes
    for node, (nx_, ny_) in pos.items():
        G.nodes[node]["pos"] = [nx_, ny_]

    return pos


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fallback_positions(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Simple circular fallback when topological sort fails (cyclic graph)."""
    nodes = list(G.nodes())
    n = len(nodes)
    import math
    pos = {}
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / max(n, 1)
        pos[node] = (
            round(0.5 + 0.4 * math.cos(angle), 4),
            round(0.5 + 0.4 * math.sin(angle), 4),
        )
    return pos


def _resolve_collisions(
    pos: dict[str, tuple[float, float]],
    min_gap: float = 0.06,
) -> None:
    """Nudge nodes that share the same grid cell to avoid exact overlap (W002).

    Modifies *pos* in place.  Uses a simple greedy pass: if two nodes are
    closer than *min_gap* in both x and y, shift the second one down by
    *min_gap*.
    """
    nodes = list(pos.keys())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            ax, ay = pos[a]
            bx, by = pos[b]
            if abs(ax - bx) < min_gap and abs(ay - by) < min_gap:
                pos[b] = (bx, min(0.95, by + min_gap))
