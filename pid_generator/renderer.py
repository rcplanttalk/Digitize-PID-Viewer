"""Stage 4–8 — Canvas init, pipe rendering, and text tag rendering (§6.3, §12, §15, §16).

Public API
----------
init_canvas()                         -> (Image, ImageDraw)
draw_title_block(draw, metadata)      -> None
render_pipes(draw, G, pos)            -> None
render_tags(draw, G, pos)             -> None
render_diagram(G, pos, out_path, ...) -> PIL.Image
"""

from __future__ import annotations

import math
import os
import random

import networkx as nx
from PIL import Image, ImageDraw, ImageFont

from .layout import (
    CANVAS_H,
    CANVAS_W,
    GRID,
    MARGIN,
    route_orthogonal,
    snap_to_grid,
    to_pixel,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BG_COLOR    = "white"
FG_COLOR    = "black"
FONT_SIZE   = 22   # px for component tags
SMALL_FONT  = 16   # px for pipe tags and notes

# Line widths per edge type (§12)
_LINE_WIDTH: dict[str, int] = {
    "process":          3,
    "utility":          1,
    "signal_electric":  1,
    "signal_pneumatic": 1,
    "signal_hydraulic": 1,
    "heat_trace":       1,
    "sample":           1,
    "drain_vent":       1,
}

# Dash patterns (on, off) per edge type — None means solid (§12)
_DASH_PATTERN: dict[str, tuple | None] = {
    "process":          None,
    "utility":          None,
    "signal_electric":  (8, 4),
    "signal_pneumatic": (8, 4),
    "signal_hydraulic": (8, 4, 2, 4),
    "heat_trace":       None,
    "sample":           (16, 6),
    "drain_vent":       None,
}

# Placeholder symbol box size (§16)
SYMBOL_BOX = 64   # px half-side for placeholder rectangles

# ---------------------------------------------------------------------------
# Font loading (graceful fallback to default)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        # Try a few common monospace fonts available on most systems
        for name in ("cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    except Exception:
        pass
    return ImageFont.load_default()


_FONT_NORMAL = None
_FONT_SMALL  = None


def _font(small: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    global _FONT_NORMAL, _FONT_SMALL
    if small:
        if _FONT_SMALL is None:
            _FONT_SMALL = _load_font(SMALL_FONT)
        return _FONT_SMALL
    if _FONT_NORMAL is None:
        _FONT_NORMAL = _load_font(FONT_SIZE)
    return _FONT_NORMAL


# ---------------------------------------------------------------------------
# Stage 4 — Canvas initialisation
# ---------------------------------------------------------------------------

def init_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a blank white canvas at the standard P&ID size (§16).

    Returns:
        ``(img, draw)`` — a PIL Image and its associated ImageDraw context.
    """
    img  = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    # Outer border
    draw.rectangle(
        [MARGIN, MARGIN, CANVAS_W - MARGIN, CANVAS_H - MARGIN],
        outline=FG_COLOR, width=2,
    )
    return img, draw


# ---------------------------------------------------------------------------
# Stage 4 — Title block
# ---------------------------------------------------------------------------

def draw_title_block(
    draw: ImageDraw.ImageDraw,
    metadata: dict | None = None,
) -> None:
    """Draw the title block at the bottom of the canvas (§15).

    Args:
        draw:     ImageDraw context on the canvas.
        metadata: Optional dict with keys ``project``, ``title``, ``sheet``,
                  ``rev``, ``org``, ``disclaimer``.
    """
    if metadata is None:
        metadata = {}

    block_h = 100
    x0 = MARGIN
    y0 = CANVAS_H - MARGIN - block_h
    x1 = CANVAS_W - MARGIN
    y1 = CANVAS_H - MARGIN

    # Title block rectangle
    draw.rectangle([x0, y0, x1, y1], outline=FG_COLOR, width=1)

    # Vertical divider
    div_x = x1 - 300
    draw.line([(div_x, y0), (div_x, y1)], fill=FG_COLOR, width=1)

    font      = _font(small=False)
    font_sm   = _font(small=True)

    # Left side — org + title
    org   = metadata.get("org",   "AUTOMATION LABS")
    title = metadata.get("title", "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM")
    draw.text((x0 + 8, y0 + 8),  org,   fill=FG_COLOR, font=font)
    draw.text((x0 + 8, y0 + 36), title, fill=FG_COLOR, font=font_sm)

    # Right side — sheet + rev
    sheet = metadata.get("sheet", "P&ID-01")
    rev   = metadata.get("rev",   "A")
    draw.text((div_x + 8, y0 + 8),  f"Sheet: {sheet}", fill=FG_COLOR, font=font)
    draw.text((div_x + 8, y0 + 36), f"Rev:   {rev}",   fill=FG_COLOR, font=font)

    # Disclaimer below title block
    disclaimer = metadata.get(
        "disclaimer",
        "THIS DOCUMENT IS SYNTHETICALLY GENERATED FOR RESEARCH PURPOSES ONLY. "
        "NOT A REAL ENGINEERING DRAWING.",
    )
    draw.text(
        (x0 + 8, y1 + 4),
        disclaimer,
        fill=(120, 120, 120),
        font=font_sm,
    )


# ---------------------------------------------------------------------------
# Stage 5 — Pipe / edge rendering
# ---------------------------------------------------------------------------

def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    dash: tuple,
    width: int = 1,
    fill: str = FG_COLOR,
) -> None:
    """Draw a dashed line between two points (§12)."""
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    # Cycle through dash pattern (supports 2-element and 4-element tuples)
    pattern = list(dash)
    pat_len = len(pattern)
    pos_along = 0.0
    pat_idx   = 0
    drawing   = True
    while pos_along < length:
        seg = pattern[pat_idx % pat_len]
        end = min(pos_along + seg, length)
        if drawing:
            draw.line(
                [
                    (x1 + dx * pos_along, y1 + dy * pos_along),
                    (x1 + dx * end,       y1 + dy * end),
                ],
                fill=fill, width=width,
            )
        pos_along = end
        pat_idx  += 1
        drawing   = not drawing


def _draw_edge(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    edge_type: str,
) -> None:
    """Draw a single edge in the correct style for its type."""
    width   = _LINE_WIDTH.get(edge_type, 1)
    dash    = _DASH_PATTERN.get(edge_type, None)
    segments = route_orthogonal(p1, p2)

    for seg_p1, seg_p2 in segments:
        if dash:
            _draw_dashed_line(draw, seg_p1, seg_p2, dash=dash, width=width)
        else:
            draw.line([seg_p1, seg_p2], fill=FG_COLOR, width=width)

    # Pneumatic signal: add small perpendicular tick marks along the line (§12)
    if edge_type == "signal_pneumatic":
        for seg_p1, seg_p2 in segments:
            _draw_pneumatic_ticks(draw, seg_p1, seg_p2)


def _draw_pneumatic_ticks(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    spacing: int = 24,
    tick_len: int = 6,
) -> None:
    """Draw small perpendicular tick marks to indicate a pneumatic signal line."""
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    px, py = -dy, dx   # perpendicular unit vector
    pos_along = spacing / 2
    while pos_along < length:
        cx = x1 + dx * pos_along
        cy = y1 + dy * pos_along
        draw.line(
            [(cx - px * tick_len, cy - py * tick_len),
             (cx + px * tick_len, cy + py * tick_len)],
            fill=FG_COLOR, width=1,
        )
        pos_along += spacing


def render_pipes(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw all edges, process lines first then signal lines (§18, Stage 5).

    Args:
        draw: ImageDraw context.
        G:    Directed graph with edge ``type`` attributes.
        pos:  Node position dict ``{node: (norm_x, norm_y)}``.
    """
    # Draw order: process → utility → signal types (so signals render on top)
    order = ["process", "utility", "heat_trace", "drain_vent", "sample",
             "signal_electric", "signal_pneumatic", "signal_hydraulic"]

    edges_by_type: dict[str, list] = {t: [] for t in order}
    edges_by_type["other"] = []

    for u, v, edata in G.edges(data=True):
        etype = edata.get("type", "process")
        edges_by_type.get(etype, edges_by_type["other"]).append((u, v, edata))

    for etype in order + ["other"]:
        for u, v, _ in edges_by_type.get(etype, []):
            if u not in pos or v not in pos:
                continue
            p1 = snap_to_grid(*to_pixel(*pos[u]))
            p2 = snap_to_grid(*to_pixel(*pos[v]))
            _draw_edge(draw, p1, p2, etype)


# ---------------------------------------------------------------------------
# Stage 6 — Pipe crossing gaps
# ---------------------------------------------------------------------------

def draw_pipe_crossing_gaps(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    gap_radius: int = 8,
) -> None:
    """Draw white circles at pipe crossings that are not junctions (§1.1, Stage 6).

    Detects H/V segment intersections between distinct non-connected edges
    and draws a small white gap on the vertical line to indicate a crossing.

    Args:
        draw:       ImageDraw context.
        G:          Directed graph.
        pos:        Node position dict.
        gap_radius: Half-size of the gap circle in pixels.
    """
    # Collect all orthogonal segments and classify as H or V
    h_segs: list[tuple[tuple, tuple, tuple]] = []   # (p1, p2, edge_key)
    v_segs: list[tuple[tuple, tuple, tuple]] = []

    for u, v, edata in G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        if edata.get("type", "process") not in ("process", "utility"):
            continue
        p1 = snap_to_grid(*to_pixel(*pos[u]))
        p2 = snap_to_grid(*to_pixel(*pos[v]))
        for seg_p1, seg_p2 in route_orthogonal(p1, p2):
            sx1, sy1 = seg_p1
            sx2, sy2 = seg_p2
            key = (u, v)
            if sy1 == sy2:
                h_segs.append((seg_p1, seg_p2, key))
            elif sx1 == sx2:
                v_segs.append((seg_p1, seg_p2, key))

    # Find intersections between H and V segments from different edges
    for (hp1, hp2, hkey) in h_segs:
        hx1, hy = min(hp1[0], hp2[0]), hp1[1]
        hx2     = max(hp1[0], hp2[0])
        for (vp1, vp2, vkey) in v_segs:
            if hkey == vkey:
                continue
            vx, vy1 = vp1[0], min(vp1[1], vp2[1])
            vy2     = max(vp1[1], vp2[1])
            if hx1 < vx < hx2 and vy1 < hy < vy2:
                # Draw white gap on the vertical pipe at the crossing
                draw.ellipse(
                    [vx - gap_radius, hy - gap_radius,
                     vx + gap_radius, hy + gap_radius],
                    fill=BG_COLOR,
                )


# ---------------------------------------------------------------------------
# Stage 7 — Symbol placeholders (no templates yet)
# ---------------------------------------------------------------------------

_NODE_COLORS: dict[str, str] = {
    "equipment":  "#D6EAF8",   # light blue
    "valve":      "#D5F5E3",   # light green
    "instrument": "#FEF9E7",   # light yellow
    "fitting":    "#F5EEF8",   # light purple
    "off_page":   "#FDFEFE",   # near-white
}


def render_symbol_placeholders(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw labelled bounding-box placeholders for each node (Stage 7 stub).

    When actual template PNGs are available this function will be replaced
    by ``place_template()``.  Until then each node is drawn as a filled
    rectangle with its ``class_id`` written inside, which is still useful
    for verifying layout and connectivity visually.

    Args:
        draw: ImageDraw context.
        G:    Directed graph.
        pos:  Node position dict.
    """
    half = SYMBOL_BOX // 2
    font = _font(small=True)

    for node, data in G.nodes(data=True):
        if node not in pos:
            continue
        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        ntype = data.get("type", "fitting")
        color = _NODE_COLORS.get(ntype, "#EEEEEE")

        # Apply line-break mask: clear pipe underneath (§1.3)
        draw.rectangle(
            [cx - half + 4, cy - half + 4, cx + half - 4, cy + half - 4],
            fill=BG_COLOR,
        )
        # Symbol box
        draw.rectangle(
            [cx - half, cy - half, cx + half, cy + half],
            outline=FG_COLOR, fill=color, width=2,
        )
        # class_id label
        cid_text = str(data.get("class_id", "?"))
        draw.text((cx - 8, cy - 10), cid_text, fill=FG_COLOR, font=font)


# ---------------------------------------------------------------------------
# Stage 8 — Text tag rendering
# ---------------------------------------------------------------------------

def render_tags(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw node and edge text tags onto the canvas (§2, §8, Stage 8).

    Node tags are placed above each symbol.  Edge (pipe) tags are placed
    at the midpoint of the first segment, offset upward.

    Args:
        draw: ImageDraw context.
        G:    Directed graph with ``tag`` attributes.
        pos:  Node position dict.
    """
    font    = _font(small=False)
    font_sm = _font(small=True)
    half    = SYMBOL_BOX // 2

    # Node tags
    for node, data in G.nodes(data=True):
        if node not in pos:
            continue
        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        tag = data.get("tag", "")
        if tag:
            draw.text(
                (cx - len(tag) * 5, cy - half - FONT_SIZE - 2),
                tag, fill=FG_COLOR, font=font,
            )

    # Edge (pipe) tags — only process edges carry a tag
    for u, v, edata in G.edges(data=True):
        tag = edata.get("tag", "")
        if not tag or edata.get("type", "process") != "process":
            continue
        if u not in pos or v not in pos:
            continue
        p1 = snap_to_grid(*to_pixel(*pos[u]))
        p2 = snap_to_grid(*to_pixel(*pos[v]))
        segs = route_orthogonal(p1, p2)
        if not segs:
            continue
        # Midpoint of first segment
        sx1, sy1 = segs[0][0]
        sx2, sy2 = segs[0][1]
        mx = (sx1 + sx2) // 2
        my = (sy1 + sy2) // 2
        draw.text((mx - len(tag) * 4, my - SMALL_FONT - 2),
                  tag, fill=(80, 80, 80), font=font_sm)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def render_diagram(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    out_path: str,
    metadata: dict | None = None,
    apply_noise: bool = False,
) -> Image.Image:
    """Run Stages 4–8 and save the diagram as a PNG (§18).

    Args:
        G:            Validated directed graph.
        pos:          Node positions from ``assign_grid_positions()``.
        out_path:     Output PNG path.
        metadata:     Title block fields (see ``draw_title_block``).
        apply_noise:  If True, apply generation-time augmentations (Stage 9).

    Returns:
        The rendered ``PIL.Image``.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    img, draw = init_canvas()

    draw_title_block(draw, metadata)
    render_pipes(draw, G, pos)
    draw_pipe_crossing_gaps(draw, G, pos)
    render_symbol_placeholders(draw, G, pos)
    render_tags(draw, G, pos)

    if apply_noise:
        from .noise import apply_generation_noise
        img = apply_generation_noise(img)

    img.save(out_path, format="PNG")
    return img
