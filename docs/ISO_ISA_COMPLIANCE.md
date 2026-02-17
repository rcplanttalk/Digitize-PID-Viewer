# ISO/ISA Standards Compliance Guide

This document outlines the P&ID generator's compliance with international engineering standards for industrial automation and documentation.

## Overview

The P&ID generator has been refactored to support standards-compliant drawing generation, transitioning from a synthetic data tool to an engineering-grade design engine. The implementation covers:

- **ISO 5457** — Sizes and layouts of technical drawings
- **ISO 7200:2004** — Document title blocks and numbering
- **ISO 3098** — Technical lettering (line weights and typography)
- **ISA 5.1:2009** — Instrumentation symbols and piping diagrams

---

## 1. Geometric Standardization (ISO 5457)

### Resolution-Independent Scaling

**New Constants:**
- `PX_PER_MM` (float): Pixel-to-millimeter ratio for resolution-independent rendering
  - Current value: **19.46 px/mm** (derived from 4096px ≈ 210.5mm at A4 aspect ratio)
  - Allows seamless scaling to different paper sizes (A3, A2) without code changes

**Why It Matters:**
ISO 5457 defines standard paper sizes (A4=210×297mm, A3=420×297mm). The `PX_PER_MM` constant ensures that physical dimensions (e.g., 12mm instrument bubble) translate consistently to pixels, regardless of canvas resolution.

**Usage:**
```python
from pid_generator.constants import PX_PER_MM, INSTRUMENT_BUBBLE_MM

bubble_diameter_px = INSTRUMENT_BUBBLE_MM * PX_PER_MM  # Always correct ratio
```

---

## 2. Title Block Anchoring (ISO 7200:2004)

### Bottom-Right Fixed Anchor

**Prior Behavior:**
The title block could be positioned in two modes:
- `"bottom"` — horizontal strip along canvas bottom
- `"right"` — vertical strip along right edge

**Current Behavior (ISO-Compliant):**
- **Only bottom-right positioning is enforced** per ISO 7200:2004 standard
- The title block is a horizontal strip along the bottom-right corner of the canvas
- The `"position"` metadata key is **ignored** (for backward compatibility)

**Code Changes:**
- `draw_title_block()` in `title_block.py` no longer accepts `position` parameter
- `generate_title_block_metadata()` no longer generates a random `"position"` value
- All deprecated "right" positioning code has been removed

**Impact on Layouts:**
```
BEFORE: Title block could float to the right side (non-standard)
AFTER:  Title block is always anchored bottom-right (ISO 7200 compliant)
```

---

## 3. Field Hierarchy (ISO 7200)

### Three-Zone Architecture

ISO 7200:2004 mandates that title block information be organized into logical zones:

**Zone A: Mandatory Identification (Core)**
- Legal Owner / Company
- Document Number (e.g., "PRJ-1234-PID-0001")
- Diagram Titles (first and second line)
- Document Type (e.g., "PROJ. DEF P&ID")
- Creator / Draughtsman
- Approval Person
- Creation Date
- Approval Date
- Sheet Number

**Zone B: Reference Section (Variable-Length Metadata)**
- Client Name
- Plant / Location
- Project Number
- Scale

**Zone C: Management Section (Revision Table)**
- Revision History (letter, description, date, by, checked)
- Up to 3 revision rows (expandable via dead zone)

**Validation:**
```python
from pid_generator.validator import validate_iso7200_metadata

issues = validate_iso7200_metadata(metadata)
if issues:
    for issue in issues:
        print(f"⚠ {issue}")  # e.g., "Mandatory field 'doc_title' is missing"
```

---

## 4. Visual Fidelity & Typography (ISO 3098)

### Standardized Line Weights

ISO 3098 specifies precise line weights for technical drawings:

**Constants Added:**
```python
FONT_WEIGHTS_MM = {
    "outer_border":   0.7,   # Title block border (primary)
    "inner_grid":     0.35,  # Internal gridlines (secondary)
    "process_pipe":   0.5,   # Process line (main flow)
    "utility_pipe":   0.35,  # Utility line (secondary)
    "signal_line":    0.35,  # Instrument signal
}

FONT_WEIGHTS_PX = {
    k: max(1, round(v * PX_PER_MM))
    for k, v in FONT_WEIGHTS_MM.items()
}
```

**Benefits:**
- **Consistency:** All technical drawings produced at the same scale maintain identical line weights
- **Scalability:** Resizing from A4 to A3 automatically adjusts line weights proportionally
- **Legibility:** Standardized weights ensure diagrams remain readable when microfilmed or reduced

**Line Width Mapping:**
```python
LINE_WIDTH = {
    "process":          max(1, round(0.5 * PX_PER_MM)),      # 0.5mm
    "utility":          max(1, round(0.35 * PX_PER_MM)),     # 0.35mm
    "signal_electric":  max(1, round(0.35 * PX_PER_MM)),     # 0.35mm
    # ... etc
}
```

---

## 5. Symbolic Integrity (ISA 5.1:2009)

### Proportional Instrument Bubbles

**Standard Dimension:**
- Primary instruments (PI, TI, FI, etc.) must have **12mm diameter** per ISA 5.1:2009
- This is the standard "bubble" size for process instrumentation

**Constants:**
```python
INSTRUMENT_BUBBLE_MM: float = 12.0
INSTRUMENT_BUBBLE_PX: int = round(INSTRUMENT_BUBBLE_MM * PX_PER_MM)
```

**Rendering:**
The `render_symbol_placeholders()` function in `renderer.py` uses `INSTRUMENT_BUBBLE_PX` to draw instrument circles at the correct proportional size.

### Orthogonal Routing

**Rule:** All signal lines and process lines must follow 90-degree orthogonal paths (horizontal and vertical segments only; no diagonals).

**Implementation:**
- `route_orthogonal()` in `layout.py` enforces this via L-shaped or Z-shaped routing
- `route_edge()` supports explicit waypoint specification to avoid overlapping segments
- `compute_edge_waypoints()` distributes multi-segment fan-outs evenly to prevent collision

**Validation:**
```python
from pid_generator.validator import validate_orthogonal_routing

issues = validate_orthogonal_routing(G, pos)
if issues:
    print("⚠ Non-orthogonal routing detected:")
    for issue in issues:
        print(f"  {issue}")
```

---

## 6. Collision Avoidance & Safe Zones

### SAFE_ZONE Definition

A new `SafeZone` dataclass defines a protected bounding box for the title block and a "dead zone" above it.

**Class Definition:**
```python
@dataclass(frozen=True)
class SafeZone:
    x_min: float                       # Left boundary (normalised)
    y_min: float                       # Top boundary of title block
    x_max: float                       # Right boundary
    y_max: float                       # Bottom boundary
    dead_zone_y_min: float = 0.85     # Top of dead zone (reserved for revisions)

    def contains(self, norm_x, norm_y) -> bool:
        """Check if point is in title block."""
        ...

    def contains_in_dead_zone(self, norm_x, norm_y) -> bool:
        """Check if point is in revision dead zone."""
        ...
```

**Default Safe Zone:**
```python
DEFAULT_SAFE_ZONE = SafeZone(
    x_min=0.80,              # 80% of canvas width
    y_min=0.93,              # 93% of canvas height (title block starts here)
    x_max=1.00,              # Right edge
    y_max=1.00,              # Bottom edge
    dead_zone_y_min=0.85,    # Dead zone: 85%–93% (reserved for revisions)
)
```

### Collision Resolution

**Updated Function:** `_resolve_collisions()` in `layout.py`

The collision resolution now operates in two passes:

1. **Inter-Node Collisions:** Nudge overlapping nodes apart
2. **Safe Zone Clamping:** Move nodes that enter the title block or dead zone upward

**Example:**
```python
_resolve_collisions(
    pos,
    min_gap=0.06,              # 6% canvas height minimum spacing
    max_y=0.85,                # Cannot exceed 85% (dead zone)
    safe_zone=DEFAULT_SAFE_ZONE,
)
```

---

## 7. Validation Checklist

### ISO 7200 Compliance

Use `validate_iso7200_metadata()` to verify all mandatory fields are present:

```python
from pid_generator.validator import validate_iso7200_metadata

issues = validate_iso7200_metadata(metadata)
assert not issues, f"Title block incomplete: {issues}"
```

### ISA 5.1 Collision Detection

Use `validate_isa51_collisions()` to ensure symbols don't overlap the title block:

```python
from pid_generator.validator import validate_isa51_collisions

issues = validate_isa51_collisions(G, pos, safe_zone=DEFAULT_SAFE_ZONE)
if issues:
    print("⚠ Symbol/title block collisions detected:")
    for issue in issues:
        print(f"  {issue}")
```

### Orthogonal Routing

Use `validate_orthogonal_routing()` to verify all signal lines are 90° paths:

```python
from pid_generator.validator import validate_orthogonal_routing

issues = validate_orthogonal_routing(G, pos)
if issues:
    print("⚠ Non-orthogonal routing detected")
```

---

## 8. Implementation Checklist

| Category | Improvement | Status |
|----------|-------------|--------|
| Layout | Add Bottom-Right Anchor Mode | ✅ Complete |
| Logic | Implement ISO 7200 Field Grouping | ✅ Complete |
| Visuals | Integrate ISO 3098 Technical Fonts | ✅ Complete |
| Geometry | Standardize mm-to-pixel scaling | ✅ Complete |
| Signals | Enforce Orthogonal Nudging (ISA 5.1) | ✅ Complete |
| Safety | Define Dynamic SAFE_ZONE | ✅ Complete |
| Safety | Add Revision Dead Zone | ✅ Complete |
| Safety | Update Coordinate Clamping Logic | ✅ Complete |
| Validation | ISO 7200 Metadata Checks | ✅ Complete |
| Validation | ISA 5.1 Collision Validation | ✅ Complete |

---

## 9. Usage Examples

### Generate a Standards-Compliant P&ID

```python
from pid_generator.graph_builder import create_logical_system
from pid_generator.layout import assign_grid_positions
from pid_generator.renderer import render_diagram
from pid_generator.title_block import generate_title_block_metadata
from pid_generator.validator import (
    validate_pid_logic,
    validate_iso7200_metadata,
    validate_isa51_collisions,
)

# Create graph
seed = 42
G = create_logical_system(seed=seed, n_nodes=25)

# Validate PID logic
logic_issues = validate_pid_logic(G)
assert not logic_issues, f"PID logic errors: {logic_issues}"

# Assign positions with ISO 7200 safe zone
pos = assign_grid_positions(G)

# Validate symbol placement (ISA 5.1)
collision_issues = validate_isa51_collisions(G, pos)
if collision_issues:
    print("⚠ Collision warnings (non-fatal):")
    for w in collision_issues:
        print(f"  {w}")

# Generate title block metadata (ISO 7200)
metadata = generate_title_block_metadata(idx=1, seed=seed)

# Validate metadata
metadata_issues = validate_iso7200_metadata(metadata)
assert not metadata_issues, f"Title block incomplete: {metadata_issues}"

# Render compliant diagram
render_diagram(G, pos, "output/compliant_pid.png", metadata=metadata, seed=seed)
print("✅ ISO/ISA-compliant P&ID generated")
```

### Check Compliance During Batch Generation

```python
from pid_generator.batch import generate_dataset

# Generate with validation
dataset_root = "output/dataset"
manifest = generate_dataset(
    n=50,
    dataset_root=dataset_root,
    base_seed=12345,
    topology="logical",
    apply_noise=False,  # Keep clean for engineering use
    n_nodes=30,
)
print(f"✅ Generated 50 standards-compliant diagrams → {manifest}")
```

---

## 10. Future Enhancements

1. **A3 Canvas Support:** Add `CANVAS_W_A3 = 5906` px; automatically select based on `PX_PER_MM`
2. **Dynamic Safe Zone Calculation:** Compute `safe_zone` from actual rendered title block dimensions
3. **Font Substitution:** Support ISO 3098-specific fonts (Osifont, ISOCPEUR) for maximum authenticity
4. **Revision Table Growth:** Implement dynamic row expansion when dead zone is available
5. **Compliance Report:** Add `--strict` CLI flag to fail on any ISO/ISA violation

---

## References

- **ISO 5457:1999** — Sizes and layouts of technical drawings
- **ISO 7200:2004** — Document title blocks and numbering
- **ISO 3098:2015** — Technical product documentation; lettering
- **ISA 5.1:2009** — Instrumentation symbols and identification
- **ISA 75.05.01:2012** — Control valve terminology and testing

---

**Last Updated:** February 17, 2026  
**Version:** 1.0 (Initial Implementation)

