"""Constant pools for the P&ID generator (§2, §11, §13, §15)."""

from __future__ import annotations

from dataclasses import dataclass

# §2 / §13 — Pipe sizes and spec codes

PIPE_SIZES: list[int] = [2, 4, 6, 8, 10, 12, 14, 16]

PIPE_SPEC_CODES: list[str] = [
    "JD",
    "CK",
    "AB",
    "EF",
    "GH",
    "PN",
    "WR",
    "ST",
    "HX",
    "MN",
]

# §2 — Component prefix pools

VALVE_PREFIXES: list[str] = [
    "GV",
    "GLV",
    "BV",
    "BFV",
    "CK",
    "PV",
    "RV",
    "NV",
    "DV",
    "AV",
    "TWV",
    "CV",
    "SOL",
    "MOV",
    "PCV",
    "HV",
]

INSTRUMENT_PREFIXES: list[str] = [
    "PI",
    "TI",
    "FI",
    "LI",
    "FIC",
    "TIC",
    "LIC",
    "PIC",
    "FT",
    "TT",
    "LT",
    "PT",
]

EQUIPMENT_PREFIXES: list[str] = ["P", "C", "T", "E", "V"]

# §11 — Class ID ranges (for _type_from_class helper)

# 0–11  : valves
# 12–23 : instruments
# 24–31 : equipment
# 32–41 : fittings / structural

CLASS_ID_VALVE_MAX = 11
CLASS_ID_INSTRUMENT_MAX = 23
CLASS_ID_EQUIPMENT_MAX = 31
CLASS_ID_FITTING_MAX = 41

ALL_CLASS_IDS: list[int] = list(range(42))


# §15 — Title block constant pools (ISO 7200:2004)

# ISO 7200 mandatory field: "Legal owner" (organisation name)
ORGANIZATION_NAMES: list[str] = [
    "AUTOMATION LABS",
    "SYNTH ENGINEERING",
    "PROCESS SYSTEMS INC",
    "DIGITAL PROCESS CO",
    "CONTROL DYNAMICS LTD",
    "APEX PROCESS GROUP",
    "MERIDIAN ENGINEERING",
    "CRESTLINE INDUSTRIAL",
    "VECTOR PROCESS TECH",
    "PINNACLE SYSTEMS ENG",
]

# Project / contract names (shown in "document type / project" field)
CONTRACT_NAMES: list[str] = [
    "PROJ. DEF P&ID",
    "SYNTH PROC. P&ID",
    "PROCESS FLOW DWG",
    "PLANT LAYOUT P&ID",
    "UTILITY SYS. P&ID",
    "OFFSITE FACILITIES P&ID",
    "TANK FARM PIPING P&ID",
    "COMPRESSOR STATION P&ID",
    "HEAT RECOVERY UNIT P&ID",
    "WATER TREATMENT P&ID",
]

# Synthetic client / owner names (optional ISO 7200 "customer" field)
CLIENT_NAMES: list[str] = [
    "GLOBAL PETROCHEMICALS LTD",
    "NORTHFIELD REFINING CO",
    "STRATA ENERGY CORP",
    "BLUECREST UTILITIES",
    "IRONGATE PROCESSING INC",
    "VERITAS CHEMICAL GROUP",
    "SOLARIS FUELS PLC",
    "CONTINENTAL OIL & GAS",
]

# Synthetic plant / facility names
PLANT_NAMES: list[str] = [
    "SYNTH PLANT A",
    "UNIT 100 — CRUDE DISTILLATION",
    "UNIT 200 — HYDROTREATER",
    "UNIT 300 — REFORMER",
    "OFFSITE STORAGE AREA",
    "UTILITIES ISLAND",
    "TANK FARM COMPLEX",
    "COOLING WATER SYSTEM",
]

# Diagram title first line
DIAGRAM_TITLES: list[str] = [
    "SYNTHETIC PROCESS FLOW DIAGRAM",
    "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME",
    "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM",
    "SYNTHETIC UTILITY FLOW DIAGRAM",
    "SYNTHETIC MECHANICAL FLOW DIAGRAM",
    "SYNTHETIC HEAT & MATERIAL BALANCE DIAGRAM",
]

# Paired second-line titles (some companies use two title lines)
DIAGRAM_TITLE_PAIRS: list[tuple[str, str]] = [
    ("SYNTHETIC PROCESS FLOW DIAGRAM", "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME"),
    ("SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM", "SYNTHETIC UTILITY FLOW DIAGRAM"),
    ("SYNTHETIC PROCESS FLOW DIAGRAM", "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM"),
    ("SYNTHETIC MECHANICAL FLOW DIAGRAM", "SYNTHETIC HEAT & MATERIAL BALANCE DIAGRAM"),
]

# Revision description pool (ISO 7200 "revision" field)
REVISION_DESCRIPTIONS: list[str] = [
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
    "ISSUED FOR DESIGN",
    "ISSUED FOR INFORMATION",
    "ISSUED FOR PROCUREMENT",
    "REVISED PER HAZOP",
    "UPDATED PER SITE SURVEY",
]

# Synthetic draughtsman / engineer initials
PERSON_INITIALS: list[str] = [
    "J.R.",
    "S.K.",
    "A.M.",
    "T.W.",
    "R.P.",
    "D.L.",
    "C.H.",
    "M.F.",
    "B.N.",
    "E.C.",
]

# Disclaimer text — must appear on every generated drawing
DISCLAIMER_TEXT: str = (
    "PLEASE NOTE THIS DISCLAIMER CAREFULLY. THIS DOCUMENT IS COMPLETELY "
    "SYNTHETICALLY GENERATED AND IS NOT A REAL ENGINEERING DRAWING. IT IS "
    "INTENDED FOR RESEARCH AND TRAINING PURPOSES ONLY. ANY RESEMBLANCE "
    "TO ACTUAL PROJECTS OR FACILITIES IS ENTIRELY COINCIDENTAL. DO NOT "
    "USE THIS DRAWING FOR CONSTRUCTION, PROCUREMENT, OR OPERATION."
)


# §16 — Canvas geometry and ISO 5457 standards
# ISO 5457 defines paper sizes: A4=210×297mm, A3=420×297mm, A2=594×420mm
# Canvas is 4096×2896 px. Approximate mapping: ~19.46 px/mm at A4 (for reference only).
# PX_PER_MM allows resolution-independent scaling. Currently set for synthetic data training.
CANVAS_W: int = 4096
CANVAS_H: int = 2896
MARGIN:   int = 40
GRID:     int = 128   # px per grid cell

PX_PER_MM: float = 19.46  # Approximate pixel-to-mm ratio (4096px ≈ 210.5mm at A4 aspect)

# DPI (Dots Per Inch) range for variable diagram generation
# Simulates diagrams viewed at different zoom levels and display densities
DPI_MIN: float = 72.0       # Low DPI (zoomed out, low-res display)
DPI_MAX: float = 300.0      # High DPI (zoomed in, high-res display)
DPI_DEFAULT: float = 96.0   # Default DPI (standard screen resolution)

# DPI scaling: affects line widths, font sizes, and all rendered dimensions
# A diagram at 72 DPI will render thinner than the same at 300 DPI
DPI_SCALE: dict[str, float] = {
    "low": DPI_MIN / DPI_DEFAULT,      # 0.75x (75% size)
    "medium": 1.0,                      # 1.0x (100% size - default)
    "high": DPI_MAX / DPI_DEFAULT,      # 3.125x (312.5% size)
}

# ISO 3098 — Technical lettering: standardised line weights (mm) for drawings
# Outer title block border: 0.7mm; internal gridlines: 0.35mm
FONT_WEIGHTS_MM: dict[str, float] = {
    "outer_border":   0.7,   # Title block outer rectangle (primary feature line)
    "inner_grid":     0.35,  # Internal title block gridlines (secondary)
    "process_pipe":   0.5,   # Process line (main flow path)
    "utility_pipe":   0.35,  # Utility line (secondary flow)
    "signal_line":    0.35,  # Instrument signal line
}

# Convert ISO 3098 mm weights to pixels for rendering
FONT_WEIGHTS_PX: dict[str, int] = {
    k: max(1, round(v * PX_PER_MM)) for k, v in FONT_WEIGHTS_MM.items()
}

# ISA 5.1 — Symbolic Integrity: instrument bubbles (circles) dimensioning
# Primary instruments (PI, TI, FI, etc.): 12mm diameter per ISA 5.1:2009
INSTRUMENT_BUBBLE_MM: float = 12.0
INSTRUMENT_BUBBLE_PX: int = round(INSTRUMENT_BUBBLE_MM * PX_PER_MM)

# §16 — Rendering
BG_COLOR:   str = "white"
FG_COLOR:   str = "black"
FONT_SIZE:  int = 22   # px — component tags
SMALL_FONT: int = 16   # px — pipe tags and notes
SYMBOL_BOX: int = 64   # px half-side for symbol bounding boxes

# §12 — Line widths per edge type (now derived from ISO 3098 standards)
LINE_WIDTH: dict[str, int] = {
    "process":          max(1, round(0.15 * PX_PER_MM)),      # Process pipe: 0.15mm (3px)
    "utility":          max(1, round(0.1 * PX_PER_MM)),       # Utility pipe: 0.1mm (2px)
    "signal_electric":  max(1, round(0.08 * PX_PER_MM)),      # Signal: 0.08mm (1-2px)
    "signal_pneumatic": max(1, round(0.08 * PX_PER_MM)),      # Signal: 0.08mm (1-2px)
    "signal_hydraulic": max(1, round(0.08 * PX_PER_MM)),      # Signal: 0.08mm (1-2px)
    "heat_trace":       max(1, round(0.15 * PX_PER_MM)),      # Heat trace: 0.15mm (3px)
    "sample":           max(1, round(0.1 * PX_PER_MM)),       # Sample: 0.1mm (2px)
    "drain_vent":       max(1, round(0.08 * PX_PER_MM)),      # Drain/vent: 0.08mm (1-2px)
}

# §12 — Dash patterns (on, off …) per edge type; None means solid
DASH_PATTERN: dict[str, tuple | None] = {
    "process":          None,
    "utility":          None,
    "signal_electric":  (8, 4),
    "signal_pneumatic": (8, 4),
    "signal_hydraulic": (8, 4, 2, 4),
    "heat_trace":       None,
    "sample":           (16, 6),
    "drain_vent":       None,
}

# §15 — Title block geometry
TITLE_BLOCK_H:     int = 180   # bottom block height in pixels
TITLE_BLOCK_W:     int = 620   # right-side block width in pixels
TITLE_BLOCK_REV_H: int = 28    # height per revision row
TITLE_BLOCK_REVS:  int = 3     # max revision rows rendered
TITLE_BLOCK_DEAD_ZONE_MM: float = 10.0  # Buffer above title block for future revisions


@dataclass(frozen=True)
class SafeZone:
    """Bounding box for the title block and its dead zone (collision avoidance).

    Coordinates are in normalised space (0.0 to 1.0). Nodes must not be positioned
    within this zone to avoid overlapping the title block or revision table.

    Attributes:
        x_min, y_min, x_max, y_max: Normalised bounding box.
        dead_zone_y_min: Lower boundary of the dead zone above the title block
                         (reserved for future revisions).
    """
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    dead_zone_y_min: float = 0.85  # Default: 85% of canvas height

    def contains(self, norm_x: float, norm_y: float) -> bool:
        """Check if a point (normalised coords) is inside the safe zone."""
        return self.x_min <= norm_x <= self.x_max and self.y_min <= norm_y <= self.y_max

    def contains_in_dead_zone(self, norm_x: float, norm_y: float) -> bool:
        """Check if a point is in the dead zone (above the title block)."""
        return (
            self.x_min <= norm_x <= self.x_max
            and self.dead_zone_y_min <= norm_y <= self.y_min
        )


# Default safe zone: bottom-right title block (ISO 7200 anchor)
# Title block spans from (MARGIN+TITLE_BLOCK_W, CANVAS_H-TITLE_BLOCK_H) in pixels.
# Normalised coords: x ≈ [0.85, 1.0], y ≈ [0.938, 1.0] (typical).
DEFAULT_SAFE_ZONE = SafeZone(
    x_min=0.80,      # ~80% of canvas width
    y_min=0.93,      # ~93% of canvas height
    x_max=1.00,      # Right edge
    y_max=1.00,      # Bottom edge
    dead_zone_y_min=0.85,  # Dead zone starts at 85%, allows 8% buffer
)


def _type_from_class(cid: int) -> str:
    """Return the node type string for a given class_id (§11)."""
    if cid <= CLASS_ID_VALVE_MAX:
        return "valve"
    if cid <= CLASS_ID_INSTRUMENT_MAX:
        return "instrument"
    if cid <= CLASS_ID_EQUIPMENT_MAX:
        return "equipment"
    return "fitting"
