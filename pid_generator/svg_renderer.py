"""SVG symbol rendering for P&ID diagrams.

This module provides utilities to render SVG symbols from the symbols folder
onto the PIL canvas during P&ID generation.
"""

import io
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False


def render_svg_to_pil(
    svg_path: Path | str,
    output_width: int = 64,
    output_height: int = 64,
) -> Image.Image | None:
    """Render an SVG file to a PIL Image.

    Args:
        svg_path: Path to the SVG file.
        output_width: Target width in pixels.
        output_height: Target height in pixels.

    Returns:
        A PIL Image, or None if rendering failed or cairosvg not available.
    """
    if not HAS_CAIROSVG:
        return None

    try:
        svg_path = Path(svg_path)
        if not svg_path.exists():
            print(f"SVG file not found: {svg_path}")
            return None

        # Use cairosvg to convert SVG to PNG in memory
        png_bytes = cairosvg.svg2png(
            url=str(svg_path),
            write_to=None,
            output_width=output_width,
            output_height=output_height,
        )

        if png_bytes is None:
            return None

        # Open PNG as PIL Image
        img = Image.open(io.BytesIO(png_bytes))
        return img.convert("RGBA")

    except Exception as e:
        print(f"Error rendering SVG {svg_path}: {e}")
        return None


def extract_svg_dimensions(svg_path: Path | str) -> tuple[float, float] | None:
    """Extract the width and height from an SVG file.

    Args:
        svg_path: Path to the SVG file.

    Returns:
        A tuple (width, height) in points (pt), or None if extraction failed.
    """
    try:
        svg_path = Path(svg_path)
        if not svg_path.exists():
            return None

        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Remove namespace for easier access
        tag = root.tag
        if "}" in tag:
            ns = tag[:tag.index("}") + 1]
            root_tag = "svg"
        else:
            ns = ""

        width_str = root.get("width", "")
        height_str = root.get("height", "")

        def parse_dimension(s: str) -> float | None:
            """Parse a dimension string (e.g., '474.838871pt')."""
            s = s.strip()
            if s.endswith("pt"):
                return float(s[:-2])
            elif s.endswith("px"):
                return float(s[:-2])
            elif s.endswith("mm"):
                return float(s[:-2]) * 2.834645669  # mm to pt
            else:
                try:
                    return float(s)
                except ValueError:
                    return None

        width = parse_dimension(width_str)
        height = parse_dimension(height_str)

        if width is not None and height is not None:
            return (width, height)

        # Fall back to viewBox
        viewbox = root.get("viewBox", "")
        if viewbox:
            parts = viewbox.split()
            if len(parts) == 4:
                try:
                    _, _, vb_w, vb_h = [float(p) for p in parts]
                    return (vb_w, vb_h)
                except ValueError:
                    pass

        return None

    except Exception as e:
        print(f"Error extracting SVG dimensions from {svg_path}: {e}")
        return None


def scale_svg_dimensions(
    orig_width: float,
    orig_height: float,
    target_size: int = 64,
) -> tuple[int, int]:
    """Scale SVG dimensions to fit within a square of target_size.

    Maintains aspect ratio and returns new (width, height) in pixels.

    Args:
        orig_width: Original width (in any unit).
        orig_height: Original height (in any unit).
        target_size: Maximum width or height in pixels.

    Returns:
        A tuple (new_width, new_height) in pixels.
    """
    if orig_width <= 0 or orig_height <= 0:
        return (target_size, target_size)

    aspect_ratio = orig_width / orig_height
    if orig_width >= orig_height:
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
    else:
        new_height = target_size
        new_width = int(target_size * aspect_ratio)

    return (new_width, new_height)

