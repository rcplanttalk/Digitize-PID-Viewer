#!/usr/bin/env python3
"""
Synthetic P&ID generator with YOLO annotations.

Subcommands:
  extract   — Crop symbol templates from the existing dataset
  generate  — Generate synthetic P&ID images from templates
  all       — Run both extract and generate
"""

import argparse
import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

# ── Paths ──────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATASET = BASE / "data" / "DigitizePID_Dataset"
TEMPLATES_DIR = BASE / "data" / "templates"
GEN_IMAGES = DATASET / "images" / "generated"
GEN_LABELS = DATASET / "labels" / "generated"

# ── Constants ──────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 7168, 4561
NUM_CLASSES = 32
MAX_TEMPLATES_PER_CLASS = 50
EXTRACT_IMAGES = 50
PADDING = 4

BG_COLOR_RANGE = (204, 240)  # min/max grayscale value per image
PIPE_WIDTH = 3

# Normalized areas
DRAW_AREA = (0.04, 0.04, 0.69, 0.86)  # x_min, y_min, x_max, y_max for pipes/symbols
NOTES_AREA = (0.790, 0.043, 0.950, 0.700)
TITLE_AREA = (0.726, 0.700, 0.950, 0.950)

# Right-panel layout
SEPARATOR_X = 0.790   # vertical line splitting notes left/right
TITLE_LEFT_X = 0.726  # left edge of title block (below notes)

PIPE_SIZES = [2, 4, 6, 8, 10, 12, 14, 16]

# Tag prefixes by class type
VALVE_PREFIXES = [
    "GV", "GLV", "BV", "BFV", "CK", "PV", "RV", "NV",
    "DV", "AV", "TWV", "CV", "SOL", "MOV", "PCV", "HV",
]
INSTRUMENT_PREFIXES = [
    "PI", "TI", "FI", "LI", "FIC", "TIC", "LIC", "PIC",
    "FT", "TT", "LT", "PT",
]
EQUIPMENT_PREFIXES = ["P", "C", "T", "E", "V"]

PIPE_SPEC_CODES = ["JD", "CK", "AB", "EF", "GH", "PN", "WR", "ST", "HX", "MN"]

# Engineering notes pool
NOTES_POOL = [
    "ALL PIPING SHALL BE IN ACCORDANCE WITH ASME B31.3.",
    "INSTRUMENTS SHALL CONFORM TO ISA-5.1 STANDARDS.",
    "ALL DIMENSIONS ARE IN MILLIMETERS UNLESS OTHERWISE NOTED.",
    "REFER TO DWG-{num} FOR EQUIPMENT DETAILS.",
    "VESSEL DESIGN PER ASME SEC VIII DIV 1.",
    "ALL VALVES TO BE FLANGED UNLESS NOTED OTHERWISE.",
    "LINE NUMBERS PER PROJECT SPECIFICATION SP-{num}.",
    "INSULATION TYPE AND THICKNESS PER SPEC INS-{num}.",
    "REFER TO P&ID-{num} FOR CONTINUATION.",
    "ALL WELDING PER AWS D1.1 AND PROJECT SPEC.",
    "CONTROL VALVES FAIL CLOSED UNLESS NOTED.",
    "RELIEF VALVES SET PER PROCESS DATA SHEETS.",
    "DRAIN AND VENT VALVES 3/4\" MIN SIZE.",
    "SPECTACLE BLINDS AT ALL BATTERY LIMIT CONNECTIONS.",
    "SAMPLE CONNECTIONS 1\" WITH BLOCK VALVE.",
    "TEST CONNECTIONS WITH BLOCK AND BLEED VALVES.",
    "TEMPORARY STRAINERS DURING COMMISSIONING.",
    "ALL FLANGED JOINTS TO USE SPIRAL WOUND GASKETS.",
    "PIPE SUPPORTS PER STRUCTURAL DRAWINGS.",
    "ELECTRICAL CLASSIFICATION AREA CLASS 1 DIV 2.",
    "FIREPROOFING PER PROJECT SPEC FP-{num}.",
    "CATHODIC PROTECTION PER SPEC CP-{num}.",
    "ALL PRESSURE GAUGES LOCAL MOUNT UNLESS NOTED.",
    "FLOW ELEMENTS PER ISA STANDARD SIZING.",
    "CHECK VALVES REQUIRED AT ALL PUMP DISCHARGES.",
    "ISOLATION VALVES AT ALL EQUIPMENT NOZZLES.",
    "ALL INSTRUMENTS ACCESSIBLE FROM GRADE OR PLATFORM.",
    "PIPING MATERIAL PER LINE CLASS SPECIFICATION.",
    "THERMOWELL INSERTION LENGTH PER PROCESS REQ.",
    "SAFETY SHOWERS PER OSHA 29 CFR 1910.151.",
]

REVISION_DESCRIPTIONS = [
    "ISSUED FOR CONSTRUCTION",
    "ISSUED FOR REVIEW",
    "ISSUED FOR APPROVAL",
    "ISSUE CONSTR. REV.",
    "REVISED PER COMMENTS",
    "PRELIMINARY ISSUE",
    "AS BUILT REVISION",
    "UPDATED PER CLIENT REV.",
    "FINAL ISSUE",
    "ISSUED FOR BID",
]

DISCLAIMER_TEXT = (
    "PLEASE NOTE THIS DISCLAIMER CAREFULLY. THIS DOCUMENT IS COMPLETELY "
    "SYNTHETICALLY GENERATED AND IS NOT A REAL ENGINEERING DRAWING. IT IS "
    "INTENDED FOR RESEARCH AND TRAINING PURPOSES ONLY. ANY RESEMBLANCE "
    "TO ACTUAL PROJECTS OR FACILITIES IS ENTIRELY COINCIDENTAL. DO NOT "
    "USE THIS DRAWING FOR CONSTRUCTION, PROCUREMENT, OR OPERATION."
)

ORGANIZATION_NAMES = [
    "AUTOMATION LABS",
    "SYNTH ENGINEERING",
    "PROCESS SYSTEMS INC",
    "DIGITAL PROCESS CO",
    "CONTROL DYNAMICS LTD",
]

CONTRACT_NAMES = [
    "PROJ. DEF P&ID",
    "SYNTH PROC. P&ID",
    "PROCESS FLOW DWG",
    "PLANT LAYOUT P&ID",
    "UTILITY SYS. P&ID",
]

DIAGRAM_TITLES = [
    "SYNTHETIC PROCESS FLOW DIAGRAM",
    "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME",
    "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM",
    "SYNTHETIC UTILITY FLOW DIAGRAM",
]

DIAGRAM_TITLE_PAIRS = [
    ("SYNTHETIC PROCESS FLOW DIAGRAM", "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME"),
    ("SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM", "SYNTHETIC UTILITY FLOW DIAGRAM"),
    ("SYNTHETIC PROCESS FLOW DIAGRAM", "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM"),
]


# ── Phase 1: Extract templates ─────────────────────────────────────
def extract_templates():
    """Crop bounding-box regions from training images as PNG templates."""
    img_dir = DATASET / "images" / "train"
    lbl_dir = DATASET / "labels" / "train"

    if not img_dir.is_dir():
        print(f"ERROR: Training images not found at {img_dir}")
        sys.exit(1)

    class_counts = {i: 0 for i in range(NUM_CLASSES)}
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    for cid in range(NUM_CLASSES):
        cdir = TEMPLATES_DIR / str(cid)
        cdir.mkdir(exist_ok=True)
        class_counts[cid] = len(list(cdir.glob("*.png")))

    image_files = sorted(img_dir.glob("*.jpg"))[:EXTRACT_IMAGES]
    total_extracted = 0

    for img_path in image_files:
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue

        img = Image.open(img_path)
        w, h = img.size

        with open(lbl_path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue

                cid = int(parts[0])
                if cid < 0 or cid >= NUM_CLASSES:
                    continue
                if class_counts[cid] >= MAX_TEMPLATES_PER_CLASS:
                    continue

                xc, yc, bw, bh = (float(v) for v in parts[1:])
                px_xc = xc * w
                px_yc = yc * h
                px_w = bw * w
                px_h = bh * h

                x1 = max(0, int(px_xc - px_w / 2) - PADDING)
                y1 = max(0, int(px_yc - px_h / 2) - PADDING)
                x2 = min(w, int(px_xc + px_w / 2) + PADDING)
                y2 = min(h, int(px_yc + px_h / 2) + PADDING)

                if x2 - x1 < 4 or y2 - y1 < 4:
                    continue

                crop = img.crop((x1, y1, x2, y2))
                out_path = TEMPLATES_DIR / str(cid) / f"{img_path.stem}_{class_counts[cid]:03d}.png"
                crop.save(out_path, "PNG")
                class_counts[cid] += 1
                total_extracted += 1

        img.close()

    print(f"Extracted {total_extracted} templates into {TEMPLATES_DIR}")
    for cid in range(NUM_CLASSES):
        count = class_counts[cid]
        if count > 0:
            print(f"  Class {cid:2d}: {count} templates")


# ── Phase 2: Generate synthetic images ─────────────────────────────
def load_templates():
    """Load all template images grouped by class ID."""
    templates = {}
    for cid in range(NUM_CLASSES):
        cdir = TEMPLATES_DIR / str(cid)
        if not cdir.is_dir():
            continue
        paths = list(cdir.glob("*.png"))
        if paths:
            templates[cid] = paths
    if not templates:
        print(f"ERROR: No templates found in {TEMPLATES_DIR}. Run 'extract' first.")
        sys.exit(1)
    return templates


def draw_dashed_rect(draw, x1, y1, x2, y2, dash=20, gap=12, width=2, fill="black"):
    """Draw a dashed rectangle."""
    for start, end in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)),
                        ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length == 0:
            continue
        ux, uy = dx / length, dy / length
        pos = 0
        while pos < length:
            seg_end = min(pos + dash, length)
            draw.line(
                [(start[0] + ux * pos, start[1] + uy * pos),
                 (start[0] + ux * seg_end, start[1] + uy * seg_end)],
                fill=fill, width=width
            )
            pos += dash + gap


def draw_dashed_line(draw, x1, y1, x2, y2, dash=16, gap=10, width=2, fill="gray"):
    """Draw a single dashed line segment."""
    dx = x2 - x1
    dy = y2 - y1
    length = (dx ** 2 + dy ** 2) ** 0.5
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0
    while pos < length:
        seg_end = min(pos + dash, length)
        draw.line(
            [(x1 + ux * pos, y1 + uy * pos),
             (x1 + ux * seg_end, y1 + uy * seg_end)],
            fill=fill, width=width
        )
        pos += dash + gap


# ── Pipe network generation ────────────────────────────────────────
def generate_pipe_network():
    """Generate a connected network of horizontal and vertical pipes.

    Returns:
        h_pipes: [(y, x_start, x_end, pipe_size_inches), ...]  (normalized)
        v_pipes: [(x, y_start, y_end, pipe_size_inches), ...]  (normalized)
        junctions: [(x, y), ...]  (normalized)
    """
    x_min, y_min, x_max, y_max = DRAW_AREA

    # 1. Choose 5-10 horizontal levels with minimum spacing
    n_h = random.randint(5, 10)
    h_levels = []
    for _ in range(n_h * 5):
        if len(h_levels) >= n_h:
            break
        y = random.uniform(y_min + 0.02, y_max - 0.02)
        if all(abs(y - hy) >= 0.06 for hy in h_levels):
            h_levels.append(y)
    h_levels.sort()

    # 2. Choose 6-12 vertical columns with minimum spacing
    n_v = random.randint(6, 12)
    v_cols = []
    for _ in range(n_v * 5):
        if len(v_cols) >= n_v:
            break
        x = random.uniform(x_min + 0.02, x_max - 0.02)
        if all(abs(x - vx) >= 0.04 for vx in v_cols):
            v_cols.append(x)
    v_cols.sort()

    # 3. Assign horizontal pipe extents
    h_pipes = []
    for y in h_levels:
        # Some are main headers (wide span), others are branches
        if random.random() < 0.4:
            # Main header: wide span
            xs = random.uniform(x_min, x_min + 0.05)
            xe = random.uniform(x_max - 0.08, x_max)
        else:
            # Branch: span 2-5 columns
            if len(v_cols) < 2:
                continue
            i_start = random.randint(0, max(0, len(v_cols) - 2))
            span = random.randint(2, min(5, len(v_cols) - i_start))
            xs = v_cols[i_start] - random.uniform(0.01, 0.03)
            xe = v_cols[min(i_start + span - 1, len(v_cols) - 1)] + random.uniform(0.01, 0.03)
            xs = max(x_min, xs)
            xe = min(x_max, xe)
        size = random.choice(PIPE_SIZES)
        h_pipes.append((y, xs, xe, size))

    # 4. Connect with vertical risers
    v_pipes = []
    junctions = []
    for x in v_cols:
        # Find horizontal pipes that this column crosses
        crossing_h = [(i, hp) for i, hp in enumerate(h_pipes) if hp[1] <= x <= hp[2]]
        if len(crossing_h) < 2:
            continue

        # Connect consecutive crossing pipes, skip ~30-40% randomly
        for k in range(len(crossing_h) - 1):
            if random.random() < 0.35:
                continue
            _, hp1 = crossing_h[k]
            _, hp2 = crossing_h[k + 1]
            y1 = hp1[0]
            y2 = hp2[0]
            size = random.choice(PIPE_SIZES)
            v_pipes.append((x, y1, y2, size))
            junctions.append((x, y1))
            junctions.append((x, y2))

    # Deduplicate junctions
    seen = set()
    unique_junctions = []
    for jx, jy in junctions:
        key = (round(jx, 4), round(jy, 4))
        if key not in seen:
            seen.add(key)
            unique_junctions.append((jx, jy))

    return h_pipes, v_pipes, unique_junctions


# ── Symbol placement on network ────────────────────────────────────
def place_symbols_on_network(h_pipes, v_pipes, junctions, templates):
    """Place symbols in logical positions on the pipe network.

    5 phases:
      1. Tee marks at junctions (class 20)
      2. Equipment at endpoints (classes 23-27)
      3. Valves ON pipe segments (classes 0-15)
      4. Instruments near pipes (classes 16-19, 21-22) with signal lines
      5. Basics at special positions (classes 28-31)

    Returns:
        placements: [(cx, cy, w, h, class_id, template_path), ...] (pixel coords)
        signal_connections: [(inst_x, inst_y, pipe_x, pipe_y), ...] (pixel coords)
    """
    placements = []
    signal_connections = []
    occupied = []  # (cx, cy, w, h) for collision avoidance

    def has_overlap(cx, cy, w, h, min_gap=20):
        for ox, oy, ow, oh in occupied:
            if (abs(cx - ox) < (w + ow) / 2 + min_gap and
                    abs(cy - oy) < (h + oh) / 2 + min_gap):
                return True
        return False

    def get_template_size(cid):
        if cid not in templates:
            return None, None, None
        tpath = random.choice(templates[cid])
        timg = Image.open(tpath)
        tw, th = timg.size
        timg.close()
        scale = random.uniform(0.9, 1.1)
        return tpath, max(8, int(tw * scale)), max(8, int(th * scale))

    def norm_to_px(nx, ny):
        return int(nx * CANVAS_W), int(ny * CANVAS_H)

    # ── Phase 1: Tee marks at junctions (class 20 - Instrument Generic) ──
    tee_class = 20
    random.shuffle(junctions)
    tee_count = 0
    tee_target = random.randint(min(30, len(junctions)), min(60, max(30, len(junctions))))
    for jx, jy in junctions:
        if tee_count >= tee_target:
            break
        if tee_class not in templates:
            break
        tpath, tw, th = get_template_size(tee_class)
        if tpath is None:
            break
        px, py = norm_to_px(jx, jy)
        if not has_overlap(px, py, tw, th):
            placements.append((px, py, tw, th, tee_class, tpath))
            occupied.append((px, py, tw, th))
            tee_count += 1

    # ── Phase 2: Equipment at pipe endpoints/junctions (classes 23-27) ──
    equip_classes = [c for c in range(23, 28) if c in templates]
    equip_target = random.randint(10, 20)
    equip_count = 0

    # Collect pipe endpoints
    endpoints = []
    for y, xs, xe, _ in h_pipes:
        endpoints.append((xs, y))
        endpoints.append((xe, y))
    for x, ys, ye, _ in v_pipes:
        endpoints.append((x, ys))
        endpoints.append((x, ye))
    random.shuffle(endpoints)

    for ex, ey in endpoints:
        if equip_count >= equip_target:
            break
        if not equip_classes:
            break
        cid = random.choice(equip_classes)
        tpath, tw, th = get_template_size(cid)
        if tpath is None:
            continue
        px, py = norm_to_px(ex, ey)
        if not has_overlap(px, py, tw, th):
            placements.append((px, py, tw, th, cid, tpath))
            occupied.append((px, py, tw, th))
            equip_count += 1

    # ── Phase 3: Valves ON pipe segments (classes 0-15) ──
    valve_classes = [c for c in range(0, 16) if c in templates]
    valve_target = random.randint(25, 50)
    valve_count = 0

    # Collect positions along horizontal pipes between junctions
    valve_candidates = []
    for y, xs, xe, _ in h_pipes:
        # Generate several candidate points along the pipe
        n_candidates = max(2, int((xe - xs) / 0.06))
        for _ in range(n_candidates):
            vx = random.uniform(xs + 0.02, xe - 0.02)
            valve_candidates.append((vx, y))
    # Also along vertical pipes
    for x, ys, ye, _ in v_pipes:
        n_candidates = max(1, int((ye - ys) / 0.08))
        for _ in range(n_candidates):
            vy = random.uniform(ys + 0.02, ye - 0.02)
            valve_candidates.append((x, vy))

    random.shuffle(valve_candidates)

    for vx, vy in valve_candidates:
        if valve_count >= valve_target:
            break
        if not valve_classes:
            break
        cid = random.choice(valve_classes)
        tpath, tw, th = get_template_size(cid)
        if tpath is None:
            continue
        px, py = norm_to_px(vx, vy)
        if not has_overlap(px, py, tw, th, min_gap=40):
            placements.append((px, py, tw, th, cid, tpath))
            occupied.append((px, py, tw, th))
            valve_count += 1

    # ── Phase 4: Instruments near pipes (classes 16-19, 21-22) ──
    inst_classes = [c for c in [16, 17, 18, 19, 21, 22] if c in templates]
    inst_target = random.randint(15, 30)
    inst_count = 0

    inst_candidates = []
    for y, xs, xe, _ in h_pipes:
        n_pts = max(2, int((xe - xs) / 0.08))
        for _ in range(n_pts):
            ix = random.uniform(xs + 0.02, xe - 0.02)
            # Offset perpendicular (above or below pipe)
            offset = random.choice([-1, 1]) * random.uniform(0.025, 0.045)
            iy = y + offset
            inst_candidates.append((ix, iy, ix, y))  # instrument pos + pipe attachment
    for x, ys, ye, _ in v_pipes:
        n_pts = max(1, int((ye - ys) / 0.10))
        for _ in range(n_pts):
            iy = random.uniform(ys + 0.02, ye - 0.02)
            offset = random.choice([-1, 1]) * random.uniform(0.025, 0.045)
            ix = x + offset
            inst_candidates.append((ix, iy, x, iy))

    random.shuffle(inst_candidates)

    for ix, iy, pipe_x, pipe_y in inst_candidates:
        if inst_count >= inst_target:
            break
        if not inst_classes:
            break
        cid = random.choice(inst_classes)
        tpath, tw, th = get_template_size(cid)
        if tpath is None:
            continue
        px, py = norm_to_px(ix, iy)
        ppx, ppy = norm_to_px(pipe_x, pipe_y)
        if not has_overlap(px, py, tw, th):
            placements.append((px, py, tw, th, cid, tpath))
            occupied.append((px, py, tw, th))
            signal_connections.append((px, py, ppx, ppy))
            inst_count += 1

    # ── Phase 5: Basics (classes 28-31) ──
    # 28=Reducer, 29=Flange, 30=End Connector, 31=Arrow
    basic_target = random.randint(15, 25)
    basic_count = 0

    basic_candidates = []
    # Reducers at random pipe positions (simulating size changes)
    for y, xs, xe, _ in h_pipes:
        mid_x = (xs + xe) / 2 + random.uniform(-0.05, 0.05)
        basic_candidates.append((mid_x, y, 28))
    # Flanges near equipment
    for p in placements:
        if p[4] in range(23, 28):
            fx = p[0] / CANVAS_W + random.choice([-1, 1]) * random.uniform(0.015, 0.025)
            fy = p[1] / CANVAS_H
            basic_candidates.append((fx, fy, 29))
    # End connectors at pipe endpoints
    for y, xs, xe, _ in h_pipes:
        if random.random() < 0.5:
            basic_candidates.append((xs, y, 30))
        if random.random() < 0.5:
            basic_candidates.append((xe, y, 30))
    # Arrows along pipes (flow direction)
    for y, xs, xe, _ in h_pipes:
        ax = random.uniform(xs + 0.05, xe - 0.05)
        basic_candidates.append((ax, y, 31))

    random.shuffle(basic_candidates)

    for bx, by, preferred_cid in basic_candidates:
        if basic_count >= basic_target:
            break
        cid = preferred_cid if preferred_cid in templates else None
        if cid is None:
            # Try any available basic class
            avail = [c for c in range(28, 32) if c in templates]
            if not avail:
                break
            cid = random.choice(avail)
        tpath, tw, th = get_template_size(cid)
        if tpath is None:
            continue
        px, py = norm_to_px(bx, by)
        if not has_overlap(px, py, tw, th):
            placements.append((px, py, tw, th, cid, tpath))
            occupied.append((px, py, tw, th))
            basic_count += 1

    return placements, signal_connections


# ── Drawing functions ──────────────────────────────────────────────
def draw_pipes(draw, h_pipes, v_pipes):
    """Draw solid black pipe lines on the canvas."""
    for y, xs, xe, _ in h_pipes:
        py = int(y * CANVAS_H)
        px_start = int(xs * CANVAS_W)
        px_end = int(xe * CANVAS_W)
        draw.line([(px_start, py), (px_end, py)], fill="black", width=PIPE_WIDTH)

    for x, ys, ye, _ in v_pipes:
        px = int(x * CANVAS_W)
        py_start = int(ys * CANVAS_H)
        py_end = int(ye * CANVAS_H)
        draw.line([(px, py_start), (px, py_end)], fill="black", width=PIPE_WIDTH)


def draw_signal_lines(draw, signal_connections):
    """Draw dashed signal lines from instruments to their pipe attachment points."""
    for ix, iy, px, py in signal_connections:
        draw_dashed_line(draw, ix, iy, px, py, dash=10, gap=8, width=1, fill=(120, 120, 120))


def generate_tag(class_id):
    """Generate a realistic ISA-style tag for a given class."""
    if 0 <= class_id <= 15:
        # Valve
        prefix = VALVE_PREFIXES[class_id]
        num = random.randint(100, 29999)
        return f"{prefix}-{num}"
    elif 16 <= class_id <= 22:
        # Instrument
        prefix = random.choice(INSTRUMENT_PREFIXES)
        num = random.randint(1000, 9999)
        return f"{prefix}-{num}"
    elif 23 <= class_id <= 27:
        # Equipment
        prefix = EQUIPMENT_PREFIXES[class_id - 23]
        num = random.randint(100, 999)
        suffix = random.choice(["", "A", "B", ""])
        return f"{prefix}-{num}{suffix}"
    else:
        # Basics (28-31) generally don't get prominent tags, but give a short ID
        return ""


def generate_line_number(pipe_size):
    """Generate a realistic pipe line number like 4\"-JD-9505."""
    code = random.choice(PIPE_SPEC_CODES)
    num = random.randint(1000, 9999)
    return f'{pipe_size}"-{code}-{num}'


def draw_text_labels(draw, placements, font, font_sm):
    """Draw ISA-style text tags for each symbol."""
    for cx, cy, sw, sh, cid, _ in placements:
        tag = generate_tag(cid)
        if not tag:
            continue
        # Position: above or to the right of the symbol
        if random.random() < 0.6:
            # Above
            lx = cx - len(tag) * 4
            ly = cy - sh // 2 - 18
        else:
            # Right
            lx = cx + sw // 2 + 5
            ly = cy - 7
        draw.text((lx, ly), tag, fill="black", font=font_sm)


def draw_pipe_size_labels(draw, h_pipes, v_pipes, font_sm):
    """Draw pipe size labels at midpoints of pipe segments."""
    for y, xs, xe, size in h_pipes:
        mid_x = int(((xs + xe) / 2) * CANVAS_W)
        py = int(y * CANVAS_H) - 16
        label = f'{size}"'
        draw.text((mid_x, py), label, fill="black", font=font_sm)

    for x, ys, ye, size in v_pipes:
        mid_y = int(((ys + ye) / 2) * CANVAS_H)
        px = int(x * CANVAS_W) + 6
        label = f'{size}"'
        draw.text((px, mid_y), label, fill="black", font=font_sm)


# ── Separator line ─────────────────────────────────────────────────
def draw_separator_line(draw):
    """Draw continuous vertical separator at SEPARATOR_X from notes top to title bottom."""
    sx = int(CANVAS_W * SEPARATOR_X)
    sy1 = int(CANVAS_H * NOTES_AREA[1])   # top of notes area
    sy2 = int(CANVAS_H * TITLE_AREA[3])   # bottom of title area
    draw.line([(sx, sy1), (sx, sy2)], fill="black", width=2)


# ── Title block sub-functions ─────────────────────────────────────
def draw_revision_table(draw, tx1, ty1, tx2, ty2, font_sm):
    """Draw revision table: header row + 4-5 data rows (ISSUE/DATE/MADE/CHECKED/APPRVD/DESCRIPTION)."""
    # Outer border
    draw.rectangle([tx1, ty1, tx2, ty2], outline="black", width=2)

    n_rows = random.randint(4, 5)
    row_h = (ty2 - ty1) / (n_rows + 1)  # +1 for header

    # Column positions (6 cols): ISSUE | DATE | MADE | CHECKED | APPRVD | DESCRIPTION
    col_fracs = [0.0, 0.10, 0.25, 0.37, 0.52, 0.67, 1.0]
    col_xs = [tx1 + int((tx2 - tx1) * f) for f in col_fracs]

    # Header row
    headers = ["ISSUE", "DATE", "MADE", "CHECKED", "APPRVD", "DESCRIPTION"]
    hy = ty1
    for ci in range(6):
        draw.text((col_xs[ci] + 4, hy + 3), headers[ci], fill="black", font=font_sm)
        if ci > 0:
            draw.line([(col_xs[ci], ty1), (col_xs[ci], ty2)], fill="black", width=1)

    # Header divider
    hdy = ty1 + int(row_h)
    draw.line([(tx1, hdy), (tx2, hdy)], fill="black", width=1)

    # Data rows
    rev_letters = ["A", "B", "C", "D", "E"]
    descs = random.sample(REVISION_DESCRIPTIONS, min(n_rows, len(REVISION_DESCRIPTIONS)))
    initials_pool = ["JD", "MK", "RS", "AL", "TP", "BN", "CW", "DH"]

    for ri in range(n_rows):
        ry = ty1 + int(row_h * (ri + 1))
        if ri > 0:
            draw.line([(tx1, ry), (tx2, ry)], fill="black", width=1)
        # ISSUE letter
        draw.text((col_xs[0] + 8, ry + 3), rev_letters[ri], fill="black", font=font_sm)
        # DATE
        month = random.randint(1, 12)
        year = random.randint(20, 25)
        draw.text((col_xs[1] + 4, ry + 3), f"{month:02d}/{year}", fill="black", font=font_sm)
        # MADE
        draw.text((col_xs[2] + 4, ry + 3), random.choice(initials_pool), fill="black", font=font_sm)
        # CHECKED
        draw.text((col_xs[3] + 4, ry + 3), random.choice(initials_pool), fill="black", font=font_sm)
        # APPRVD
        draw.text((col_xs[4] + 4, ry + 3), random.choice(initials_pool), fill="black", font=font_sm)
        # DESCRIPTION
        desc = descs[ri] if ri < len(descs) else ""
        if len(desc) > 22:
            desc = desc[:20] + ".."
        draw.text((col_xs[5] + 4, ry + 3), desc, fill="black", font=font_sm)


def draw_sample_title_row(draw, tx1, ty1, tx2, ty2, image_index, font_lg, font_bold):
    """Draw 'SAMPLE Project' | 'SAMPLE' row with large text."""
    draw.rectangle([tx1, ty1, tx2, ty2], outline="black", width=2)

    # Vertical divider at SEPARATOR_X
    sep_x = int(CANVAS_W * SEPARATOR_X)
    draw.line([(sep_x, ty1), (sep_x, ty2)], fill="black", width=1)

    text_y = ty1 + (ty2 - ty1) // 2 - 18
    draw.text((tx1 + 15, text_y), "SAMPLE Project", fill="black", font=font_lg)
    draw.text((sep_x + 15, text_y), "SAMPLE", fill="black", font=font_bold)


def draw_flow_titles(draw, tx1, ty1, tx2, ty2, font_sm):
    """Draw disclaimer text + two diagram title rows."""
    draw.rectangle([tx1, ty1, tx2, ty2], outline="black", width=2)

    # Disclaimer (top portion, small text wrapped up to 4 lines)
    disclaimer_lines = []
    words = DISCLAIMER_TEXT.split()
    line = ""
    for w in words:
        test = line + " " + w if line else w
        if len(test) > 70:
            disclaimer_lines.append(line)
            line = w
        else:
            line = test
    if line:
        disclaimer_lines.append(line)

    dy = ty1 + 3
    for dl in disclaimer_lines[:4]:
        draw.text((tx1 + 10, dy), dl, fill="black", font=font_sm)
        dy += 16

    # Two diagram titles (bottom portion)
    title1, title2 = random.choice(DIAGRAM_TITLE_PAIRS)
    title_y = dy + 8
    draw.text((tx1 + 10, title_y), title1, fill="black", font=font_sm)
    draw.text((tx1 + 10, title_y + 18), title2, fill="black", font=font_sm)


def draw_data_grid(draw, tx1, ty1, tx2, ty2, image_index, font_sm, font_bold):
    """Draw 5-row data grid: PROJECT/ORGANIZATION, CONTRACTOR, DRAWING NAME, UNIT, SCALE/REV."""
    draw.rectangle([tx1, ty1, tx2, ty2], outline="black", width=2)

    n_rows = 5
    row_h = (ty2 - ty1) / n_rows

    # Column positions relative to title block width
    w = tx2 - tx1
    col1 = tx1 + int(w * 0.28)  # label | value
    col2 = tx1 + int(w * 0.53)  # second label
    col3 = tx1 + int(w * 0.78)  # second value

    # Row dividers
    for ri in range(1, n_rows):
        ry = ty1 + int(row_h * ri)
        draw.line([(tx1, ry), (tx2, ry)], fill="black", width=1)

    # Column dividers for all rows
    for col_x in [col1, col2, col3]:
        draw.line([(col_x, ty1), (col_x, ty2)], fill="black", width=1)

    # 5th column (REV) only on last row
    rev_col = tx2 - int(w * 0.12)
    last_row_y = ty1 + int(row_h * 4)
    draw.line([(rev_col, last_row_y), (rev_col, ty2)], fill="black", width=1)

    def row_y(ri):
        return ty1 + int(row_h * ri) + 4

    # Row 0: PROJECT | <name> | ORGANIZATION | <org>
    ry0 = row_y(0)
    proj_name = f"SYNTH-{random.randint(100, 999)}"
    draw.text((tx1 + 6, ry0), "PROJECT", fill="black", font=font_sm)
    draw.text((col1 + 6, ry0), proj_name, fill="black", font=font_bold)
    draw.text((col2 + 6, ry0), "ORGANIZATION", fill="black", font=font_sm)
    draw.text((col3 + 6, ry0), random.choice(ORGANIZATION_NAMES), fill="black", font=font_bold)

    # Row 1: CONTRACTOR PROJECT NO | AI-XX-XX | CONTR NO | NNN
    ry1 = row_y(1)
    proj_no = f"AI-{random.randint(10, 99)}-{random.randint(10, 99)}"
    draw.text((tx1 + 6, ry1), "CONTRACTOR PROJ NO", fill="black", font=font_sm)
    draw.text((col1 + 6, ry1), proj_no, fill="black", font=font_bold)
    draw.text((col2 + 6, ry1), "CONTR NO", fill="black", font=font_sm)
    draw.text((col3 + 6, ry1), f"{random.randint(1, 999)}", fill="black", font=font_bold)

    # Row 2: DRAWING NAME | SAMPLE_XXXX.JPG | CONTRACT NAME | <name>
    ry2 = row_y(2)
    contract = random.choice(CONTRACT_NAMES)
    draw.text((tx1 + 6, ry2), "DRAWING NAME", fill="black", font=font_sm)
    draw.text((col1 + 6, ry2), f"SAMPLE_{image_index}.JPG", fill="black", font=font_bold)
    draw.text((col2 + 6, ry2), "CONTRACT NAME", fill="black", font=font_sm)
    draw.text((col3 + 6, ry2), contract, fill="black", font=font_bold)

    # Row 3: UNIT | XX-XXXX | AREA | NNN
    ry3 = row_y(3)
    unit = f"{random.randint(10, 99)}-{random.randint(1000, 9999)}"
    draw.text((tx1 + 6, ry3), "UNIT", fill="black", font=font_sm)
    draw.text((col1 + 6, ry3), unit, fill="black", font=font_bold)
    draw.text((col2 + 6, ry3), "AREA", fill="black", font=font_sm)
    draw.text((col3 + 6, ry3), f"{random.randint(100, 999)}", fill="black", font=font_bold)

    # Row 4: SCALE | NONE | DRAW/SHEET NO | sheet | REV | rev
    ry4 = row_y(4)
    sheet = f"{random.randint(10000000, 99999999)}"
    rev = random.choice(["A", "B", "C", "D", "0", "1", "2"])
    draw.text((tx1 + 6, ry4), "SCALE", fill="black", font=font_sm)
    draw.text((col1 + 6, ry4), "NONE", fill="black", font=font_bold)
    draw.text((col2 + 6, ry4), "DRAW/SHEET NO", fill="black", font=font_sm)
    draw.text((col3 + 6, ry4), sheet, fill="black", font=font_bold)
    draw.text((rev_col + 6, ry4), "REV", fill="black", font=font_sm)
    draw.text((rev_col + 30, ry4), rev, fill="black", font=font_bold)


# ── Title block orchestrator ──────────────────────────────────────
def draw_title_block(draw, image_index, font, font_sm, font_bold, font_lg):
    """Draw the complete title block below the notes section.

    Layout (all within TITLE_AREA):
      y 0.700-0.760  Revision table
      y 0.760-0.790  SAMPLE title row
      y 0.790-0.845  Disclaimer + flow titles
      y 0.845-0.950  Data grid
    """
    tx1 = int(CANVAS_W * TITLE_AREA[0])
    tx2 = int(CANVAS_W * TITLE_AREA[2])
    ty1 = int(CANVAS_H * TITLE_AREA[1])
    ty2 = int(CANVAS_H * TITLE_AREA[3])

    # Section boundaries (pixel)
    rev_y1 = ty1
    rev_y2 = int(CANVAS_H * 0.760)
    sample_y1 = rev_y2
    sample_y2 = int(CANVAS_H * 0.790)
    flow_y1 = sample_y2
    flow_y2 = int(CANVAS_H * 0.845)
    grid_y1 = flow_y2
    grid_y2 = ty2

    draw_revision_table(draw, tx1, rev_y1, tx2, rev_y2, font_sm)
    draw_sample_title_row(draw, tx1, sample_y1, tx2, sample_y2, image_index, font_lg, font_bold)
    draw_flow_titles(draw, tx1, flow_y1, tx2, flow_y2, font_sm)
    draw_data_grid(draw, tx1, grid_y1, tx2, grid_y2, image_index, font_sm, font_bold)

    # Outer border for the entire right panel (notes + title block)
    outer_x1 = int(CANVAS_W * TITLE_LEFT_X)
    outer_y1 = int(CANVAS_H * NOTES_AREA[1])
    outer_x2 = tx2
    outer_y2 = ty2
    draw.rectangle([outer_x1, outer_y1, outer_x2, outer_y2], outline="black", width=3)


# ── Notes section ──────────────────────────────────────────────────
def draw_notes_section(draw, font, font_sm, font_bold):
    """Draw numbered notes section on the right side (above title block).

    Uses the SEPARATOR_X vertical line as left border (drawn separately).
    Notes area spans from NOTES_AREA y_min to y_max.
    """
    nx1 = int(CANVAS_W * NOTES_AREA[0])
    ny1 = int(CANVAS_H * NOTES_AREA[1])
    nx2 = int(CANVAS_W * NOTES_AREA[2])
    ny2 = int(CANVAS_H * NOTES_AREA[3])

    # "NOTES" header
    header_x = nx1 + (nx2 - nx1) // 2 - 40
    draw.text((header_x, ny1 + 5), "NOTES", fill="black", font=font_bold)

    # Numbered items (up to 26)
    line_y = ny1 + 40
    line_spacing = 32
    n_notes = random.randint(23, 26)
    deleted_indices = set(random.sample(range(n_notes), random.randint(6, 8)))
    notes_shuffled = random.sample(NOTES_POOL, min(n_notes, len(NOTES_POOL)))

    for idx in range(n_notes):
        num_str = f"{idx + 1}."
        if idx in deleted_indices:
            text = f"  {num_str}  DELETED"
        else:
            note = notes_shuffled[idx % len(notes_shuffled)]
            note = note.replace("{num}", str(random.randint(100, 9999)))
            text = f"  {num_str}  {note}"

        if len(text) > 55:
            text = text[:52] + "..."

        draw.text((nx1 + 10, line_y), text, fill="black", font=font_sm)
        line_y += line_spacing

        if line_y > ny2 - 20:
            break


# ── Paste symbol templates ─────────────────────────────────────────
def paste_symbols(img, placements):
    """Paste template images onto canvas at their placed positions."""
    for cx, cy, sw, sh, cid, tpath in placements:
        timg = Image.open(tpath).convert("RGBA")
        timg = timg.resize((sw, sh), Image.LANCZOS)
        px = cx - sw // 2
        py = cy - sh // 2
        if timg.mode == "RGBA":
            img.paste(timg, (px, py), timg)
        else:
            img.paste(timg, (px, py))
        timg.close()


# ── Noise ──────────────────────────────────────────────────────────
def apply_noise(img):
    """Apply slight brightness/contrast variation and sparse salt-and-pepper."""
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(random.uniform(0.95, 1.05))

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(random.uniform(0.95, 1.05))

    pixels = img.load()
    w, h = img.size
    n_noise = int(w * h * 0.0002)

    for _ in range(n_noise):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        pixels[x, y] = (255, 255, 255)

    for _ in range(n_noise):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        pixels[x, y] = (0, 0, 0)

    return img


# ── YOLO labels ────────────────────────────────────────────────────
def write_yolo_labels(placements, out_path):
    """Write YOLO format label file."""
    with open(out_path, "w") as f:
        for cx, cy, sw, sh, cid, _ in placements:
            nx = cx / CANVAS_W
            ny = cy / CANVAS_H
            nw = sw / CANVAS_W
            nh = sh / CANVAS_H
            f.write(f"{cid} {nx:.15f} {ny:.15f} {nw:.15f} {nh:.15f}\n")


# ── Main orchestrator ──────────────────────────────────────────────
def generate_images(n_images, seed=None):
    """Generate n synthetic P&ID images with YOLO annotations."""
    if seed is not None:
        random.seed(seed)

    templates = load_templates()

    GEN_IMAGES.mkdir(parents=True, exist_ok=True)
    GEN_LABELS.mkdir(parents=True, exist_ok=True)

    # Load fonts
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font
        font_bold = font
        font_lg = font

    for i in range(n_images):
        print(f"Generating image {i + 1}/{n_images}...", end=" ", flush=True)

        # 1. Grey canvas (random shade) + dashed border
        bg_val = random.randint(BG_COLOR_RANGE[0], BG_COLOR_RANGE[1])
        bg_color = (bg_val, bg_val, bg_val)
        img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg_color)
        draw = ImageDraw.Draw(img)

        bx1 = int(CANVAS_W * 0.02)
        by1 = int(CANVAS_H * 0.02)
        bx2 = int(CANVAS_W * 0.98)
        by2 = int(CANVAS_H * 0.98)
        draw_dashed_rect(draw, bx1, by1, bx2, by2, dash=24, gap=14, width=3)

        # 2. Generate pipe network
        h_pipes, v_pipes, junctions = generate_pipe_network()

        # 3. Place symbols on network
        placements, signal_connections = place_symbols_on_network(
            h_pipes, v_pipes, junctions, templates
        )

        # 4. Draw pipes (under symbols)
        draw_pipes(draw, h_pipes, v_pipes)

        # 5. Draw signal lines (under symbols)
        draw_signal_lines(draw, signal_connections)

        # 6. Paste symbol templates (on top of pipes)
        paste_symbols(img, placements)

        # Re-acquire draw after paste
        draw = ImageDraw.Draw(img)

        # 7. Draw text labels + pipe size labels
        draw_text_labels(draw, placements, font, font_sm)
        draw_pipe_size_labels(draw, h_pipes, v_pipes, font_sm)

        # 8. Draw notes section
        draw_notes_section(draw, font, font_sm, font_bold)

        # 9. Draw separator line + title block
        draw_separator_line(draw)
        draw_title_block(draw, i, font, font_sm, font_bold, font_lg)

        # 10. Apply noise
        img = apply_noise(img)

        # 11. Save JPEG + YOLO labels
        stem = f"gen_{i:04d}"
        img.save(GEN_IMAGES / f"{stem}.jpg", "JPEG", quality=85)
        write_yolo_labels(placements, GEN_LABELS / f"{stem}.txt")

        print(f"{len(placements)} symbols placed")
        img.close()

    print(f"\nDone! Generated {n_images} images in {GEN_IMAGES}")


# ── CLI ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Synthetic P&ID generator with YOLO annotations"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("extract", help="Extract symbol templates from training images")

    gen_p = sub.add_parser("generate", help="Generate synthetic P&ID images")
    gen_p.add_argument("-n", "--count", type=int, default=50,
                       help="Number of images to generate (default: 50)")
    gen_p.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducibility")

    all_p = sub.add_parser("all", help="Extract templates then generate images")
    all_p.add_argument("-n", "--count", type=int, default=50,
                       help="Number of images to generate (default: 50)")
    all_p.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducibility")

    args = parser.parse_args()

    if args.command == "extract":
        extract_templates()
    elif args.command == "generate":
        generate_images(args.count, args.seed)
    elif args.command == "all":
        extract_templates()
        generate_images(args.count, args.seed)


if __name__ == "__main__":
    main()
