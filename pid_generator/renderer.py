"""Stage 4–8 — Canvas init, pipe rendering, and text tag rendering (§6.3, §12, §15, §16).

Public API
----------
init_canvas()                                    -> (Image, ImageDraw)
draw_title_block(draw, metadata)                 -> None
compute_snap_canvas_map(G, pos, ...)             -> dict[node, list[snap_entry]]
render_pipes(draw, G, pos, snap_canvas_map, ...) -> None
render_tags(draw, G, pos)                        -> None
render_diagram(G, pos, out_path, ...)            -> PIL.Image
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont

from pid_generator.constants import (
    BG_COLOR,
    CANVAS_H,
    CANVAS_W,
    CROSSING_COLOR,
    CROSSING_PALETTE,
    DASH_PATTERN,
    DPI_DEFAULT,
    DPI_MAX,
    DPI_MIN,
    FG_COLOR,
    FONT_SIZE,
    LINE_WIDTH,
    MARGIN,
    SMALL_FONT,
    SYMBOL_BOX,
)
from pid_generator.layout import compute_edge_waypoints, route_edge, snap_to_grid, to_pixel

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
    wp_x: int | None = None,
    dpi_scale: float = 1.0,
    fill: str = FG_COLOR,
) -> None:
    """Draw an edge with consistent line width regardless of DPI.

    DPI affects output quality/resolution but NOT line thickness.
    The *fill* colour overrides the default foreground colour; used by the
    ``"full_line_color"`` crossing style to give each crossing edge a unique colour.
    """
    # Line width is constant across all DPI values
    width = max(1, LINE_WIDTH.get(edge_type, 1))
    dash  = DASH_PATTERN.get(edge_type)
    segs  = route_edge(p1, p2, wp_x)
    for seg_p1, seg_p2 in segs:
        if dash:
            _draw_dashed_line(draw, seg_p1, seg_p2, dash=dash, width=width, fill=fill)
        else:
            draw.line([seg_p1, seg_p2], fill=fill, width=width)
    if edge_type == "signal_pneumatic":
        for seg_p1, seg_p2 in segs:
            _draw_pneumatic_ticks(draw, seg_p1, seg_p2)


def compute_snap_canvas_map(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    dpi_scale: float = 1.0,
    standard: str = "isa",
) -> dict[str, list[dict]]:
    """Compute canvas coordinates for each symbol's snap points (Stage 7 pre-pass).

    For every node that has a matching SVG symbol, the symbol's snap points are
    converted from normalised SVG coordinates to absolute canvas pixels using
    anchor-based positioning (so ``in_out`` points land where pipes connect).
    Nodes without a symbol fall back to a single centre-point entry.

    Returns:
        Mapping of ``node_id → list[snap_entry]`` where each entry is::

            {"x": int, "y": int, "type": str, "id": str}
    """
    from pid_generator.symbols_loader import get_registry

    registry = get_registry(standard=standard)
    symbol_size = int(SYMBOL_BOX * dpi_scale)
    result: dict[str, list[dict]] = {}

    for node, data in G.nodes(data=True):
        if node not in pos:
            continue

        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        class_id = data.get("class_id", 0)

        symbol = registry.get_symbol_for_class_id(class_id)
        if symbol:
            norm_snaps = registry.get_normalised_snap_points(symbol)
            in_out_norm = [(s["nx"], s["ny"]) for s in norm_snaps if s.get("type") == "in_out"]
        else:
            norm_snaps = []
            in_out_norm = []

        if not in_out_norm:
            # No in_out points — centre fallback
            result[node] = [{"x": cx, "y": cy, "type": "in_out", "id": "center"}]
            continue

        # Anchor = centroid of in_out snap points (normalised)
        ax = sum(p[0] for p in in_out_norm) / len(in_out_norm)
        ay = sum(p[1] for p in in_out_norm) / len(in_out_norm)

        # Top-left corner so the anchor lands at (cx, cy)
        tlx = cx - ax * symbol_size
        tly = cy - ay * symbol_size

        entries = []
        for sp in norm_snaps:
            entries.append({
                "x": int(tlx + sp["nx"] * symbol_size),
                "y": int(tly + sp["ny"] * symbol_size),
                "type": sp.get("type", "in_out"),
                "id":   sp.get("id", ""),
            })
        result[node] = entries

    return result


def _nearest_snap_in_direction(
    snap_entries: list[dict],
    from_cx: int,
    from_cy: int,
    to_cx: int,
    to_cy: int,
) -> tuple[int, int]:
    """Pick the ``in_out`` snap point most aligned with the direction from→to.

    Projects each candidate snap point onto the unit direction vector and
    returns the one with the highest dot product (i.e. furthest in the
    target direction).  Falls back to ``(from_cx, from_cy)`` when no
    ``in_out`` entries exist.
    """
    pts = [e for e in snap_entries if e.get("type") == "in_out"]
    if not pts:
        return (from_cx, from_cy)

    dx = to_cx - from_cx
    dy = to_cy - from_cy
    length = math.hypot(dx, dy)
    if length == 0:
        return (pts[0]["x"], pts[0]["y"])

    dx /= length
    dy /= length

    # Score = dot product of (snap - from_center) with direction vector
    best = max(pts, key=lambda e: (e["x"] - from_cx) * dx + (e["y"] - from_cy) * dy)
    return (best["x"], best["y"])


def render_pipes(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    waypoints: dict | None = None,
    dpi_scale: float = 1.0,
    snap_canvas_map: dict | None = None,
) -> None:
    """Draw all edges, process lines first then signal lines (§18, Stage 5).

    Args:
        draw: PIL ImageDraw object.
        G: The P&ID graph.
        pos: Node positions (normalised coordinates).
        waypoints: Computed edge waypoints (computed if None).
        dpi_scale: DPI scaling factor (affects line widths).
        snap_canvas_map: Pre-computed snap point canvas coordinates from
            :func:`compute_snap_canvas_map`.  When provided, pipe endpoints
            are placed at the symbol's nearest ``in_out`` snap point rather
            than the node centre.
    """
    if waypoints is None:
        waypoints = compute_edge_waypoints(G, pos)
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
            # Node centre positions (used as fallback and for direction)
            uc = snap_to_grid(*to_pixel(*pos[u]))
            vc = snap_to_grid(*to_pixel(*pos[v]))

            if snap_canvas_map is not None:
                p1 = _nearest_snap_in_direction(
                    snap_canvas_map.get(u, []), uc[0], uc[1], vc[0], vc[1])
                p2 = _nearest_snap_in_direction(
                    snap_canvas_map.get(v, []), vc[0], vc[1], uc[0], uc[1])
            else:
                p1, p2 = uc, vc

            wp_x = waypoints.get((u, v)) if etype == "process" else None
            _draw_edge(draw, p1, p2, etype, wp_x=wp_x, dpi_scale=dpi_scale)


# Stage 6 — Pipe crossing gaps

def draw_pipe_crossing_gaps(
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    hop_radius: int = 20,
    waypoints: dict | None = None,
    dpi_scale: float = 1.0,
    crossing_style: str = "hop",
    snap_canvas_map: dict | None = None,
) -> None:
    """Draw pipe crossings that are not junctions (§1.1).

    Two styles are available via *crossing_style*:

    ``"hop"`` (default)
        The horizontal segment remains continuous; the vertical segment gets a
        right-facing semicircular hop arc where it crosses the horizontal pipe.

    ``"color_change"``
        Both segments remain fully continuous. Only the small crossing zone of
        the *vertical* segment is redrawn in ``CROSSING_COLOR`` (red).

    ``"full_line_color"``
        Every edge that participates in at least one crossing is redrawn in
        its own unique colour from ``CROSSING_PALETTE``. Edges that cross each
        other always receive different colours, making all crossing lines
        individually traceable across the whole diagram.

    Args:
        hop_radius: Half-size of the crossing zone in pixels.
        dpi_scale: DPI scaling factor (affects line widths).
        crossing_style: ``"hop"``, ``"color_change"``, or ``"full_line_color"``.
    """
    if waypoints is None:
        waypoints = compute_edge_waypoints(G, pos)

    h_segs: list[tuple] = []
    v_segs: list[tuple] = []
    for u, v, edata in G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        etype = edata.get("type", "process")
        uc   = snap_to_grid(*to_pixel(*pos[u]))
        vc   = snap_to_grid(*to_pixel(*pos[v]))
        if snap_canvas_map is not None:
            p1 = _nearest_snap_in_direction(
                snap_canvas_map.get(u, []), uc[0], uc[1], vc[0], vc[1])
            p2 = _nearest_snap_in_direction(
                snap_canvas_map.get(v, []), vc[0], vc[1], uc[0], uc[1])
        else:
            p1, p2 = uc, vc
        wp_x = waypoints.get((u, v)) if etype == "process" else None
        for sp1, sp2 in route_edge(p1, p2, wp_x):
            dx = sp2[0] - sp1[0]
            dy = sp2[1] - sp1[1]
            key = (u, v)
            if dy == 0 and dx != 0:
                h_segs.append((sp1, sp2, key, etype))
            elif dx == 0 and dy != 0:
                v_segs.append((sp1, sp2, key, etype))

    r = hop_radius

    if crossing_style == "full_line_color":
        # Pass 1 — find every edge key that participates in at least one crossing.
        crossing_keys: set = set()
        for hp1, hp2, hkey, _ in h_segs:
            hx1 = min(hp1[0], hp2[0])
            hx2 = max(hp1[0], hp2[0])
            hy  = hp1[1]
            for vp1, vp2, vkey, _ in v_segs:
                if hkey == vkey:
                    continue
                vx  = vp1[0]
                vy1 = min(vp1[1], vp2[1])
                vy2 = max(vp1[1], vp2[1])
                if hx1 < vx < hx2 and vy1 < hy < vy2:
                    crossing_keys.add(hkey)
                    crossing_keys.add(vkey)

        # Assign a unique palette color to each crossing edge.
        edge_colors: dict = {
            key: CROSSING_PALETTE[i % len(CROSSING_PALETTE)]
            for i, key in enumerate(crossing_keys)
        }

        # Pass 2 — redraw each crossing edge entirely in its assigned color.
        for u, v, edata in G.edges(data=True):
            key = (u, v)
            if key not in edge_colors:
                continue
            if u not in pos or v not in pos:
                continue
            etype = edata.get("type", "process")
            uc   = snap_to_grid(*to_pixel(*pos[u]))
            vc   = snap_to_grid(*to_pixel(*pos[v]))
            if snap_canvas_map is not None:
                p1 = _nearest_snap_in_direction(
                    snap_canvas_map.get(u, []), uc[0], uc[1], vc[0], vc[1])
                p2 = _nearest_snap_in_direction(
                    snap_canvas_map.get(v, []), vc[0], vc[1], uc[0], uc[1])
            else:
                p1, p2 = uc, vc
            wp_x = waypoints.get((u, v)) if etype == "process" else None
            _draw_edge(draw, p1, p2, etype, wp_x=wp_x, dpi_scale=dpi_scale,
                       fill=edge_colors[key])

    else:
        for hp1, hp2, hkey, h_etype in h_segs:
            hx1 = min(hp1[0], hp2[0])
            hx2 = max(hp1[0], hp2[0])
            hy  = hp1[1]
            h_w = max(1, LINE_WIDTH.get(h_etype, 1))
            for vp1, vp2, vkey, v_etype in v_segs:
                if hkey == vkey:
                    continue
                vx  = vp1[0]
                vy1 = min(vp1[1], vp2[1])
                vy2 = max(vp1[1], vp2[1])
                v_w = max(1, LINE_WIDTH.get(v_etype, 1))
                if hx1 < vx < hx2 and vy1 < hy < vy2:
                    if crossing_style == "color_change":
                        # Redraw only the crossing zone of the vertical segment.
                        draw.line(
                            [(vx, hy - r), (vx, hy + r)],
                            fill=CROSSING_COLOR,
                            width=v_w,
                        )
                    else:
                        # "hop": erase zone, keep horizontal continuous, arc on vertical.
                        draw.rectangle([vx - r, hy - r, vx + r, hy + r], fill=BG_COLOR)
                        draw.line([(vx - r, hy), (vx + r, hy)], fill=FG_COLOR, width=h_w)
                        draw.arc(
                            [vx - r, hy - r, vx + r, hy + r],
                            start=270, end=90,
                            fill=FG_COLOR, width=v_w,
                        )


# Stage 7 — Symbol rendering

_NODE_COLORS: dict[str, str] = {
    "equipment":  "#D6EAF8",
    "valve":      "#D5F5E3",
    "instrument": "#FEF9E7",
    "fitting":    "#F5EEF8",
    "off_page":   "#FDFEFE",
}


def render_symbol_placeholders(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    dpi_scale: float = 1.0,
    standard: str = "isa",
    snap_canvas_map: dict | None = None,
    rng: Any = None,
) -> None:
    """Draw actual SVG symbols per node (Stage 7).

    Symbols are placed using anchor-based positioning: the centroid of the
    symbol's ``in_out`` snap points lands at the node's canvas centre,
    so pipe lines connect at the right physical point on the symbol body.
    Falls back to a placeholder box for nodes with no matching symbol.

    Args:
        img: The PIL Image to paste symbols onto.
        draw: The ImageDraw object.
        G: The P&ID graph.
        pos: Node positions (normalised coordinates).
        dpi_scale: DPI scaling factor (affects symbol size).
        standard: Symbol standard to use (e.g., ``"isa"``).
        snap_canvas_map: Pre-computed snap point positions from
            :func:`compute_snap_canvas_map`.  Used to determine the
            symbol's top-left placement corner directly.
        rng: ``random.Random`` instance for symbol variant selection.
    """
    from pid_generator.symbols_loader import get_registry
    from pid_generator.svg_renderer import render_svg_to_pil

    registry = get_registry(standard=standard)
    half = SYMBOL_BOX // 2
    font = _font(small=True)
    symbol_size = int(SYMBOL_BOX * dpi_scale)

    for node, data in G.nodes(data=True):
        if node not in pos:
            continue

        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        class_id = data.get("class_id", 0)

        symbol = registry.get_symbol_for_class_id(class_id, rng=rng)

        if symbol:
            svg_path = registry.get_svg_path(symbol)
            if svg_path:
                svg_img = render_svg_to_pil(svg_path, output_width=symbol_size, output_height=symbol_size)
                if svg_img:
                    # Anchor-based placement: offset top-left so the
                    # in_out centroid lands at (cx, cy).
                    ax, ay = registry.compute_anchor(symbol)
                    x = int(cx - ax * symbol_size)
                    y = int(cy - ay * symbol_size)
                    # Clamp to canvas bounds
                    x = max(0, min(x, img.width  - svg_img.width))
                    y = max(0, min(y, img.height - svg_img.height))
                    img.paste(svg_img, (x, y), svg_img)
                    continue

        # Fallback: placeholder box
        color = _NODE_COLORS.get(data.get("type", "fitting"), "#EEEEEE")
        draw.rectangle([cx - half + 4, cy - half + 4, cx + half - 4, cy + half - 4],
                       fill=BG_COLOR)
        draw.rectangle([cx - half, cy - half, cx + half, cy + half],
                       outline=FG_COLOR, fill=color, width=2)
        draw.text((cx - 8, cy - 10), str(class_id),
                  fill=FG_COLOR, font=font)


# Stage 8 — Text tag rendering


def _paste_rotated_tag(
    img: Image.Image,
    tag: str,
    cx: int,
    cy: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Render *tag* rotated 90° CCW and paste it centred at (cx, cy)."""
    char_w = SMALL_FONT - 2
    txt_w = max(8, len(tag) * char_w + 4)
    txt_h = SMALL_FONT + 6
    surf = Image.new("RGBA", (txt_w, txt_h), (255, 255, 255, 0))
    ImageDraw.Draw(surf).text((2, 2), tag, fill=(80, 80, 80), font=font)
    rotated = surf.rotate(90, expand=True)
    img.paste(rotated, (cx - rotated.width // 2, cy - rotated.height // 2), rotated)


def render_tags(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    waypoints: dict | None = None,
    dpi_scale: float = 1.0,
) -> None:
    """Draw node and edge text tags onto the canvas (§2, §8, Stage 8).

    Args:
        dpi_scale: DPI scaling factor (currently not used for text, reserved for future).
    """
    if waypoints is None:
        waypoints = compute_edge_waypoints(G, pos)

    font    = _font(small=False)
    font_sm = _font(small=True)
    half    = SYMBOL_BOX // 2
    halo    = "white"

    for node, data in G.nodes(data=True):
        if node not in pos:
            continue
        cx, cy = snap_to_grid(*to_pixel(*pos[node]))
        tag = data.get("tag", "")
        if tag:
            tx = cx - len(tag) * 5
            ty = cy - half - FONT_SIZE - 2
            # White halo background
            draw.rectangle([tx - 2, ty - 1, tx + len(tag) * 5 + 2, ty + FONT_SIZE + 1],
                           fill=halo)
            draw.text((tx, ty), tag, fill=FG_COLOR, font=font)

    for u, v, edata in G.edges(data=True):
        tag = edata.get("tag", "")
        if not tag or edata.get("type", "process") != "process":
            continue
        if u not in pos or v not in pos:
            continue
        wp_x = waypoints.get((u, v))
        segs = route_edge(snap_to_grid(*to_pixel(*pos[u])),
                          snap_to_grid(*to_pixel(*pos[v])),
                          wp_x)
        if not segs:
            continue
        # Place the label on the longest segment
        longest = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        sx1, sy1 = longest[0]
        sx2, sy2 = longest[1]
        mx, my = (sx1 + sx2) // 2, (sy1 + sy2) // 2
        is_vertical = (sx1 == sx2)
        if is_vertical:
            _paste_rotated_tag(img, tag, mx - SMALL_FONT - 4, my, font_sm)
        else:
            tx = mx - len(tag) * 4
            ty = my - SMALL_FONT - 2
            draw.rectangle([tx - 2, ty - 1, tx + len(tag) * 8 + 2, ty + SMALL_FONT + 1],
                           fill=halo)
            draw.text((tx, ty), tag, fill=(80, 80, 80), font=font_sm)


# Full pipeline

def render_diagram(
    G: nx.DiGraph,
    pos: dict[str, tuple[float, float]],
    out_path: str,
    metadata: dict | None = None,
    apply_noise: bool = False,
    idx: int = 1,
    seed: int | None = None,
    dpi: float | None = None,
    crossing_style: str | None = None,
    symbol_standard: str = "isa",
) -> Image.Image:
    """Run Stages 4–8 and save the diagram as a PNG (§18).

    If *metadata* is ``None``, ``generate_title_block_metadata(idx, seed)``
    is called automatically so every diagram gets a unique title block.

    Args:
        G: The P&ID graph.
        pos: Node positions (normalised coordinates).
        out_path: Output file path for PNG.
        metadata: ISO 7200 metadata dict (auto-generated if None).
        apply_noise: Whether to apply Stage 9 noise augmentation.
        idx: Diagram index for metadata generation.
        seed: RNG seed for reproducibility.
        dpi: Display DPI (72–300). If None, uses random value in range.
             Affects output quality/resolution. Line thickness remains constant.
        crossing_style: How pipe crossings are rendered. ``"hop"`` draws a
             semicircular arc on the vertical pipe. ``"color_change"``
             redraws the vertical pipe's crossing zone in ``CROSSING_COLOR``
             (red) so both lines stay continuous but are visually distinct.
             ``None`` (default) picks randomly between the two styles.
        symbol_standard: Symbol library to use (e.g. ``"isa"``).
    """
    if metadata is None:
        from pid_generator.title_block import generate_title_block_metadata
        metadata = generate_title_block_metadata(idx=idx, seed=seed)

    import random as _random
    rng = _random.Random(seed) if seed is not None else _random.Random()

    # Handle variable DPI: if not specified, choose random DPI in range
    if dpi is None:
        dpi = rng.uniform(DPI_MIN, DPI_MAX)

    # Handle crossing style: if not specified, pick randomly
    if crossing_style is None:
        crossing_style = rng.choice(["hop", "color_change", "full_line_color"])

    # Ensure DPI is within valid range
    dpi = max(DPI_MIN, min(dpi, DPI_MAX))

    # Calculate DPI scaling factor (relative to default 96 DPI)
    dpi_scale = dpi / DPI_DEFAULT

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    # Pre-compute snap point canvas positions (needed for pipe routing)
    snap_canvas_map = compute_snap_canvas_map(G, pos, dpi_scale=dpi_scale, standard=symbol_standard)

    img, draw = init_canvas()
    draw_title_block(draw, metadata)
    waypoints = compute_edge_waypoints(G, pos)
    render_pipes(draw, G, pos, waypoints, dpi_scale=dpi_scale,
                 snap_canvas_map=snap_canvas_map)
    draw_pipe_crossing_gaps(draw, G, pos, waypoints=waypoints, dpi_scale=dpi_scale,
                            crossing_style=crossing_style, snap_canvas_map=snap_canvas_map)
    render_symbol_placeholders(img, draw, G, pos, dpi_scale=dpi_scale,
                               standard=symbol_standard,
                               snap_canvas_map=snap_canvas_map, rng=rng)
    render_tags(img, draw, G, pos, waypoints, dpi_scale=dpi_scale)

    if apply_noise:
        from pid_generator.noise import apply_generation_noise
        img = apply_generation_noise(img)

    # Add DPI metadata to PNG
    img.info["dpi"] = (dpi, dpi)
    img.save(out_path, format="PNG", dpi=(dpi, dpi))
    return img
