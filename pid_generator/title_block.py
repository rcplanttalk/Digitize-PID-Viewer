"""Title block metadata generator and renderer (§15, ISO 7200:2004).

Public API
----------
generate_title_block_metadata(idx, seed) -> dict
draw_title_block(draw, metadata)         -> None
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import TYPE_CHECKING

from pid_generator.constants import (
    CANVAS_H,
    CANVAS_W,
    CLIENT_NAMES,
    CONTRACT_NAMES,
    DIAGRAM_TITLE_PAIRS,
    DISCLAIMER_TEXT,
    MARGIN,
    ORGANIZATION_NAMES,
    PERSON_INITIALS,
    PLANT_NAMES,
    REVISION_DESCRIPTIONS,
    TITLE_BLOCK_H,
    TITLE_BLOCK_REV_H,
    TITLE_BLOCK_REVS,
    TITLE_BLOCK_W,
)

if TYPE_CHECKING:
    from PIL import ImageDraw


def generate_title_block_metadata(
    idx: int = 1,
    seed: int | None = None,
) -> dict:
    """Return a fully-populated ISO 7200:2004 title block metadata dict.

    Mandatory fields (ISO 7200:2004 §5):
        legal_owner, doc_number, doc_title, doc_title_2, doc_type,
        creator, creation_date, approval_person, approval_date, sheet_number.

    Optional fields rendered by the generator:
        client, plant, project_number, scale, revisions, disclaimer.
    """
    rng = random.Random(seed)

    today = date(2026, 2, 16)
    creation_date = today - timedelta(days=rng.randint(30, 365))
    approval_date = creation_date + timedelta(days=rng.randint(1, 14))
    title_pair    = rng.choice(DIAGRAM_TITLE_PAIRS)
    n_revs        = rng.randint(1, TITLE_BLOCK_REVS)

    revisions = []
    rev_date  = creation_date
    for letter in "ABCDE"[:n_revs]:
        rev_date = rev_date + timedelta(days=rng.randint(7, 60))
        revisions.append({
            "rev":         letter,
            "description": rng.choice(REVISION_DESCRIPTIONS),
            "date":        rev_date.strftime("%Y-%m-%d"),
            "by":          rng.choice(PERSON_INITIALS),
            "chk":         rng.choice(PERSON_INITIALS),
        })

    proj_num = f"PRJ-{rng.randint(1000, 9999)}"

    return {
        "legal_owner":     rng.choice(ORGANIZATION_NAMES),
        "doc_number":      f"{proj_num}-PID-{idx:04d}",
        "doc_title":       title_pair[0],
        "doc_title_2":     title_pair[1],
        "doc_type":        rng.choice(CONTRACT_NAMES),
        "creator":         rng.choice(PERSON_INITIALS),
        "creation_date":   creation_date.strftime("%Y-%m-%d"),
        "approval_person": rng.choice(PERSON_INITIALS),
        "approval_date":   approval_date.strftime("%Y-%m-%d"),
        "sheet_number":    f"P&ID-{idx:02d}",
        "client":          rng.choice(CLIENT_NAMES),
        "plant":           rng.choice(PLANT_NAMES),
        "project_number":  proj_num,
        "scale":           "NTS",
        "revisions":       revisions,
        "disclaimer":      DISCLAIMER_TEXT,
        "position":        rng.choice(["bottom", "right"]),
    }


def draw_title_block(
    draw: ImageDraw.ImageDraw,
    metadata: dict | None = None,
) -> None:
    """Draw a fully-populated ISO 7200-compliant title block (§15).

    Position is controlled by ``metadata["position"]``:

    - ``"bottom"`` (default) — horizontal strip along the bottom of the canvas::

        ┌──────────────────────┬───────────────────┬──────────────────┐
        │ LEGAL OWNER / TITLES │ REV | DESC | DATE  │ DOC NUMBER       │
        │ DRN: …  APPR: …      │ revision rows      │ SHEET    SCALE   │
        └──────────────────────┴───────────────────┴──────────────────┘
          DISCLAIMER TEXT (two grey lines below the block)

    - ``"right"`` — vertical strip along the right side of the canvas::

        ┌───────────────────────┐
        │ DOC NO. / TYPE / PROJ │  stamp section
        │ SHEET   │ SCALE       │
        ├───────────────────────┤
        │ REV │ DESC │ DATE …   │  revision table
        ├───────────────────────┤
        │ LEGAL OWNER / TITLES  │  info section
        │ DRN: …  APPR: …       │
        └───────────────────────┘
    """
    from pid_generator.renderer import _font  # local import avoids circular dep

    if metadata is None:
        metadata = {}

    def _get(key: str, default: str = "") -> str:
        return str(metadata.get(key, default))

    font    = _font(small=False)
    font_sm = _font(small=True)
    fg      = "black"
    grey    = (100, 100, 100)
    pad     = 6

    position = metadata.get("position", "bottom")

    if position == "right":
        # Vertical strip on the right side
        bx0 = CANVAS_W - MARGIN - TITLE_BLOCK_W
        bx1 = CANVAS_W - MARGIN
        by0 = MARGIN
        by1 = CANVAS_H - MARGIN

        draw.rectangle([bx0, by0, bx1, by1], outline=fg, width=2, fill=(252, 252, 252))

        # Section heights
        stamp_h  = 160
        rev_h    = 20 + TITLE_BLOCK_REVS * TITLE_BLOCK_REV_H  # header + rows
        stamp_y1 = by0 + stamp_h
        rev_y1   = stamp_y1 + rev_h
        info_y0  = rev_y1

        draw.line([(bx0, stamp_y1), (bx1, stamp_y1)], fill=fg, width=1)
        draw.line([(bx0, rev_y1),   (bx1, rev_y1)],   fill=fg, width=1)

        # Stamp section
        cy = by0 + pad
        draw.text((bx0 + pad, cy),      "DOC NO.", fill=grey, font=font_sm)
        draw.text((bx0 + pad, cy + 18), _get("doc_number"), fill=fg, font=font)
        draw.text((bx0 + pad, cy + 46), "TYPE: " + _get("doc_type"),       fill=grey, font=font_sm)
        draw.text((bx0 + pad, cy + 64), "PROJ: " + _get("project_number"), fill=grey, font=font_sm)
        sheet_y = by0 + stamp_h - 50
        mid_x   = bx0 + TITLE_BLOCK_W // 2
        draw.line([(bx0, sheet_y), (bx1, sheet_y)], fill=fg, width=1)
        draw.line([(mid_x, sheet_y), (mid_x, stamp_y1)], fill=fg, width=1)
        draw.text((bx0 + pad, sheet_y + pad),      "SHEET", fill=grey, font=font_sm)
        draw.text((bx0 + pad, sheet_y + pad + 18), _get("sheet_number"), fill=fg, font=font)
        draw.text((mid_x + pad, sheet_y + pad),      "SCALE",               fill=grey, font=font_sm)
        draw.text((mid_x + pad, sheet_y + pad + 18), _get("scale", "NTS"),  fill=fg,   font=font)

        # Revision table
        hdr_h      = 20
        col_widths = [30, 210, 110, 70, 70]
        headers    = ["REV", "DESCRIPTION", "DATE", "BY", "CHK"]
        draw.rectangle([bx0, stamp_y1, bx1, stamp_y1 + hdr_h],
                       fill=(230, 230, 230), outline=fg, width=1)
        rx = bx0
        for w, hdr in zip(col_widths, headers):
            draw.text((rx + 3, stamp_y1 + 3), hdr, fill=fg, font=font_sm)
            rx += w
            draw.line([(rx, stamp_y1), (rx, stamp_y1 + hdr_h)], fill=fg, width=1)
        for row_i, rev in enumerate(metadata.get("revisions", [])[:TITLE_BLOCK_REVS]):
            ry0 = stamp_y1 + hdr_h + row_i * TITLE_BLOCK_REV_H
            draw.line([(bx0, ry0), (bx1, ry0)], fill=fg, width=1)
            values = [rev.get("rev", ""), rev.get("description", ""),
                      rev.get("date", ""), rev.get("by", ""), rev.get("chk", "")]
            rx = bx0
            for w, val in zip(col_widths, values):
                draw.text((rx + 3, ry0 + 5), val, fill=fg, font=font_sm)
                rx += w
                draw.line([(rx, ry0), (rx, ry0 + TITLE_BLOCK_REV_H)], fill=fg, width=1)

        # Info section
        cy = info_y0 + pad
        draw.text((bx0 + pad, cy), _get("legal_owner", "ORGANISATION"), fill=fg, font=font)
        cy += 24
        draw.text((bx0 + pad, cy), f"CLIENT: {_get('client')}", fill=grey, font=font_sm)
        cy += 18
        draw.text((bx0 + pad, cy), f"PLANT:  {_get('plant')}",  fill=grey, font=font_sm)
        cy += 18
        draw.text((bx0 + pad, cy), _get("doc_title", "DIAGRAM TITLE"), fill=fg, font=font)
        cy += 24
        draw.text((bx0 + pad, cy), _get("doc_title_2"), fill=fg, font=font_sm)
        draw.text(
            (bx0 + pad, by1 - 20),
            f"DRN: {_get('creator')}  {_get('creation_date')}   "
            f"APPR: {_get('approval_person')}  {_get('approval_date')}",
            fill=grey, font=font_sm,
        )

        # Disclaimer along the bottom margin (left side, away from the block)
        disclaimer = _get("disclaimer", DISCLAIMER_TEXT)
        split_at   = disclaimer.rfind(" ", 0, len(disclaimer) // 2)
        draw.text((MARGIN + pad, by1 + 4),  disclaimer[:split_at],     fill=grey, font=font_sm)
        draw.text((MARGIN + pad, by1 + 18), disclaimer[split_at + 1:], fill=grey, font=font_sm)

    else:
        # Default: horizontal strip along the bottom
        x0 = MARGIN
        x1 = CANVAS_W - MARGIN
        y1 = CANVAS_H - MARGIN
        y0 = y1 - TITLE_BLOCK_H

        draw.rectangle([x0, y0, x1, y1], outline=fg, width=2, fill=(252, 252, 252))

        total_w   = x1 - x0
        rev_w     = 500
        stamp_w   = 260
        left_w    = total_w - rev_w - stamp_w
        div_rev   = x0 + left_w
        div_stamp = div_rev + rev_w

        draw.line([(div_rev,   y0), (div_rev,   y1)], fill=fg, width=1)
        draw.line([(div_stamp, y0), (div_stamp, y1)], fill=fg, width=1)

        # Left panel
        cy = y0 + pad
        draw.text((x0 + pad, cy), _get("legal_owner", "ORGANISATION"), fill=fg, font=font)
        cy += 24
        draw.text((x0 + pad, cy), f"CLIENT: {_get('client')}", fill=grey, font=font_sm)
        cy += 18
        draw.text((x0 + pad, cy), f"PLANT:  {_get('plant')}",  fill=grey, font=font_sm)
        cy += 18
        draw.text((x0 + pad, cy), _get("doc_title", "DIAGRAM TITLE"), fill=fg, font=font)
        cy += 24
        draw.text((x0 + pad, cy), _get("doc_title_2"), fill=fg, font=font_sm)
        draw.text(
            (x0 + pad, y1 - 20),
            f"DRN: {_get('creator')}  {_get('creation_date')}   "
            f"APPR: {_get('approval_person')}  {_get('approval_date')}",
            fill=grey, font=font_sm,
        )

        # Revision table
        hdr_h      = 20
        col_widths = [30, 210, 110, 70, 70]
        headers    = ["REV", "DESCRIPTION", "DATE", "BY", "CHK"]
        draw.rectangle([div_rev, y0, div_stamp, y0 + hdr_h],
                       fill=(230, 230, 230), outline=fg, width=1)
        rx = div_rev
        for w, hdr in zip(col_widths, headers):
            draw.text((rx + 3, y0 + 3), hdr, fill=fg, font=font_sm)
            rx += w
            draw.line([(rx, y0), (rx, y0 + hdr_h)], fill=fg, width=1)
        for row_i, rev in enumerate(metadata.get("revisions", [])[:TITLE_BLOCK_REVS]):
            ry0 = y0 + hdr_h + row_i * TITLE_BLOCK_REV_H
            draw.line([(div_rev, ry0), (div_stamp, ry0)], fill=fg, width=1)
            values = [rev.get("rev", ""), rev.get("description", ""),
                      rev.get("date", ""), rev.get("by", ""), rev.get("chk", "")]
            rx = div_rev
            for w, val in zip(col_widths, values):
                draw.text((rx + 3, ry0 + 5), val, fill=fg, font=font_sm)
                rx += w
                draw.line([(rx, ry0), (rx, ry0 + TITLE_BLOCK_REV_H)], fill=fg, width=1)

        # Right stamp column
        mid_y = y0 + (TITLE_BLOCK_H - 20) // 2
        draw.line([(div_stamp, mid_y), (x1, mid_y)], fill=fg, width=1)
        draw.text((div_stamp + pad, y0 + pad),      "DOC NO.", fill=grey, font=font_sm)
        draw.text((div_stamp + pad, y0 + pad + 18), _get("doc_number"), fill=fg, font=font)
        draw.text((div_stamp + pad, y0 + pad + 48), "TYPE: " + _get("doc_type"),       fill=grey, font=font_sm)
        draw.text((div_stamp + pad, y0 + pad + 68), "PROJ: " + _get("project_number"), fill=grey, font=font_sm)
        draw.text((div_stamp + pad, mid_y + pad),      "SHEET", fill=grey, font=font_sm)
        draw.text((div_stamp + pad, mid_y + pad + 18), _get("sheet_number"), fill=fg, font=font)
        scale_x = div_stamp + stamp_w // 2
        draw.text((scale_x, mid_y + pad),      "SCALE",               fill=grey, font=font_sm)
        draw.text((scale_x, mid_y + pad + 18), _get("scale", "NTS"),  fill=fg,   font=font)

        # Disclaimer strip
        disclaimer = _get("disclaimer", DISCLAIMER_TEXT)
        split_at   = disclaimer.rfind(" ", 0, len(disclaimer) // 2)
        draw.text((x0 + pad, y1 + 4),  disclaimer[:split_at],     fill=grey, font=font_sm)
        draw.text((x0 + pad, y1 + 18), disclaimer[split_at + 1:], fill=grey, font=font_sm)
