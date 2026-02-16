"""Constant pools for the P&ID generator (§2, §11, §13, §15)."""

# ---------------------------------------------------------------------------
# §2 / §13 — Pipe sizes and spec codes
# ---------------------------------------------------------------------------

PIPE_SIZES: list[int] = [2, 4, 6, 8, 10, 12, 14, 16]

PIPE_SPEC_CODES: list[str] = [
    "JD", "CK", "AB", "EF", "GH", "PN", "WR", "ST", "HX", "MN"
]

# ---------------------------------------------------------------------------
# §2 — Component prefix pools
# ---------------------------------------------------------------------------

VALVE_PREFIXES: list[str] = [
    "GV", "GLV", "BV", "BFV", "CK", "PV", "RV", "NV",
    "DV", "AV", "TWV", "CV", "SOL", "MOV", "PCV", "HV",
]

INSTRUMENT_PREFIXES: list[str] = [
    "PI", "TI", "FI", "LI", "FIC", "TIC", "LIC", "PIC",
    "FT", "TT", "LT", "PT",
]

EQUIPMENT_PREFIXES: list[str] = ["P", "C", "T", "E", "V"]

# ---------------------------------------------------------------------------
# §11 — Class ID ranges (for _type_from_class helper)
# ---------------------------------------------------------------------------

# 0–11  : valves
# 12–23 : instruments
# 24–31 : equipment
# 32–41 : fittings / structural

CLASS_ID_VALVE_MAX      = 11
CLASS_ID_INSTRUMENT_MAX = 23
CLASS_ID_EQUIPMENT_MAX  = 31
CLASS_ID_FITTING_MAX    = 41

ALL_CLASS_IDS: list[int] = list(range(42))


# ---------------------------------------------------------------------------
# §15 — Title block constant pools (ISO 7200:2004)
# ---------------------------------------------------------------------------

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
    ("SYNTHETIC PROCESS FLOW DIAGRAM",
     "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME"),
    ("SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM",
     "SYNTHETIC UTILITY FLOW DIAGRAM"),
    ("SYNTHETIC PROCESS FLOW DIAGRAM",
     "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM"),
    ("SYNTHETIC MECHANICAL FLOW DIAGRAM",
     "SYNTHETIC HEAT & MATERIAL BALANCE DIAGRAM"),
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
    "J.R.", "S.K.", "A.M.", "T.W.", "R.P.",
    "D.L.", "C.H.", "M.F.", "B.N.", "E.C.",
]

# Disclaimer text — must appear on every generated drawing
DISCLAIMER_TEXT: str = (
    "PLEASE NOTE THIS DISCLAIMER CAREFULLY. THIS DOCUMENT IS COMPLETELY "
    "SYNTHETICALLY GENERATED AND IS NOT A REAL ENGINEERING DRAWING. IT IS "
    "INTENDED FOR RESEARCH AND TRAINING PURPOSES ONLY. ANY RESEMBLANCE "
    "TO ACTUAL PROJECTS OR FACILITIES IS ENTIRELY COINCIDENTAL. DO NOT "
    "USE THIS DRAWING FOR CONSTRUCTION, PROCUREMENT, OR OPERATION."
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
