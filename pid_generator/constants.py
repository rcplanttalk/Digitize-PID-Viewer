"""Constant pools for the P&ID generator (§2, §11, §13)."""

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


def _type_from_class(cid: int) -> str:
    """Return the node type string for a given class_id (§11)."""
    if cid <= CLASS_ID_VALVE_MAX:
        return "valve"
    if cid <= CLASS_ID_INSTRUMENT_MAX:
        return "instrument"
    if cid <= CLASS_ID_EQUIPMENT_MAX:
        return "equipment"
    return "fitting"
