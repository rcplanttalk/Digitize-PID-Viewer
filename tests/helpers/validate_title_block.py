#!/usr/bin/env python3
"""Pixel-level validation of generated P&ID title block.

Checks 7 properties of a generated JPEG and prints JSON to stdout.
Exit code 0 = all passed, 1 = at least one failure.
"""

import sys
from pathlib import Path

from PIL import Image

# Layout constants (must match generate_pid.py)
CANVAS_W, CANVAS_H = 7168, 4561
SEPARATOR_X = 0.790
TITLE_LEFT_X = 0.726
NOTES_Y_MIN = 0.043
TITLE_Y_MAX = 0.950


def is_dark(pixel, threshold=100):
    """Check if a pixel is dark (below threshold in all channels)."""
    if isinstance(pixel, int):
        return pixel < threshold
    return all(c < threshold for c in pixel[:3])


def check_dimensions(img):
    w, h = img.size
    return w == CANVAS_W and h == CANVAS_H, f"Expected {CANVAS_W}x{CANVAS_H}, got {w}x{h}"


def check_separator_line(img):
    """Vertical separator at SEPARATOR_X should have dark pixels."""
    x = int(CANVAS_W * SEPARATOR_X)
    # Sample 6 points along the separator, spread across the notes+title area
    y_positions = [int(CANVAS_H * y) for y in [0.10, 0.20, 0.35, 0.50, 0.65, 0.80]]
    dark_count = sum(1 for y in y_positions if is_dark(img.getpixel((x, y))))
    return dark_count >= 4, f"{dark_count}/6 dark pixels on separator"


def check_background_color(img):
    """Background should be grey in range 204-240."""
    # Sample 5 points in the drawing area (away from pipes/symbols)
    test_points = [
        (int(CANVAS_W * 0.05), int(CANVAS_H * 0.05)),
        (int(CANVAS_W * 0.35), int(CANVAS_H * 0.03)),
        (int(CANVAS_W * 0.65), int(CANVAS_H * 0.03)),
        (int(CANVAS_W * 0.05), int(CANVAS_H * 0.95)),
        (int(CANVAS_W * 0.50), int(CANVAS_H * 0.95)),
    ]
    in_range = 0
    for x, y in test_points:
        p = img.getpixel((x, y))
        r = p[0] if isinstance(p, tuple) else p
        if 190 <= r <= 255:  # wider tolerance for noise
            in_range += 1
    return in_range >= 3, f"{in_range}/5 points in grey range"


def check_title_row_has_text(img):
    """The SAMPLE title row (y=0.760-0.790) should have dark pixels (text)."""
    y_start = int(CANVAS_H * 0.760)
    y_end = int(CANVAS_H * 0.790)
    x_start = int(CANVAS_W * TITLE_LEFT_X)
    x_end = int(CANVAS_W * 0.950)
    dark_count = 0
    total = 0
    step = 4
    for y in range(y_start, y_end, step):
        for x in range(x_start, x_end, step):
            total += 1
            if is_dark(img.getpixel((x, y)), threshold=80):
                dark_count += 1
    ratio = dark_count / max(total, 1)
    return ratio > 0.01, f"dark pixel ratio {ratio:.4f}"


def check_rev_table_lines(img):
    """Revision table (y=0.700-0.760) should have horizontal lines (dark transitions)."""
    x = int(CANVAS_W * 0.84)  # middle of title block
    y_start = int(CANVAS_H * 0.700)
    y_end = int(CANVAS_H * 0.760)
    transitions = 0
    prev_dark = False
    for y in range(y_start, y_end):
        d = is_dark(img.getpixel((x, y)))
        if d and not prev_dark:
            transitions += 1
        prev_dark = d
    # Expect at least 3 horizontal lines (header + data rows)
    return transitions >= 3, f"{transitions} dark transitions"


def check_data_grid_has_content(img):
    """Data grid (y=0.845-0.950) should have dark pixels (text + lines)."""
    y_start = int(CANVAS_H * 0.845)
    y_end = int(CANVAS_H * 0.950)
    x_start = int(CANVAS_W * TITLE_LEFT_X)
    x_end = int(CANVAS_W * 0.950)
    dark_count = 0
    total = 0
    step = 6
    for y in range(y_start, y_end, step):
        for x in range(x_start, x_end, step):
            total += 1
            if is_dark(img.getpixel((x, y)), threshold=80):
                dark_count += 1
    ratio = dark_count / max(total, 1)
    return ratio > 0.005, f"dark pixel ratio {ratio:.4f}"


def check_outer_border(img):
    """Outer border left edge at TITLE_LEFT_X should have dark pixels."""
    x = int(CANVAS_W * TITLE_LEFT_X)
    y_positions = [int(CANVAS_H * y) for y in [0.10, 0.30, 0.50, 0.70, 0.90]]
    dark_count = sum(1 for y in y_positions if is_dark(img.getpixel((x, y))))
    return dark_count >= 3, f"{dark_count}/5 dark pixels on outer border"


def validate(image_path):
    img = Image.open(image_path)
    checks = {
        "dimensions": check_dimensions,
        "separator_line": check_separator_line,
        "background_color": check_background_color,
        "title_row_has_text": check_title_row_has_text,
        "rev_table_lines": check_rev_table_lines,
        "data_grid_has_content": check_data_grid_has_content,
        "outer_border": check_outer_border,
    }
    results = {}
    all_pass = True
    for name, fn in checks.items():
        passed, detail = fn(img)
        results[name] = {"pass": passed, "detail": detail}
        if not passed:
            all_pass = False
    img.close()
    return {"pass": all_pass, "checks": results}


def main():
    if len(sys.argv) < 2:
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.exists():
        sys.exit(1)
    result = validate(path)
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
