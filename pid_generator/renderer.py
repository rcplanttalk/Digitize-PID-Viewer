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
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from pid_generator.constants import (
    BG_COLOR,
    CANVAS_H,
    CANVAS_W,
    DASH_PATTERN,
    FG_COLOR,
    FONT_SIZE,
    LINE_WIDTH,
    MARGIN,
    SMALL_FONT,
    SYMBOL_BOX,
)
from pid_generator.layout import route_orthogonal, snap_to_grid, to_pixel

if TYPE_CHECKING:
    import networkx as nx


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


_FONT_NORMAL = None
_FONT_SMALL = None


def _font(small: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    global _FONT_NORMAL, _FONT_SMALL
    if small:
        if _FONT_SMALL is None:
            _FONT_SMALL = _load_font(SMALL_FONT)
        return _FONT_SMALL
    if _FONT_NORMAL is None:
        _FONT_NORMAL = _load_font(FONT_SIZE)
    return _FONT_NORMAL


# Stage 4 — Canvas initialisation

def init_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a blank white canvas at the standard P&ID size (§16)."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rectangle([MARGIN, MARGIN, CANVAS_W - MARGIN, CANVAS_H - MARGIN],
                   outline=FG_COLOR, width=2)
    return img, draw


# Stage 4 — Title block (delegated to title_block module)

def draw_title_block(
    draw: ImageDraw.ImageDraw,
    metadata: dict | None = None,
) -> None:
    """Draw the ISO 7200-compliant title block (§15).

    Delegates to :func:`pid_generator.title_block.draw_title_block`.
    """
    from pid_generator.title_block import draw_title_block as _dtb
    _dtb(draw, metadata)


# Stage 5 — Pipe / edge rendering

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
    pattern = list(dash)
    pat_len = len(pattern)
    pos_along, pat_idx, drawing = 0.0, 0, True
    while pos_along < length:
        seg = pattern[pat_idx % pat_len]
        end = min(pos_along + seg, length)
        if drawing:
            draw.line(
                [(x1 + dx * pos_along, y1 + dy * pos_along),
                 (x1 + dx * end,       y1 + dy * end)],
                fill=fill, width=width,
            )
        pos_along, pat_idx, drawing = end, pat_idx + 1, not drawing


def _draw_pneumatic_ticks(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    spacing: int = 24,
    tick_len: int = 6,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    px, py = -dy, dx
    pos_along = spacing / 2
    while pos_along < length:
        cx = x1 + dx * pos_along
        cy = y1 + dy * pos_along
        draw.line([(cx - px * tick_len, cy - py * tick_len),
                   (cx + px * tick_len, cy + py * tick_len)],
                  fill=FG_COLOR, width=1)
        pos_along += spacing


def _draw_edge(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    edge_type: str,
) -> None:
    width = LINE_WIDTH.get(edge_type, 1)
    dash  = DASH_PATTERN.get(edge_type)
    for seg_p1, seg_p2 in route_orthogonal(p1, p2):
        if dash:
            _draw_dashed_line(draw, seg_p1, seg_p2, dash=dash, width=width)
        else:
            draw.line([seg_p1, seg_p2], fill=FG_COLOR, width=width)
    if edge_type == "signal_pneumatic":
        for seg_p1, seg_p2 in route_orthogonal(p1, p2):
            _draw_pneumatic_ticks(draw, seg_p1, seg_p2)


def render_pipes(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw all edges, process lines first then signal lines (§18, Stage 5)."""
    order = ["process", "utility", "heat_trace", "drain_vent", "sample",
             "signal_electric", "signal_pneumatic", "signal_hydraulic"]
    by_type: dict[str, list] = {t: [] for t in order}
    by_type["other"] = []
    for u, v, edata in G.edges(data=True):
        etype = edata.get("type", "process")
        by_type.get(etype, by_type["other"]).append((u, v, edata))
    for etype in [*order, "other"]:
        for u, v, _ in by_type.get(etype, []):
            if u not in pos or v not in pos:
                continue
            p1 = snap_to_grid(*to_pixel(*pos[u]))
            p2 = snap_to_grid(*to_pixel(*pos[v]))
            _draw_edge(draw, p1, p2, etype)


# Stage 6 — Pipe crossing gaps

def draw_pipe_crossing_gaps(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    gap_radius: int = 8,
) -> None:
    """Draw white gap circles at pipe crossings that are not junctions (§1.1)."""
    h_segs: list[tuple] = []
    v_segs: list[tuple] = []
    for u, v, edata in G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        if edata.get("type", "process") not in ("process", "utility"):
            continue
        p1 = snap_to_grid(*to_pixel(*pos[u]))
        p2 = snap_to_grid(*to_pixel(*pos[v]))
        for sp1, sp2 in route_orthogonal(p1, p2):
            key = (u, v)
            if sp1[1] == sp2[1]:
                h_segs.append((sp1, sp2, key))
            elif sp1[0] == sp2[0]:
                v_segs.append((sp1, sp2, key))
    for hp1, hp2, hkey in h_segs:
        hx1, hy = min(hp1[0], hp2[0]), hp1[1]
        hx2 = max(hp1[0], hp2[0])
        for vp1, vp2, vkey in v_segs:
            if hkey == vkey:
                continue
            vx = vp1[0]
            vy1 = min(vp1[1], vp2[1])
            vy2 = max(vp1[1], vp2[1])
            if hx1 < vx < hx2 and vy1 < hy < vy2:
                draw.ellipse([vx - gap_radius, hy - gap_radius,
                              vx + gap_radius, hy + gap_radius],
                             fill=BG_COLOR)


# Stage 7 — Symbol placeholders

_NODE_COLORS: dict[str, str] = {
    "equipment":  "#D6EAF8",
    "valve":      "#D5F5E3",
    "instrument": "#FEF9E7",
    "fitting":    "#F5EEF8",
    "off_page":   "#FDFEFE",
}


def render_symbol_placeholders(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw labelled bounding-box placeholders per node (Stage 7 stub)."""
    half = SYMBOL_BOX // 2
    font = _font(small=True)
    for node, data in G.nodes(data=True):
        if node not in pos:
            continue
        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        color = _NODE_COLORS.get(data.get("type", "fitting"), "#EEEEEE")
        draw.rectangle([cx - half + 4, cy - half + 4, cx + half - 4, cy + half - 4],
                       fill=BG_COLOR)
        draw.rectangle([cx - half, cy - half, cx + half, cy + half],
                       outline=FG_COLOR, fill=color, width=2)
        draw.text((cx - 8, cy - 10), str(data.get("class_id", "?")),
                  fill=FG_COLOR, font=font)


# Stage 8 — Text tag rendering

def render_tags(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
) -> None:
    """Draw node and edge text tags onto the canvas (§2, §8, Stage 8)."""
    font    = _font(small=False)
    font_sm = _font(small=True)
    half    = SYMBOL_BOX // 2

    for node, data in G.nodes(data=True):
        if node not in pos:
            continue
        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        tag = data.get("tag", "")
        if tag:
            draw.text((cx - len(tag) * 5, cy - half - FONT_SIZE - 2),
                      tag, fill=FG_COLOR, font=font)

    for u, v, edata in G.edges(data=True):
        tag = edata.get("tag", "")
        if not tag or edata.get("type", "process") != "process":
            continue
        if u not in pos or v not in pos:
            continue
        segs = route_orthogonal(snap_to_grid(*to_pixel(*pos[u])),
                                snap_to_grid(*to_pixel(*pos[v])))
        if not segs:
            continue
        sx1, sy1 = segs[0][0]
        sx2, sy2 = segs[0][1]
        mx, my = (sx1 + sx2) // 2, (sy1 + sy2) // 2
        draw.text((mx - len(tag) * 4, my - SMALL_FONT - 2),
                  tag, fill=(80, 80, 80), font=font_sm)


# Full pipeline

def render_diagram(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    out_path: str,
    metadata: dict | None = None,
    apply_noise: bool = False,
    idx: int = 1,
    seed: int | None = None,
) -> Image.Image:
    """Run Stages 4–8 and save the diagram as a PNG (§18).

    If *metadata* is ``None``, ``generate_title_block_metadata(idx, seed)``
    is called automatically so every diagram gets a unique title block.
    """
    if metadata is None:
        from pid_generator.title_block import generate_title_block_metadata
        metadata = generate_title_block_metadata(idx=idx, seed=seed)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    img, draw = init_canvas()
    draw_title_block(draw, metadata)
    render_pipes(draw, G, pos)
    draw_pipe_crossing_gaps(draw, G, pos)
    render_symbol_placeholders(draw, G, pos)
    render_tags(draw, G, pos)

    if apply_noise:
        from pid_generator.noise import apply_generation_noise
        img = apply_generation_noise(img)

    img.save(out_path, format="PNG")
    return img
