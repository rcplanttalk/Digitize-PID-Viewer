"""Title block metadata generator and renderer (§15, ISO 7200:2004).

ISO 7200:2004 specifies the data fields required in engineering drawing title
blocks.  This module covers:

  Mandatory fields (ISO 7200 §5):
    legal_owner, doc_number, doc_title, creator, creation_date,
    approval_person, approval_date, doc_type, sheet_number

  Optional fields rendered when present:
    client, plant, project_number, revision_index, revision_description,
    revision_date, checked_by, scale, language_code

Public API
----------
generate_title_block_metadata(idx, seed) -> dict
draw_title_block(draw, metadata)         -> None   (replaces renderer stub)
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import TYPE_CHECKING

from pid_generator.constants import (
    CLIENT_NAMES,
    CONTRACT_NAMES,
    DIAGRAM_TITLE_PAIRS,
    DISCLAIMER_TEXT,
    ORGANIZATION_NAMES,
    PERSON_INITIALS,
    PLANT_NAMES,
    REVISION_DESCRIPTIONS,
)
from pid_generator.layout import CANVAS_H, CANVAS_W, MARGIN

if TYPE_CHECKING:
    from PIL import ImageDraw

# ---------------------------------------------------------------------------
# Layout constants for the title block (§15)
# ---------------------------------------------------------------------------

BLOCK_H = 180  # total title block height in pixels
BLOCK_H_REV = 28  # height per revision row
REV_ROWS = 3  # number of revision rows to render

# ---------------------------------------------------------------------------
# Metadata generator
# ---------------------------------------------------------------------------


def generate_title_block_metadata(
    idx: int = 1,
    seed: int | None = None,
) -> dict:
    """Return a fully-populated title block metadata dict (ISO 7200:2004).

    All fields are drawn randomly from their constant pools.  The result
    can be passed directly to ``draw_title_block()``.

    ISO 7200 mandatory fields present in the returned dict
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``legal_owner``     Legal owner / originating organisation name.
    ``doc_number``      Unique document identification number.
    ``doc_title``       Two-line diagram title.
    ``doc_title_2``     Second title line (optional in spec, common in practice).
    ``doc_type``        Document type string (e.g. "P&ID").
    ``creator``         Initials of the drawing creator (draughtsman).
    ``creation_date``   ISO-8601 date string.
    ``approval_person`` Initials of the approving engineer.
    ``approval_date``   ISO-8601 date string.
    ``sheet_number``    Sheet identifier, e.g. ``"P&ID-03"``.

    Additional fields (ISO 7200 optional / industry practice)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``client``          Client / owner company name.
    ``plant``           Facility or unit name.
    ``project_number``  Synthetic project number string.
    ``scale``           Always ``"NTS"`` (Not to Scale).
    ``revisions``       List of revision row dicts (up to REV_ROWS).
    ``disclaimer``      Full disclaimer text from DISCLAIMER_TEXT.

    Args:
        idx:  1-based diagram index — used to make doc_number unique.
        seed: Optional RNG seed.

    Returns:
        Metadata dict suitable for ``draw_title_block()``.
    """
    rng = random.Random(seed)

    # Dates: creation 30–365 days ago; approval 1–14 days after creation
    today = date(2026, 2, 16)
    create_offset = rng.randint(30, 365)
    creation_date = today - timedelta(days=create_offset)
    approval_date = creation_date + timedelta(days=rng.randint(1, 14))

    title_pair = rng.choice(DIAGRAM_TITLE_PAIRS)
    rev_letters = "ABCDE"
    n_revs = rng.randint(1, REV_ROWS)

    # Build revision table rows
    revisions = []
    rev_date = creation_date
    for i in range(n_revs):
        rev_date = rev_date + timedelta(days=rng.randint(7, 60))
        revisions.append(
            {
                "rev": rev_letters[i],
                "description": rng.choice(REVISION_DESCRIPTIONS),
                "date": rev_date.strftime("%Y-%m-%d"),
                "by": rng.choice(PERSON_INITIALS),
                "chk": rng.choice(PERSON_INITIALS),
            }
        )

    proj_num = f"PRJ-{rng.randint(1000, 9999)}"
    doc_num = f"{proj_num}-PID-{idx:04d}"

    return {
        # ISO 7200 mandatory
        "legal_owner": rng.choice(ORGANIZATION_NAMES),
        "doc_number": doc_num,
        "doc_title": title_pair[0],
        "doc_title_2": title_pair[1],
        "doc_type": rng.choice(CONTRACT_NAMES),
        "creator": rng.choice(PERSON_INITIALS),
        "creation_date": creation_date.strftime("%Y-%m-%d"),
        "approval_person": rng.choice(PERSON_INITIALS),
        "approval_date": approval_date.strftime("%Y-%m-%d"),
        "sheet_number": f"P&ID-{idx:02d}",
        # ISO 7200 optional / industry standard
        "client": rng.choice(CLIENT_NAMES),
        "plant": rng.choice(PLANT_NAMES),
        "project_number": proj_num,
        "scale": "NTS",
        "revisions": revisions,
        "disclaimer": DISCLAIMER_TEXT,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def draw_title_block(
    draw: ImageDraw.ImageDraw,
    metadata: dict | None = None,
) -> None:
    """Draw a fully-populated ISO 7200-compliant title block (§15).

    Layout (bottom of canvas, full width)::

        ┌──────────────────────────────────┬───────────────┬──────────────┐
        │ LEGAL OWNER                      │ DOC NUMBER    │ SHEET        │
        │ CLIENT                           │ DOC TYPE      │ SCALE  NTS   │
        │ PLANT                            ├───────────────┤              │
        │ TITLE LINE 1                     │ Rev | Desc | Date | By | Chk │
        │ TITLE LINE 2                     │ ... (up to 3 rows)           │
        │ Created: DATE  Drn: XX  Appr: YY │                              │
        ├──────────────────────────────────┴───────────────┴──────────────┤
        │ DISCLAIMER TEXT                                                  │
        └──────────────────────────────────────────────────────────────────┘

    Args:
        draw:     ImageDraw context on the full canvas.
        metadata: Dict from ``generate_title_block_metadata()``.
                  Falls back to placeholder strings if None or missing keys.
    """
    from pid_generator.renderer import _font  # local import to avoid circular dependency

    if metadata is None:
        metadata = {}

    def _get(key: str, default: str = "") -> str:
        return str(metadata.get(key, default))

    font = _font(small=False)
    font_sm = _font(small=True)
    fg = "black"
    grey = (100, 100, 100)

    x0 = MARGIN
    x1 = CANVAS_W - MARGIN
    y1 = CANVAS_H - MARGIN
    y0 = y1 - BLOCK_H

    pad = 6  # inner padding

    # -----------------------------------------------------------------------
    # Outer title block rectangle
    # -----------------------------------------------------------------------
    draw.rectangle([x0, y0, x1, y1], outline=fg, width=2, fill=(252, 252, 252))

    # -----------------------------------------------------------------------
    # Vertical dividers: left info panel | revision table | right stamps
    # -----------------------------------------------------------------------
    total_w = x1 - x0
    rev_w = 500  # width of revision table column
    stamp_w = 260  # width of doc-number / sheet column
    left_w = total_w - rev_w - stamp_w

    div_rev = x0 + left_w
    div_stamp = div_rev + rev_w

    draw.line([(div_rev, y0), (div_rev, y1)], fill=fg, width=1)
    draw.line([(div_stamp, y0), (div_stamp, y1)], fill=fg, width=1)

    # -----------------------------------------------------------------------
    # Left panel: org, client, plant, titles, created/approved
    # -----------------------------------------------------------------------
    cy = y0 + pad

    draw.text((x0 + pad, cy), _get("legal_owner", "ORGANISATION"), fill=fg, font=font)
    cy += 24

    draw.text((x0 + pad, cy), f"CLIENT: {_get('client')}", fill=grey, font=font_sm)
    cy += 18

    draw.text((x0 + pad, cy), f"PLANT:  {_get('plant')}", fill=grey, font=font_sm)
    cy += 18

    draw.text((x0 + pad, cy), _get("doc_title", "DIAGRAM TITLE"), fill=fg, font=font)
    cy += 24

    draw.text((x0 + pad, cy), _get("doc_title_2"), fill=fg, font=font_sm)
    cy += 20

    # Created / approved line
    sig_line = (
        f"DRN: {_get('creator')}  {_get('creation_date')}   APPR: {_get('approval_person')}  {_get('approval_date')}"
    )
    draw.text((x0 + pad, y1 - 20), sig_line, fill=grey, font=font_sm)

    # -----------------------------------------------------------------------
    # Revision table (middle column)
    # -----------------------------------------------------------------------
    # Header row
    hdr_h = 20
    draw.rectangle([div_rev, y0, div_stamp, y0 + hdr_h], fill=(230, 230, 230), outline=fg, width=1)
    col_widths = [30, 210, 110, 70, 70]  # Rev, Description, Date, By, Chk
    headers = ["REV", "DESCRIPTION", "DATE", "BY", "CHK"]
    rx = div_rev
    for w, hdr in zip(col_widths, headers):
        draw.text((rx + 3, y0 + 3), hdr, fill=fg, font=font_sm)
        rx += w
        draw.line([(rx, y0), (rx, y0 + hdr_h)], fill=fg, width=1)

    # Revision rows
    revisions = metadata.get("revisions", [])
    for row_i, rev in enumerate(revisions[:REV_ROWS]):
        ry0 = y0 + hdr_h + row_i * BLOCK_H_REV
        ry1 = ry0 + BLOCK_H_REV
        draw.line([(div_rev, ry0), (div_stamp, ry0)], fill=fg, width=1)
        values = [
            rev.get("rev", ""),
            rev.get("description", ""),
            rev.get("date", ""),
            rev.get("by", ""),
            rev.get("chk", ""),
        ]
        rx = div_rev
        for w, val in zip(col_widths, values):
            draw.text((rx + 3, ry0 + 5), val, fill=fg, font=font_sm)
            rx += w
            draw.line([(rx, ry0), (rx, ry1)], fill=fg, width=1)

    # -----------------------------------------------------------------------
    # Right stamp column: doc number, doc type, sheet, scale
    # -----------------------------------------------------------------------
    # Doc number box (top half)
    mid_y = y0 + (BLOCK_H - 20) // 2
    draw.line([(div_stamp, mid_y), (x1, mid_y)], fill=fg, width=1)

    draw.text((div_stamp + pad, y0 + pad), "DOC NO.", fill=grey, font=font_sm)
    draw.text((div_stamp + pad, y0 + pad + 18), _get("doc_number"), fill=fg, font=font)

    draw.text((div_stamp + pad, y0 + pad + 48), "TYPE: " + _get("doc_type"), fill=grey, font=font_sm)

    draw.text((div_stamp + pad, y0 + pad + 68), "PROJ: " + _get("project_number"), fill=grey, font=font_sm)

    # Sheet / scale (bottom half)
    draw.text((div_stamp + pad, mid_y + pad), "SHEET", fill=grey, font=font_sm)
    draw.text((div_stamp + pad, mid_y + pad + 18), _get("sheet_number"), fill=fg, font=font)

    scale_x = div_stamp + stamp_w // 2
    draw.text((scale_x, mid_y + pad), "SCALE", fill=grey, font=font_sm)
    draw.text((scale_x, mid_y + pad + 18), _get("scale", "NTS"), fill=fg, font=font)

    # -----------------------------------------------------------------------
    # Disclaimer strip below title block
    # -----------------------------------------------------------------------
    disclaimer = _get("disclaimer", DISCLAIMER_TEXT)
    # Wrap to two lines if needed
    half = len(disclaimer) // 2
    space = disclaimer.rfind(" ", 0, half)
    line1 = disclaimer[:space]
    line2 = disclaimer[space + 1 :]
    draw.text((x0 + pad, y1 + 4), line1, fill=grey, font=font_sm)
    draw.text((x0 + pad, y1 + 18), line2, fill=grey, font=font_sm)
