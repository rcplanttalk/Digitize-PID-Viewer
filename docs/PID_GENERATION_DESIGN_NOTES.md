# P&ID Synthetic Data Generator — Design Notes

## 1. Visual Realism Techniques

### 1.1 Pipe Crossings (Jump / Gap)
When two pipes cross but do **not** connect, professional drawings use a "jump" to indicate they are at different depths.

**Implementation:** At the intersection of a horizontal and vertical pipe that is not a junction, draw a small white circle (background color) over the vertical line to create a visual gap.

### 1.2 Rotating Symbols for Vertical Pipes
Templates are drawn for horizontal orientation by default. When placing a symbol on a vertical pipe, rotate it 90° and swap its dimensions:

```python
tpath, tw, th = get_template_size(cid)
timg = Image.open(tpath)
if is_vertical_pipe:
    timg = timg.rotate(90, expand=True)
    tw, th = th, tw  # Swap dimensions after rotation
```

### 1.3 Line-Break Rule (Symbol Masking)
In real P&IDs, a valve is not placed on top of a line — the line is **broken** so the symbol sits in the gap.

**Implementation:** Before placing a symbol, fill a small rectangle (slightly smaller than the symbol) with the background color to clear the pipe underneath. This prevents pipe lines from showing through valve or pump templates.

### 1.4 Visual Noise for Realism
To help models generalise, avoid perfectly clean diagrams:

| Technique | Description |
|---|---|
| Varying line weights | Main process lines thick; signal/utility lines thin |
| Revision clouds | Scalloped circles around randomly selected areas |
| Scanning distortions | Slight rotation (~0.5°) or salt-and-pepper noise to simulate scanned blueprints |

---

## 2. Text Tags & Labels

Real P&IDs carry text tags on every component. Generated from the constant pools defined in the project.

### Tag Formats

| Component | Format | Example | Placement |
|---|---|---|---|
| Pipes | `[Size]-[Spec]-[Seq]` | `6-JD-1001` | Parallel to line, centred |
| Valves | `[Prefix]-[Seq]` | `GV-042` | Directly above/beside the valve |
| Instruments | `[Prefix]-[Seq]` | `PT-101` | Inside or below the instrument bubble |
| Equipment | `[Prefix]-[Seq]` | `P-101` | Below or beside the symbol |

### Pipe Sizes (inches)

```python
PIPE_SIZES = [2, 4, 6, 8, 10, 12, 14, 16]
```

All pipe `size` attributes on graph edges and nodes must be drawn from this list. A valve placed on a pipe must share the same size value.

### Pipe Spec Codes

```python
PIPE_SPEC_CODES = ["JD", "CK", "AB", "EF", "GH", "PN", "WR", "ST", "HX", "MN"]
```

Randomly assigned per pipe at graph-build time. Consistent along a single line (all edges in one path share the same spec).

### Valve Prefixes

```python
VALVE_PREFIXES = [
    "GV", "GLV", "BV", "BFV", "CK", "PV", "RV", "NV",
    "DV", "AV", "TWV", "CV", "SOL", "MOV", "PCV", "HV",
]
```

| Prefix | Full Name |
|---|---|
| `GV` | Gate Valve |
| `GLV` | Globe Valve |
| `BV` | Ball Valve |
| `BFV` | Butterfly Valve |
| `CK` | Check Valve |
| `PV` | Control Valve (process) |
| `RV` | Relief Valve |
| `NV` | Needle Valve |
| `DV` | Diaphragm Valve |
| `AV` | Angle Valve |
| `TWV` | Three-Way Valve |
| `CV` | Control Valve (generic) |
| `SOL` | Solenoid Valve |
| `MOV` | Motor-Operated Valve |
| `PCV` | Pressure Control Valve |
| `HV` | Hand Valve |

### Instrument Prefixes

```python
INSTRUMENT_PREFIXES = [
    "PI", "TI", "FI", "LI", "FIC", "TIC", "LIC", "PIC",
    "FT", "TT", "LT", "PT",
]
```

| Prefix | Measured Variable | Type |
|---|---|---|
| `PI` | Pressure | Indicator |
| `TI` | Temperature | Indicator |
| `FI` | Flow | Indicator |
| `LI` | Level | Indicator |
| `FIC` | Flow | Controller |
| `TIC` | Temperature | Controller |
| `LIC` | Level | Controller |
| `PIC` | Pressure | Controller |
| `FT` | Flow | Transmitter |
| `TT` | Temperature | Transmitter |
| `LT` | Level | Transmitter |
| `PT` | Pressure | Transmitter |

### Equipment Prefixes

```python
EQUIPMENT_PREFIXES = ["P", "C", "T", "E", "V"]
```

| Prefix | Equipment Type |
|---|---|
| `P` | Pump |
| `C` | Compressor |
| `T` | Tank / Vessel |
| `E` | Heat Exchanger |
| `V` | Vessel (generic) |

### Instrument Bubble Styles (ANSI/ISA-5.1)

| Line through circle | Meaning |
|---|---|
| Solid single line | Field-mounted (at the pipe) |
| Double line | Control room mounted |
| None | Behind a panel |

---

## 3. Functional Logic (Beyond Visual Randomness)

Placing random symbols on random pipes produces diagrams that *look* like P&IDs but fail engineering logic. The goal is to act like a **Simplified CAD Engine**.

### Levels of Generation Quality

| Level | What it generates | Result |
|---|---|---|
| Basic | Random symbols + random pipes | Looks like a drawing; fails engineering logic |
| Intermediate | Orientation + size matching | Looks correct to the eye; labels make sense |
| Advanced | Process loops + flow direction | Functional; could theoretically describe a real system |

### 3.1 Pipe Spec / Size Consistency
- Assign a fixed **size** (e.g., `8"`) and **spec** (e.g., `AB`) when generating a pipe.
- When placing a valve, only pick symbols that match that spec.
- The generated text tag must reflect the pipe size (no 6" valve label on a 2" line).

### 3.2 Directional / Flow Logic
- Establish a global flow direction (usually left-to-right).
- **Source → Sink**: networks start at a source (pump, tank) and end at a destination (vessel, off-page connector).
- **Check valves** must be oriented so their arrow points away from the source toward the sink.

### 3.3 Instrumentation Control Loop Rule
Instruments are part of **Control Loops**, not floating bubbles.

A complete loop requires three elements:

| Role | Example |
|---|---|
| Sensing | Transmitter — `PT-101` |
| Indicating | Controller/Indicator — `PIC-101` |
| Acting | Control Valve — `PV-101` |

- All three components share the same **loop number**.
- They are connected with a **dashed signal line** (electrical) or solid cross-hatched line (pneumatic).
- Never connect a process pipe directly to a control indicator.

---

## 4. Physical Connectivity Rules

| Rule | Description |
|---|---|
| Line Break | Pipes must never pass through the center of a symbol |
| No Dangling Components | Every valve/instrument must attach to a pipe |
| Standard Orientation | Horizontal pipe → valve upright; vertical pipe → valve rotated 90°/270° |
| Reducer Logic | Pipe size change requires a Reducer symbol (Class 28) at the transition point |
| Elbows vs. Tees | Direction change on one line = elbow (no dot); connection of two lines = tee (dot) |

---

## 5. Process Logic Rules

| Rule | Description |
|---|---|
| Isolation valves | Major equipment (pumps/tanks) must have manual isolation valves on both inlet and outlet |
| Check valve placement | Must be on pump **discharge** lines only, to prevent backflow |
| Drain/Vent | Every low point → drain valve; every high point → vent valve |
| Gravity constraints | Tank outlets at bottom; inlets/vents at top |
| Bypass loops | Control valves should have a parallel manual bypass (50% probability in generator) |

---

## 6. NetworkX-Based Architecture

### Why Graph Theory Instead of Coordinates

Instead of placing symbols at random `(x, y)` positions, build a **mathematical graph** first, then render it.

- **Nodes**: Tanks, Pumps, Valves — with attributes `type`, `class_id`, `size`
- **Edges**: Pipes — with attributes `spec`, `size`
- **DiGraph**: Directed graph so every pipe has a known `source → target` (flow direction)

This gives the renderer enough information to handle rotation, masking, and tagging automatically.

### 6.1 Logical Graph Construction

```python
import networkx as nx

def create_logical_system():
    G = nx.DiGraph()

    G.add_node("PUMP_01",  type="equipment", class_id=25, size=8)
    G.add_node("VALVE_01", type="valve",     class_id=5,  size=8)
    G.add_node("TANK_01",  type="equipment", class_id=23, size=12)

    G.add_edge("PUMP_01",  "VALVE_01", size=8, spec="A1A")
    G.add_edge("VALVE_01", "TANK_01",  size=8, spec="A1A")

    return G
```

### 6.2 Orthogonal Grid Layout

Standard graph layouts produce diagonal lines. P&IDs require **orthogonal routing** (horizontal and vertical segments only).

```python
def assign_grid_positions(G):
    pos = {
        "PUMP_01":  (0.2, 0.5),
        "VALVE_01": (0.4, 0.5),
        "TANK_01":  (0.7, 0.5),
    }
    return pos
```

If two nodes are not aligned on the same axis, route the edge as an "L" or "Z" shape.

### 6.3 Smart Renderer

```python
def render_from_graph(G, pos, draw_obj):
    # Draw pipes first (edges)
    for u, v, data in G.edges(data=True):
        p1, p2 = pos[u], pos[v]
        width = data['size'] // 2
        draw_line_between(p1, p2, width)

    # Draw symbols (nodes)
    for node, data in G.nodes(data=True):
        coords = pos[node]
        cid = data['class_id']

        neighbors = list(G.neighbors(node)) + list(G.predecessors(node))
        rotation = calculate_rotation(pos[node], pos[neighbors[0]])

        apply_symbol_mask(coords, cid)   # clear pipe under symbol
        place_template(coords, cid, rotation)
```

---

## 7. Structural Rules (NetworkX "Rules Engine")

### Node Degree Constraints

| Component | In-degree | Out-degree |
|---|---|---|
| Valve / Instrument | 1 | 1 |
| Tee / Junction | up to 3 | up to 3 |
| Pump | exactly 1 (suction) | exactly 1 (discharge) |

### Semantic / Metadata Rules

| Rule | Description |
|---|---|
| Size-Match | Node (valve) `size` must equal the `size` of its connected edges (pipes) |
| Reducer Trigger | Two edges with different `size` values → automatically insert a Reducer node (Class 28) |
| Tag Inheritance | Components inherit the sequence number from the pipe they sit on |

### Example Validator

```python
def validate_pid_logic(G):
    for node, data in G.nodes(data=True):
        # Check valves must have exactly one input
        if data['class_id'] == 2 and G.in_degree(node) != 1:
            raise ValueError(f"Check Valve {node} must have exactly one input.")

        # Control valves must have a signal line
        if data.get('type') == 'control_valve':
            has_signal = any(
                G[u][v].get('type') == 'signal'
                for u, v in G.edges(node)
            )
            if not has_signal:
                print(f"Warning: Control Valve {node} is missing a signal line.")
```

---

## 8. Generation Method Comparison

| Method | Visual Accuracy | Engineering Logic | Difficulty |
|---|---|---|---|
| Random paste | High | Low | ⭐ |
| NetworkX logic | Very high | High | ⭐⭐⭐ |
| Z3 / SMT Solver | Perfect | Perfect | ⭐⭐⭐⭐⭐ |

**Recommended path:** Start with NetworkX logic. It provides enough functional correctness to train a context-aware YOLO model without the complexity of formal constraint solvers.

---

## 9. Why Functional Diagrams Matter for YOLO Training

Training on purely random diagrams teaches the model to **detect symbols in isolation**. Training on NetworkX-logic diagrams teaches the model **context**:

- Gate valves appear near pumps.
- Instruments are children of main process lines.
- Reducers always sit between a thick line and a thin line.

This contextual understanding makes the model robust when shown real-world engineering drawings.

---

## 10. Recommended Implementation Order

1. **Line-Break / Symbol Mask** — biggest visual quality gain for least effort.
2. **Pipe size + spec consistency** — prevents nonsensical valve sizing.
3. **NetworkX DiGraph backbone** — enables all subsequent structural rules.
4. **Orthogonal routing** — makes diagrams look like actual P&IDs.
5. **Control loop pairing** — adds instrument logic (transmitter ↔ control valve).
6. **Visual noise** — scanning distortions, line weights, revision clouds.

---

## 11. Symbol Class ID Reference

All class IDs used in node attributes (`class_id`) map to the following YOLO detection classes. This table is the single source of truth for the generator, validator, and renderer.

### 11.1 Valves

| class_id | Symbol Name | Abbreviation | Notes |
|---|---|---|---|
| 0 | Ball Valve | BV | Quarter-turn; used for isolation |
| 1 | Butterfly Valve | BFV | Large-bore isolation; low pressure drop |
| 2 | Check Valve | CV | Direction-sensitive; discharge lines only |
| 3 | Control Valve (generic) | XV | Requires signal line to instrument |
| 4 | Gate Valve | GV | Fully open/closed; main isolation |
| 5 | Globe Valve | GLV | Throttling; used in bypasses |
| 6 | Needle Valve | NV | Fine flow control; small-bore only |
| 7 | Plug Valve | PV | Quarter-turn; similar to ball valve |
| 8 | Relief / Safety Valve | PSV | Outlet must be to atmosphere or flare |
| 9 | Pressure Reducing Valve | PRV | Downstream pressure control |
| 10 | Diaphragm Valve | DV | Slurry / hygienic service |
| 11 | Angle Valve | AV | 90° body; used at tank drains |

### 11.2 Instruments

| class_id | Symbol Name | Tag Prefix | Measured Variable |
|---|---|---|---|
| 12 | Pressure Transmitter | PT | Pressure |
| 13 | Pressure Indicator | PI | Pressure |
| 14 | Pressure Controller | PIC | Pressure |
| 15 | Temperature Transmitter | TT | Temperature |
| 16 | Temperature Indicator | TI | Temperature |
| 17 | Flow Transmitter | FT | Flow rate |
| 18 | Flow Indicator | FI | Flow rate |
| 19 | Flow Controller | FIC | Flow rate |
| 20 | Level Transmitter | LT | Liquid level |
| 21 | Level Indicator | LI | Liquid level |
| 22 | Level Controller | LIC | Liquid level |
| 23 | Analyser Transmitter | AT | Composition / quality |

### 11.3 Equipment

| class_id | Symbol Name | Type | Degree constraints |
|---|---|---|---|
| 24 | Centrifugal Pump | equipment | in=1 (suction), out=1 (discharge) |
| 25 | Reciprocating Pump | equipment | in=1, out=1 |
| 26 | Compressor | equipment | in=1, out=1 |
| 27 | Heat Exchanger | equipment | in=2 (shell+tube), out=2 |
| 28 | Vertical Vessel / Column | equipment | in=1+ (top), out=1+ (bottom) |
| 29 | Horizontal Vessel | equipment | in=1+ (top/side), out=1+ (bottom) |
| 30 | Storage Tank | equipment | in=1+ (top), out=1 (bottom) |
| 31 | Agitator / Mixer | equipment | in=2+, out=1 |

### 11.4 Pipe Fittings & Specials

| class_id | Symbol Name | Notes |
|---|---|---|
| 32 | Reducer (concentric) | Triggers when adjacent edges have different `size` values |
| 33 | Reducer (eccentric) | Used on pump suction to avoid air pockets |
| 34 | Strainer / Y-Filter | Placed upstream of pumps and control valves |
| 35 | Spectacle Blind | Isolates equipment for maintenance |
| 36 | Expansion Joint | Absorbs thermal movement on long runs |
| 37 | Flame Arrestor | Required upstream of flare headers |

### 11.5 Structural / Drawing Elements

| class_id | Symbol Name | Notes |
|---|---|---|
| 38 | Off-Page Connector | Links to another sheet; has a sheet reference tag |
| 39 | Instrument Bubble (generic) | Circle only; tag written inside |
| 40 | Junction / Tee dot | Filled circle at pipe branch point |
| 41 | Pipe crossing (no connection) | Drawn as a "jump" gap on the vertical pipe |

---

## 12. Line Type Visual Reference

Every line on a P&ID has a specific visual style. The renderer must select style based on edge `type` attribute.

| Edge `type` | Visual Style | PIL Parameters | Meaning |
|---|---|---|---|
| `process` | Solid, thick | `width=3`, solid | Main process fluid |
| `utility` | Solid, thin | `width=1`, solid | Steam, water, air, nitrogen |
| `signal_electric` | Dashed | `width=1`, dash `(8, 4)` | Electrical control signal |
| `signal_pneumatic` | Dashed + crosshatch | `width=1`, dash `(8, 4)` + tick marks | Pneumatic (instrument air) signal |
| `signal_hydraulic` | Dash-dot | `width=1`, dash `(8, 4, 2, 4)` | Hydraulic control signal |
| `heat_trace` | Double solid | Two parallel lines, `width=1` | Electrical or steam heat tracing |
| `sample` | Long dash | `width=1`, dash `(16, 6)` | Sample/analysis connection |
| `drain_vent` | Thin solid, stub | `width=1`, short length only | Drain or vent branch |

### Rendering Dashed Lines with PIL

PIL's `ImageDraw` does not natively support dashed lines. Use a helper:

```python
def draw_dashed_line(draw, p1, p2, dash=(8, 4), width=1, fill="black"):
    x1, y1 = p1
    x2, y2 = p2
    length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    dash_on, dash_off = dash
    pos, drawing = 0.0, True
    while pos < length:
        seg = dash_on if drawing else dash_off
        end = min(pos + seg, length)
        if drawing:
            draw.line(
                [(x1 + dx * pos, y1 + dy * pos),
                 (x1 + dx * end, y1 + dy * end)],
                fill=fill, width=width
            )
        pos, drawing = end, not drawing
```

---

## 13. Pipe Spec Codes & Tag Assembly

The project does not use fluid-service codes in the pipe tag. Pipe identity is encoded as:

```
[Size]-[Spec]-[Seq]
Example:  6-JD-1001
```

### Available Spec Codes

```python
PIPE_SPEC_CODES = ["JD", "CK", "AB", "EF", "GH", "PN", "WR", "ST", "HX", "MN"]
```

These are synthetic spec identifiers. In a real plant each code maps to a specific material class (pressure rating, material, gasket type). For training-data generation they are treated as opaque strings — randomly assigned at pipe creation and held constant along an entire pipe run.

### Tag Assembly Rules

```python
def build_pipe_tag(size: int, spec: str, seq: int) -> str:
    return f"{size}-{spec}-{seq:04d}"   # e.g. "8-AB-0042"

def build_component_tag(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:03d}"        # e.g. "GV-042"
```

- `size` must be a member of `PIPE_SIZES`.
- `spec` must be a member of `PIPE_SPEC_CODES`.
- Sequence numbers are zero-padded and unique within their prefix group per diagram.

---

## 14. Off-Page Connectors

Off-page connectors appear wherever a pipe continues on another drawing sheet. They are essential for multi-sheet P&IDs and make a key YOLO detection target.

### Visual Form
A right-pointing arrow (or pentagon shape) with a sheet reference tag inside or beside it.
Direction convention:
- **Arrow pointing right** → flow exits this sheet (source side)
- **Arrow pointing left** → flow enters this sheet (sink side)

### Tag Format
```
[Sheet Number] / [Line Tag]
Example:  03 / 6"-PW-A1-042
```

### Graph Representation
```python
# Sink connector — flow leaving this sheet
G.add_node("OPC_OUT_01", type="off_page", direction="out",
           ref_sheet=3, ref_line="6-PW-A1-042")

# Source connector — flow arriving from another sheet
G.add_node("OPC_IN_01",  type="off_page", direction="in",
           ref_sheet=2, ref_line="6-PW-A1-042")
```

### Rules
- A `direction="out"` node has `in_degree=1`, `out_degree=0` — it is a valid graph sink.
- A `direction="in"` node has `in_degree=0`, `out_degree=1` — it is a valid graph source.
- Matching `ref_line` tags on two different sheets means they are the same physical pipe.

---

## 15. Title Block & Border

Every real P&ID sheet has a standardised border. Including it in generated images makes the training data much closer to real scanned drawings.

### Governing Standard — ISO 7200:2004

**ISO 7200:2004** (*Technical product documentation — Data fields in title blocks and document headers*) is the international standard that defines exactly which fields must and may appear in an engineering drawing title block.  It supersedes ISO 7200:1984 and is the standard against which the generator is aligned.

#### Mandatory fields (ISO 7200:2004 §5)

| ISO 7200 field name | Generator key | Source / logic |
|---|---|---|
| Legal owner | `legal_owner` | Random pick from `ORGANIZATION_NAMES` |
| Document identification number | `doc_number` | `{project_number}-PID-{idx:04d}` |
| Document title | `doc_title` + `doc_title_2` | Random pair from `DIAGRAM_TITLE_PAIRS` |
| Creator (draughtsman) | `creator` | Random initials from `PERSON_INITIALS` |
| Date of creation | `creation_date` | Random date 30–365 days before generation date |
| Approval person | `approval_person` | Random initials from `PERSON_INITIALS` |
| Date of approval | `approval_date` | `creation_date` + 1–14 days |
| Document type | `doc_type` | Random pick from `CONTRACT_NAMES` |
| Sheet / segment number | `sheet_number` | `P&ID-{idx:02d}` |

#### Optional fields rendered by the generator (ISO 7200:2004 §6 / industry practice)

| Field name | Generator key | Source / logic |
|---|---|---|
| Customer / client | `client` | Random pick from `CLIENT_NAMES` |
| Plant / facility | `plant` | Random pick from `PLANT_NAMES` |
| Project number | `project_number` | `PRJ-{randint(1000,9999)}` |
| Revision index | `revisions[i].rev` | Letters `A`–`E` |
| Revision description | `revisions[i].description` | Random pick from `REVISION_DESCRIPTIONS` |
| Revision date | `revisions[i].date` | Incremented after creation date |
| Checked by | `revisions[i].chk` | Random initials from `PERSON_INITIALS` |
| Scale | `scale` | Always `"NTS"` (Not to Scale) |

> ISO 7200 also defines optional fields for *language code*, *superseded document number*, and *electronic file reference* which are not rendered by the generator as they add no training-data value.

### Layout

The title block occupies the bottom **180 px** of the canvas and is divided into three vertical columns:

```
┌──────────────────────────────────┬──────────────────┬──────────────────┐
│ LEGAL OWNER                      │ REV | DESC | DATE │ DOC NUMBER       │
│ CLIENT: …                        │ A   | …    | …    │ DOC TYPE         │
│ PLANT:  …                        │ B   | …    | …    │ PROJ NUMBER      │
│ TITLE LINE 1                     │ C   | …    | …    ├──────────────────┤
│ TITLE LINE 2                     │                   │ SHEET   SCALE    │
│ DRN: XX  DATE   APPR: YY  DATE   │                   │ P&ID-01  NTS     │
└──────────────────────────────────┴──────────────────┴──────────────────┘
  DISCLAIMER TEXT (two lines, grey, below the block boundary)
```

Column widths (px, 4096-wide canvas):
- Left panel: `total_width − 500 − 260`
- Revision table: `500`
- Stamp column: `260`

### Constant Pools Used

```python
ORGANIZATION_NAMES = [
    "AUTOMATION LABS", "SYNTH ENGINEERING", "PROCESS SYSTEMS INC",
    "DIGITAL PROCESS CO", "CONTROL DYNAMICS LTD",
    "APEX PROCESS GROUP", "MERIDIAN ENGINEERING", "CRESTLINE INDUSTRIAL",
    "VECTOR PROCESS TECH", "PINNACLE SYSTEMS ENG",
]

CLIENT_NAMES = [
    "GLOBAL PETROCHEMICALS LTD", "NORTHFIELD REFINING CO",
    "STRATA ENERGY CORP", "BLUECREST UTILITIES", "IRONGATE PROCESSING INC",
    "VERITAS CHEMICAL GROUP", "SOLARIS FUELS PLC", "CONTINENTAL OIL & GAS",
]

PLANT_NAMES = [
    "SYNTH PLANT A", "UNIT 100 — CRUDE DISTILLATION",
    "UNIT 200 — HYDROTREATER", "UNIT 300 — REFORMER",
    "OFFSITE STORAGE AREA", "UTILITIES ISLAND",
    "TANK FARM COMPLEX", "COOLING WATER SYSTEM",
]

CONTRACT_NAMES = [
    "PROJ. DEF P&ID", "SYNTH PROC. P&ID", "PROCESS FLOW DWG",
    "PLANT LAYOUT P&ID", "UTILITY SYS. P&ID",
    "OFFSITE FACILITIES P&ID", "TANK FARM PIPING P&ID",
    "COMPRESSOR STATION P&ID", "HEAT RECOVERY UNIT P&ID",
    "WATER TREATMENT P&ID",
]

DIAGRAM_TITLE_PAIRS = [
    ("SYNTHETIC PROCESS FLOW DIAGRAM",
     "SYNTHETIC PROCESS ENGINEERING FLOW SCHEME"),
    ("SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM",
     "SYNTHETIC UTILITY FLOW DIAGRAM"),
    ("SYNTHETIC PROCESS FLOW DIAGRAM",
     "SYNTHETIC PIPING & INSTRUMENTATION DIAGRAM"),
    ("SYNTHETIC MECHANICAL FLOW DIAGRAM",
     "SYNTHETIC HEAT & MATERIAL BALANCE DIAGRAM"),
]

REVISION_DESCRIPTIONS = [
    "ISSUED FOR CONSTRUCTION", "ISSUED FOR REVIEW", "ISSUED FOR APPROVAL",
    "ISSUE CONSTR. REV.", "REVISED PER COMMENTS", "PRELIMINARY ISSUE",
    "AS BUILT REVISION", "UPDATED PER CLIENT REV.", "FINAL ISSUE",
    "ISSUED FOR BID", "ISSUED FOR DESIGN", "ISSUED FOR INFORMATION",
    "ISSUED FOR PROCUREMENT", "REVISED PER HAZOP", "UPDATED PER SITE SURVEY",
]

PERSON_INITIALS = [
    "J.R.", "S.K.", "A.M.", "T.W.", "R.P.",
    "D.L.", "C.H.", "M.F.", "B.N.", "E.C.",
]
```

### Disclaimer

Every generated drawing must include the disclaimer text below the title block:

```python
DISCLAIMER_TEXT = (
    "PLEASE NOTE THIS DISCLAIMER CAREFULLY. THIS DOCUMENT IS COMPLETELY "
    "SYNTHETICALLY GENERATED AND IS NOT A REAL ENGINEERING DRAWING. IT IS "
    "INTENDED FOR RESEARCH AND TRAINING PURPOSES ONLY. ANY RESEMBLANCE "
    "TO ACTUAL PROJECTS OR FACILITIES IS ENTIRELY COINCIDENTAL. DO NOT "
    "USE THIS DRAWING FOR CONSTRUCTION, PROCUREMENT, OR OPERATION."
)
```

### Generator API

```python
from pid_generator.title_block import generate_title_block_metadata, draw_title_block

metadata = generate_title_block_metadata(idx=1, seed=42)
# Returns a fully-populated dict with all mandatory + optional ISO 7200 fields.
# render_diagram() calls this automatically when metadata=None.
```

### Revision Table

Up to 3 revision rows are generated per diagram.  Row count is sampled from `randint(1, 3)`.

| Rev | Description | Date | By | Chk |
|---|---|---|---|---|
| A | *(from `REVISION_DESCRIPTIONS`)* | *(creation_date + offset)* | *(initials)* | *(initials)* |
| B | *(from `REVISION_DESCRIPTIONS`)* | *(prev + 7–60 days)* | *(initials)* | *(initials)* |

### Standards Reference

| Standard | Scope |
|---|---|
| **ISO 7200:2004** | Mandatory and optional title block data fields for technical product documentation |
| **ISO 10628-1:2014** | Flow diagrams for process plants — rules on sheet content and drawing structure |
| **ISO 5457:1999** | Technical product documentation — sizes and layout of drawing sheets |

---

## 16. Coordinate System & Canvas Scale

Defines the pixel space the renderer works in. All layout functions should use these constants.

### Recommended Canvas Defaults

| Parameter | Value | Notes |
|---|---|---|
| Canvas width | `4096 px` | A1 sheet at 200 DPI |
| Canvas height | `2896 px` | A1 landscape |
| Background color | `#FFFFFF` | White |
| Border margin | `40 px` | Space reserved for title block border |
| Grid cell size | `128 px` | One "unit" in the normalised layout grid |
| Symbol bounding box | `96 × 96 px` | Default before rotation or scaling |
| Pipe width (process) | `3 px` | Main process line |
| Pipe width (utility) | `1 px` | Utility / signal line |
| Min pipe segment length | `64 px` | Prevents symbols from touching directly |

### Coordinate Mapping

Normalised graph positions `(0.0 – 1.0)` map to pixel coordinates as:

```python
CANVAS_W, CANVAS_H = 4096, 2896
MARGIN = 40

def to_pixel(norm_x: float, norm_y: float) -> tuple[int, int]:
    usable_w = CANVAS_W - 2 * MARGIN
    usable_h = CANVAS_H - 2 * MARGIN
    return (
        int(MARGIN + norm_x * usable_w),
        int(MARGIN + norm_y * usable_h),
    )
```

### Grid Snapping

All node positions must snap to the grid to guarantee orthogonal routing:

```python
GRID = 128  # px

def snap_to_grid(px: int, py: int) -> tuple[int, int]:
    return (round(px / GRID) * GRID, round(py / GRID) * GRID)
```

---

## 17. Graph Node & Edge JSON Schema

Use this schema as the single contract between the graph builder, validator, and renderer. Any key marked **required** will cause a `KeyError` if missing.

### Node Schema

```json
{
  "id": "PUMP_01",
  "type": "equipment",
  "class_id": 24,
  "size": 8,
  "tag": "P-101",
  "orientation": 0,
  "pos": [0.2, 0.5],
  "sheet": 1
}
```

| Key | Type | Required | Valid values | Description |
|---|---|---|---|---|
| `id` | string | yes | any unique string | Node identifier (e.g. `PUMP_01`) |
| `type` | string | yes | `equipment`, `valve`, `instrument`, `off_page`, `fitting` | Category for degree-constraint checks |
| `class_id` | int | yes | See Section 11 | YOLO detection class |
| `size` | int | yes | `PIPE_SIZES` = `[2,4,6,8,10,12,14,16]` | Nozzle / connection size in inches |
| `tag` | string | yes | `[PREFIX]-[seq]` | Built from `VALVE_PREFIXES`, `INSTRUMENT_PREFIXES`, or `EQUIPMENT_PREFIXES` |
| `orientation` | int | no | `0`, `90`, `180`, `270` | Defaults to `0`; set by renderer |
| `pos` | [float, float] | no | 0.0–1.0 each | Normalised canvas position; set by layout step |
| `sheet` | int | no | ≥ 1 | Sheet number; defaults to `1` |

### Edge Schema

```json
{
  "source": "PUMP_01",
  "target": "VALVE_01",
  "type": "process",
  "size": 8,
  "spec": "AB",
  "tag": "8-AB-0001"
}
```

| Key | Type | Required | Valid values | Description |
|---|---|---|---|---|
| `source` | string | yes | existing node `id` | Upstream node |
| `target` | string | yes | existing node `id` | Downstream node |
| `type` | string | yes | See Section 12 | Line visual style |
| `size` | int | yes | `PIPE_SIZES` = `[2,4,6,8,10,12,14,16]` | Nominal pipe size in inches |
| `spec` | string | yes | `PIPE_SPEC_CODES` = `["JD","CK","AB","EF","GH","PN","WR","ST","HX","MN"]` | Pipe material/class code |
| `tag` | string | no | `[size]-[spec]-[seq:04d]` | Auto-generated if omitted |

---

## 18. Rendering Pipeline

The full sequence from an empty graph to a finished image. Each stage has a clear input and output.

```
┌─────────────────────────────────────────────────────────┐
│  STAGE 1 — Graph Build                                  │
│  Input : generation parameters (node count, fluids…)    │
│  Output: nx.DiGraph with node + edge attributes         │
│  Tools : create_logical_system(), add_control_loops()   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 2 — Validation                                   │
│  Input : nx.DiGraph                                     │
│  Output: validated graph or list of warnings/errors     │
│  Tools : validate_pid_logic()                           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 3 — Layout                                       │
│  Input : validated graph                                │
│  Output: graph with `pos` attribute set on every node   │
│  Tools : assign_grid_positions(), snap_to_grid()        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 4 — Canvas Init                                  │
│  Input : canvas constants                               │
│  Output: blank PIL Image + ImageDraw context            │
│  Tools : Image.new(), draw_title_block()                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 5 — Pipe Rendering (edges)                       │
│  Input : graph edges with pos resolved to pixels        │
│  Output: canvas with all pipes drawn                    │
│  Tools : draw_line_between(), draw_dashed_line()        │
│  Order : process lines first, then utility, then signal │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 6 — Pipe Crossing Gaps                           │
│  Input : canvas, list of H/V pipe intersections         │
│  Output: canvas with jump gaps drawn over crossings     │
│  Tools : draw_pipe_jump()                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 7 — Symbol Rendering (nodes)                     │
│  Input : graph nodes with pos + class_id + orientation  │
│  Output: canvas with all symbols placed                 │
│  Tools : apply_symbol_mask(), place_template()          │
│  Order : equipment first, then valves, then instruments │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 8 — Text Tag Rendering                           │
│  Input : graph nodes + edges with `tag` attributes      │
│  Output: canvas with all labels placed                  │
│  Tools : draw_tag(), build_line_tag()                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 9 — Visual Noise                                 │
│  Input : clean canvas                                   │
│  Output: canvas with realistic imperfections            │
│  Tools : add_salt_pepper(), apply_slight_rotation()     │
│          draw_revision_cloud()                          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  STAGE 10 — YOLO Label Export                           │
│  Input : graph nodes with pos + class_id + canvas size  │
│  Output: .txt file per image (YOLO normalised bbox)     │
│  Tools : export_yolo_labels()                           │
└─────────────────────────────────────────────────────────┘
```

### YOLO Label Export

```python
def export_yolo_labels(G, pos, canvas_w, canvas_h, out_path: str):
    lines = []
    for node, data in G.nodes(data=True):
        px, py = to_pixel(*pos[node])
        bw = bh = 96  # default symbol bounding box
        # Normalise to 0–1
        cx = px / canvas_w
        cy = py / canvas_h
        nw = bw / canvas_w
        nh = bh / canvas_h
        lines.append(f"{data['class_id']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
```

---

## 19. Equipment Sizing Rules

These constraints prevent physically impossible combinations in the generated graph.

| Rule | Description |
|---|---|
| Pump suction > discharge | Suction nozzle is always one pipe size larger than discharge (e.g. 6" suction → 4" discharge) |
| Vessel nozzle ≤ vessel diameter | No nozzle can be wider than the vessel it connects to |
| Control valve smaller than line | A control valve is typically one size smaller than the pipe (e.g. 3" CV on a 4" line, with reducers) |
| Relief valve outlet ≥ inlet | Outlet size must be equal or larger to handle the relieved flow |
| Strainer before control valve | A Y-strainer (class_id=34) must be placed immediately upstream of any control valve |
| Eccentric reducer on pump suction | Use class_id=33 (eccentric) on horizontal pump suction; class_id=32 (concentric) elsewhere |

---

## 20. Engineering Notes Pool

Real P&IDs carry a "General Notes" block — a numbered list of project-wide engineering requirements. The generator picks a random subset from the pool and renders them in a notes box on the drawing.

```python
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
```

### Usage Rules

- Select 5–12 notes at random per drawing (more = more realistic).
- Notes that contain `{num}` are template strings; substitute a random drawing/spec reference number before rendering:

```python
import random

def render_note(template: str) -> str:
    num = random.randint(100, 999)
    return template.format(num=num)
```

- Number the notes sequentially: `1.`, `2.`, …
- Render in a bordered box in the lower-left corner of the drawing, below the main diagram area.
- Font size should be visibly smaller than component tags to reflect real drawing conventions.

### Cross-References to Other Sections

| Note content | Related section |
|---|---|
| ASME B31.3 piping | Section 21 (Standards Reference) |
| ISA-5.1 instruments | Section 2 (Text Tags) |
| Check valves at pump discharge | Section 5 (Process Logic Rules) |
| Isolation valves at equipment | Section 5 (Process Logic Rules) |
| Control valves fail closed | Section 3.3 (Control Loop Rule) |
| Drain/vent valves | Section 5 (Process Logic Rules) |
| Spectacle blinds at battery limits | Section 14 (Off-Page Connectors) |

---

## 21. Symbol Template File Structure

The renderer resolves a `class_id` integer to a physical template image file. This section defines the on-disk convention so `get_template_size()` and `place_template()` can be implemented consistently.

### Directory Layout

```
assets/
└── templates/
    ├── valves/
    │   ├── 00_ball_valve.png
    │   ├── 01_butterfly_valve.png
    │   ├── 02_check_valve.png
    │   └── ...
    ├── instruments/
    │   ├── 12_pressure_transmitter.png
    │   ├── 13_pressure_indicator.png
    │   └── ...
    ├── equipment/
    │   ├── 24_centrifugal_pump.png
    │   ├── 27_heat_exchanger.png
    │   └── ...
    └── fittings/
        ├── 32_reducer_concentric.png
        ├── 34_strainer.png
        └── ...
```

### Naming Convention

```
{class_id:02d}_{snake_case_name}.png
```

- Zero-padded two-digit class ID prefix guarantees lexicographic sort matches numeric order.
- File format: **PNG with white background** (not transparent). The masking step in Section 1.3 removes the background before compositing.

### Template Spec

| Property | Value |
|---|---|
| Format | PNG, 8-bit RGB |
| Background | Pure white `#FFFFFF` |
| Default size | 96 × 96 px (square) |
| Stroke colour | Black `#000000` |
| Line weight | 2–3 px |
| Orientation | Horizontal (0°) — all templates face right/horizontal by default |

### `get_template_size()` Implementation

```python
import os
from PIL import Image

TEMPLATE_ROOT = "assets/templates"

# Flat index built at startup: class_id -> file path
_TEMPLATE_INDEX: dict[int, str] = {}

def _build_index():
    for subdir in ("valves", "instruments", "equipment", "fittings"):
        folder = os.path.join(TEMPLATE_ROOT, subdir)
        for fname in os.listdir(folder):
            if fname.endswith(".png"):
                cid = int(fname.split("_")[0])
                _TEMPLATE_INDEX[cid] = os.path.join(folder, fname)

_build_index()

def get_template_size(class_id: int) -> tuple[str, int, int]:
    path = _TEMPLATE_INDEX[class_id]
    with Image.open(path) as img:
        w, h = img.size
    return path, w, h
```

---

## 22. Pipe Routing Algorithm

Translates a graph edge `(u, v)` into one or more straight line segments on the canvas, ensuring all segments are strictly horizontal or vertical (orthogonal routing).

### Cases

```
Case A — Same row (same y):     single horizontal segment
Case B — Same column (same x):  single vertical segment
Case C — L-shape:               one H segment + one V segment, joined at a waypoint
Case D — Z-shape (forced):      two H + one V, used when a direct L would collide
```

### Waypoint Selection for L-Shape

The waypoint is placed at the x-coordinate of the **target** node:

```
p1 = (x1, y1)    p2 = (x2, y2)    waypoint = (x2, y1)

p1 ──────────── wp
                 |
                p2
```

### Implementation

```python
def route_orthogonal(p1: tuple[int,int],
                     p2: tuple[int,int]) -> list[tuple[tuple[int,int], tuple[int,int]]]:
    """Return a list of (start, end) segment pairs forming an orthogonal path."""
    x1, y1 = p1
    x2, y2 = p2

    if y1 == y2:                        # Case A
        return [(p1, p2)]
    if x1 == x2:                        # Case B
        return [(p1, p2)]

    # Case C — L-shape via waypoint at (x2, y1)
    wp = (x2, y1)
    return [(p1, wp), (wp, p2)]
```

### Collision Avoidance (Z-Shape)

If the L-shape waypoint falls inside an existing node's bounding box, shift the horizontal segment to a midpoint row:

```python
def route_with_collision(p1, p2, occupied: list[tuple]) -> list:
    x1, y1 = p1
    x2, y2 = p2
    wp = (x2, y1)
    if any(_bbox_contains(wp, bbox) for bbox in occupied):
        mid_y = (y1 + y2) // 2
        # Z-shape: right → down → right
        return [(p1, (x2, y1)), ((x2, y1), (x2, mid_y)), ((x2, mid_y), p2)]
    return [(p1, wp), (wp, p2)]
```

---

## 23. Symbol Overlap Detection

Before placing a symbol, check that its bounding box does not overlap any previously placed symbol. If it does, either shift or skip.

### Bounding Box Registry

```python
from dataclasses import dataclass, field

@dataclass
class PlacedSymbol:
    node_id: str
    cx: int   # centre x in pixels
    cy: int   # centre y in pixels
    w:  int
    h:  int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.cx - self.w//2, self.cy - self.h//2,
                self.cx + self.w//2, self.cy + self.h//2)

_placed: list[PlacedSymbol] = []
```

### Overlap Check

```python
def _overlaps(a: tuple, b: tuple, padding: int = 8) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + padding < bx1 or bx2 + padding < ax1 or
                ay2 + padding < by1 or by2 + padding < ay1)

def can_place(cx: int, cy: int, w: int, h: int) -> bool:
    candidate = (cx - w//2, cy - h//2, cx + w//2, cy + h//2)
    return not any(_overlaps(candidate, s.bbox) for s in _placed)
```

### Placement Strategy

1. **Check** `can_place()` at the graph-derived position.
2. **Shift** — try offsets `[+GRID, -GRID, +2*GRID, -2*GRID]` on both axes.
3. **Skip** — if no valid position found after 8 attempts, omit the symbol and log a warning. Do **not** force-place overlapping symbols; this corrupts YOLO bounding boxes.

---

## 24. Control Loop Generation Algorithm

Generates a complete Transmitter → Controller → Control Valve trio with shared loop number and signal lines.

### Step-by-Step

```
1. Pick a process pipe edge (u → v) with type="process".
2. Choose a measurement variable: pressure (P), flow (F), level (L), or temperature (T).
3. Assign a loop number: next available integer in the sequence (e.g. 101).
4. Create three new nodes:
     - Transmitter  : tag=f"{var}T-{loop}"  class_id from INSTRUMENT_PREFIXES
     - Controller   : tag=f"{var}IC-{loop}" class_id from INSTRUMENT_PREFIXES
     - Control Valve: tag=f"{var}V-{loop}"  class_id from VALVE_PREFIXES ("CV" or "PCV")
5. Insert the Control Valve onto the pipe edge:
     a. Remove edge (u → v).
     b. Add edges: (u → CV_node) and (CV_node → v), inheriting size + spec.
6. Place Transmitter adjacent to the pipe (offset 1 grid cell perpendicular).
7. Add signal edges:
     - (Transmitter → Controller) type="signal_electric"
     - (Controller  → CV_node)   type="signal_electric"
8. Loop number is stored as attribute `loop` on all three nodes.
```

### Code Sketch

```python
def add_control_loop(G: nx.DiGraph, pipe_edge: tuple,
                     variable: str, loop_num: int):
    u, v, data = pipe_edge
    size, spec = data["size"], data["spec"]

    cv_id  = f"{variable}V_{loop_num:03d}"
    tx_id  = f"{variable}T_{loop_num:03d}"
    ctl_id = f"{variable}IC_{loop_num:03d}"

    G.remove_edge(u, v)
    G.add_node(cv_id,  type="valve",      class_id=3,
               size=size, tag=f"{variable}V-{loop_num}", loop=loop_num)
    G.add_node(tx_id,  type="instrument", class_id=_tx_class(variable),
               size=size, tag=f"{variable}T-{loop_num}",  loop=loop_num)
    G.add_node(ctl_id, type="instrument", class_id=_ctl_class(variable),
               size=size, tag=f"{variable}IC-{loop_num}", loop=loop_num)

    G.add_edge(u,      cv_id,  size=size, spec=spec, type="process")
    G.add_edge(cv_id,  v,      size=size, spec=spec, type="process")
    G.add_edge(tx_id,  ctl_id, type="signal_electric")
    G.add_edge(ctl_id, cv_id,  type="signal_electric")
```

---

## 25. YOLO Dataset Folder Structure

YOLOv8/v11 expects a specific folder layout. The batch generator must produce this structure directly.

### Folder Layout

```
dataset/
├── data.yaml
├── images/
│   ├── train/
│   │   ├── pid_0001.png
│   │   ├── pid_0002.png
│   │   └── ...
│   ├── val/
│   │   ├── pid_0801.png
│   │   └── ...
│   └── test/
│       ├── pid_0901.png
│       └── ...
└── labels/
    ├── train/
    │   ├── pid_0001.txt
    │   └── ...
    ├── val/
    │   └── ...
    └── test/
        └── ...
```

### `data.yaml`

```yaml
path: dataset          # root relative to train script
train: images/train
val:   images/val
test:  images/test

nc: 42                 # number of classes (update when class list changes)
names:
  0:  ball_valve
  1:  butterfly_valve
  2:  check_valve
  3:  control_valve
  4:  gate_valve
  5:  globe_valve
  6:  needle_valve
  7:  plug_valve
  8:  relief_valve
  9:  pressure_reducing_valve
  10: diaphragm_valve
  11: angle_valve
  12: pressure_transmitter
  13: pressure_indicator
  14: pressure_controller
  15: temperature_transmitter
  16: temperature_indicator
  17: flow_transmitter
  18: flow_indicator
  19: flow_controller
  20: level_transmitter
  21: level_indicator
  22: level_controller
  23: analyser_transmitter
  24: centrifugal_pump
  25: reciprocating_pump
  26: compressor
  27: heat_exchanger
  28: vertical_vessel
  29: horizontal_vessel
  30: storage_tank
  31: agitator
  32: reducer_concentric
  33: reducer_eccentric
  34: strainer
  35: spectacle_blind
  36: expansion_joint
  37: flame_arrestor
  38: off_page_connector
  39: instrument_bubble
  40: junction_tee
  41: pipe_crossing
```

### Label File Format (per image)

One line per detected symbol:

```
<class_id> <cx_norm> <cy_norm> <w_norm> <h_norm>
```

All values normalised 0–1 relative to image width/height. Example:

```
4  0.312500 0.437500 0.023438 0.033088
12 0.500000 0.300000 0.023438 0.033088
```

---

## 26. Batch Generation Pipeline

### Split Ratios

| Split | Fraction | Usage |
|---|---|---|
| train | 80% | Model training |
| val | 10% | Hyperparameter tuning & early stopping |
| test | 10% | Final evaluation only — never seen during training |

### File Naming

```python
def image_filename(idx: int) -> str:
    return f"pid_{idx:04d}.png"     # pid_0001.png … pid_9999.png

def label_filename(idx: int) -> str:
    return f"pid_{idx:04d}.txt"
```

### Seed Reproducibility

```python
import random, numpy as np

def set_global_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
```

Set once at the top of the generation script. Log the seed value alongside each generated image in a `manifest.csv` so any individual diagram can be reproduced.

### Manifest CSV

```
idx, seed, sheet_count, node_count, edge_count, split
1,   42,   1,           18,         22,          train
2,   42,   1,           11,         13,          val
```

### Parallelisation

```python
from multiprocessing import Pool

def generate_one(args: tuple) -> str:
    idx, seed = args
    set_global_seed(seed + idx)   # unique seed per diagram
    G    = create_logical_system()
    pos  = assign_grid_positions(G)
    img  = render_from_graph(G, pos)
    path = save_image_and_label(img, G, pos, idx)
    return path

if __name__ == "__main__":
    N = 1000
    seeds = [(i, 42) for i in range(N)]
    with Pool() as pool:
        results = pool.map(generate_one, seeds)
```

> Note: PIL is not thread-safe but is process-safe. Use `multiprocessing.Pool`, not `ThreadPoolExecutor`.

---

## 27. Augmentation Catalogue

Augmentations split into two categories:

- **Generation-time** — baked into the saved PNG; the YOLO label remains valid.
- **Training-time** — applied by the YOLO framework on-the-fly (e.g. Albumentations); not stored on disk.

### Generation-Time Augmentations

| Augmentation | Parameters | PIL Implementation | Notes |
|---|---|---|---|
| Salt & pepper noise | density 0.002–0.01 | Random pixel set to black/white | Simulates scan noise |
| Slight rotation | ±0.3°–1.5° | `Image.rotate(angle, expand=False)` | Simulates non-straight scan |
| JPEG compression | quality 60–85 | `img.save(..., format="JPEG", quality=q)` then reload | Simulates photocopied drawing |
| Brightness jitter | factor 0.85–1.15 | `ImageEnhance.Brightness(img).enhance(f)` | Simulates uneven scanner exposure |
| Gaussian blur | radius 0.3–0.8 | `img.filter(ImageFilter.GaussianBlur(r))` | Simulates out-of-focus scan |
| Contrast jitter | factor 0.9–1.1 | `ImageEnhance.Contrast(img).enhance(f)` | Simulates faded blueprint |

### Training-Time Augmentations (Albumentations / YOLO built-in)

| Augmentation | Recommended | Reason |
|---|---|---|
| Horizontal flip | No | P&IDs have directional meaning; flipping reverses flow |
| Vertical flip | No | Same reason |
| Random crop | Yes (10–15%) | Simulates partial scans |
| Mosaic | Yes | Standard YOLO augmentation; improves small-object detection |
| Copy-paste | Yes | Duplicates symbols into other images; increases class balance |
| Hue/saturation | No | Drawings are greyscale; hue shift adds no useful variation |

### Applying Generation-Time Augmentations

```python
import random
from PIL import ImageEnhance, ImageFilter

def apply_generation_noise(img):
    # Salt & pepper
    import numpy as np
    arr = np.array(img)
    mask = np.random.random(arr.shape[:2]) < 0.005
    arr[mask] = 0
    mask2 = np.random.random(arr.shape[:2]) < 0.005
    arr[mask2] = 255
    img = Image.fromarray(arr)

    # Brightness jitter
    img = ImageEnhance.Brightness(img).enhance(random.uniform(0.88, 1.12))

    # Slight rotation
    angle = random.uniform(-1.0, 1.0)
    img = img.rotate(angle, fillcolor=255)

    return img
```

---

## 28. Validation Error Catalogue

Full list of errors and warnings `validate_pid_logic()` can raise, with the recommended auto-fix for each.

| Code | Severity | Condition | Auto-fix |
|---|---|---|---|
| `E001` | Error | Check valve (`CK`) has `in_degree != 1` | Remove node if isolated; raise if in a loop |
| `E002` | Error | Pump has `in_degree != 1` or `out_degree != 1` | Add missing suction/discharge stub edge to off-page connector |
| `E003` | Error | Edge `size` not in `PIPE_SIZES` | Round to nearest valid size |
| `E004` | Error | Edge `spec` not in `PIPE_SPEC_CODES` | Replace with random valid spec |
| `E005` | Error | Node `size` differs from connected edge `size` with no reducer between them | Insert reducer node automatically |
| `E006` | Error | Control valve has no incoming signal edge | Call `add_control_loop()` to wire a minimal loop |
| `E007` | Error | Graph has no source node (in_degree=0 for all non-off-page nodes) | Add a pump node at grid position (0.1, 0.5) |
| `E008` | Error | Graph has no sink node (out_degree=0 for all non-off-page nodes) | Add an off-page connector at grid position (0.9, 0.5) |
| `W001` | Warning | Valve has `in_degree=0` or `out_degree=0` (dangling) | Log; skip rendering this node |
| `W002` | Warning | Two nodes share the same `pos` grid cell | Shift one node by one grid cell |
| `W003` | Warning | Control loop exists but `loop` attribute not set on all three nodes | Set `loop` to next available integer |
| `W004` | Warning | Relief valve outlet not connected to a flare/vent node | Log only; no auto-fix |

### Validator Skeleton

```python
def validate_pid_logic(G: nx.DiGraph) -> list[str]:
    errors = []
    for node, data in G.nodes(data=True):
        cid = data.get("class_id")

        if cid == 2 and G.in_degree(node) != 1:          # E001
            errors.append(f"E001: Check valve {node} in_degree={G.in_degree(node)}")

        if data.get("type") == "equipment" and cid in (24, 25):
            if G.in_degree(node) != 1 or G.out_degree(node) != 1:
                errors.append(f"E002: Pump {node} degree constraint violated")

        if data.get("type") == "control_valve":
            has_signal = any(
                G[u][v].get("type") == "signal_electric"
                for u, v in G.edges(node)
            )
            if not has_signal:
                errors.append(f"E006: Control valve {node} missing signal line")

    for u, v, edata in G.edges(data=True):
        if edata.get("size") not in (2, 4, 6, 8, 10, 12, 14, 16):
            errors.append(f"E003: Edge ({u}→{v}) invalid size {edata.get('size')}")
        if edata.get("spec") not in ("JD","CK","AB","EF","GH","PN","WR","ST","HX","MN"):
            errors.append(f"E004: Edge ({u}→{v}) invalid spec {edata.get('spec')}")

    return errors
```

---

## 29. Multi-Sheet Linking

For diagrams that span more than one sheet, the graph is partitioned and linked via off-page connector pairs.

### Partitioning Strategy

```
1. Build the full single-sheet graph normally.
2. If node count > MAX_NODES_PER_SHEET (default: 30):
   a. Perform a graph cut using nx.minimum_edge_cut() or a simple
      topological split at a long pipe edge.
   b. For each cut edge (u → v):
      - Remove the edge.
      - Add OPC_OUT node after u  (direction="out", ref_sheet=N+1)
      - Add OPC_IN  node before v (direction="in",  ref_sheet=N,
                                   ref_line = same tag as cut edge)
3. Assign each partition to its own sheet number.
4. Render each partition as a separate image.
```

### Matching Rule

Two off-page connectors are a matched pair when:

```python
def are_matched(a: dict, b: dict) -> bool:
    return (
        a["direction"] != b["direction"] and   # one out, one in
        a["ref_line"]  == b["ref_line"]         # same physical pipe
    )
```

### Validation Check

After partitioning, every `direction="out"` node on sheet X must have exactly one `direction="in"` counterpart on another sheet with the same `ref_line`. If no match exists, it is an unlinked connector — flag as `W005`.

---

## 30. Standards Reference

| Standard | Scope | Key Rules Covered |
|---|---|---|
| **ANSI/ISA-5.1** | Instrumentation symbols & identification | Instrument tag format, bubble styles, signal line types (Sections 2, 12) |
| **ISO 10628-2** | P&ID diagram content and structure | Line break rule, off-page connectors, title block (Sections 4, 14, 15) |
| **ISO 14617** | Graphical symbols for diagrams | Symbol shapes for valves, equipment, fittings (Section 11) |
| **ASME B31.3** | Process piping | Pipe spec / material class codes (Section 13) |
| **IEC 62424** | Process control diagrams (CAEX) | Control loop pairing, signal consistency (Section 3.3) |

> These standards are referenced for design intent only. The generator produces synthetic training data, not certified engineering drawings.

---

## 31. Random Topology Mode (Level 1 Fallback)

To align with the Paliwal et al. (2021) Digitize-PID approach, the generator supports a **purely random graph topology** as a Level 1 mode before any domain constraints are applied. This is useful for generating high-volume, visually varied data without engineering correctness requirements.

### When to Use

| Mode | Use case |
|---|---|
| Random topology | Maximum visual diversity; symbol detector pre-training |
| Domain-constrained (Sections 3–5) | Engineering-aware training; context-learning phase |

### Algorithm

```
1. Sample node count N from uniform(MIN_NODES, MAX_NODES).
2. Create N nodes, each assigned a class_id sampled uniformly from
   the 42-class pool (Section 11).
3. Build edges using one of:
   a. Erdős–Rényi  — G(N, p) with p = 0.3 (sparse random)
   b. Barabási–Albert — preferential attachment; creates hubs like
      real P&ID junction points.
4. Convert to DiGraph; assign random flow direction per edge.
5. Assign size + spec to every edge (random draw from PIPE_SIZES /
   PIPE_SPEC_CODES), ignoring size-match rules.
6. Skip validation (Section 28); proceed directly to layout.
```

### Implementation

```python
import random
import networkx as nx

PIPE_SIZES      = [2, 4, 6, 8, 10, 12, 14, 16]
PIPE_SPEC_CODES = ["JD", "CK", "AB", "EF", "GH", "PN", "WR", "ST", "HX", "MN"]
ALL_CLASS_IDS   = list(range(42))   # 0–41 per Section 11

def create_random_topology(
    min_nodes: int = 6,
    max_nodes: int = 20,
    edge_prob: float = 0.3,
) -> nx.DiGraph:
    N   = random.randint(min_nodes, max_nodes)
    ug  = nx.erdos_renyi_graph(N, edge_prob, seed=None)
    G   = nx.DiGraph(ug)   # arbitrarily directed

    for i, node in enumerate(G.nodes()):
        cid = random.choice(ALL_CLASS_IDS)
        G.nodes[node].update({
            "id":       f"NODE_{i:03d}",
            "class_id": cid,
            "type":     _type_from_class(cid),
            "size":     random.choice(PIPE_SIZES),
            "tag":      f"SYM-{i:03d}",
        })

    for u, v in G.edges():
        G[u][v].update({
            "size": random.choice(PIPE_SIZES),
            "spec": random.choice(PIPE_SPEC_CODES),
            "type": "process",
        })

    return G

def _type_from_class(cid: int) -> str:
    if cid <= 11:  return "valve"
    if cid <= 23:  return "instrument"
    if cid <= 31:  return "equipment"
    return "fitting"
```

### Class Balance Enforcement

Uniform random sampling will naturally skew toward the most common class IDs. To enforce balance across the 42 classes, use a **stratified draw**:

```python
def create_balanced_random_topology(n_nodes: int = 42) -> nx.DiGraph:
    """Guarantee at least one node per class in a single diagram."""
    G = nx.DiGraph()
    cids = list(range(42))
    random.shuffle(cids)

    for i, cid in enumerate(cids[:n_nodes]):
        G.add_node(i, class_id=cid, type=_type_from_class(cid),
                   size=random.choice(PIPE_SIZES), tag=f"SYM-{i:03d}")

    # Sparse random edges
    nodes = list(G.nodes())
    for u in nodes:
        for v in nodes:
            if u != v and random.random() < 0.15:
                G.add_edge(u, v, size=random.choice(PIPE_SIZES),
                           spec=random.choice(PIPE_SPEC_CODES), type="process")
    return G
```

---

## 32. Graph Serialisation (Ground-Truth Connectivity Export)

The YOLO label file (Section 18, Stage 10) records **bounding boxes only** — it does not capture which symbols are connected. For digitization research (training a graph-recovery pipeline), the underlying `nx.DiGraph` must also be persisted alongside each image.

### Output Format

Each generated image `pid_XXXX.png` must have a companion file `pid_XXXX_graph.json` in the same directory, containing the full node-link representation of the graph.

### Serialisation

```python
import json
import networkx as nx
from networkx.readwrite import node_link_data

def export_graph(G: nx.DiGraph, out_path: str):
    """Serialise graph to JSON using NetworkX node-link format."""
    data = node_link_data(G)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
```

### Deserialisation

```python
from networkx.readwrite import node_link_graph

def load_graph(path: str) -> nx.DiGraph:
    with open(path) as f:
        data = json.load(f)
    return node_link_graph(data, directed=True, multigraph=False)
```

### File Naming Convention

```python
def graph_filename(idx: int) -> str:
    return f"pid_{idx:04d}_graph.json"
```

### JSON Structure (example)

```json
{
  "directed": true,
  "multigraph": false,
  "nodes": [
    {"id": "PUMP_01", "type": "equipment", "class_id": 24,
     "size": 8, "tag": "P-101", "pos": [0.2, 0.5]},
    {"id": "VALVE_01", "type": "valve", "class_id": 4,
     "size": 8, "tag": "GV-042", "pos": [0.4, 0.5]}
  ],
  "links": [
    {"source": "PUMP_01", "target": "VALVE_01",
     "size": 8, "spec": "AB", "type": "process", "tag": "8-AB-0001"}
  ]
}
```

### Manifest Update

Add `graph_path` to the manifest CSV (Section 26):

```
idx, seed, sheet_count, node_count, edge_count, split, graph_path
1,   42,   1,           18,         22,          train, labels/train/pid_0001_graph.json
```

### Dataset Folder Layout (updated)

```
dataset/
├── data.yaml
├── images/
│   ├── train/
│   │   ├── pid_0001.png
│   │   └── ...
│   └── val/ ...
└── labels/
    ├── train/
    │   ├── pid_0001.txt          ← YOLO bounding boxes
    │   ├── pid_0001_graph.json   ← ground-truth connectivity
    │   └── ...
    └── val/ ...
```

> **Note (Paliwal et al. limitation):** The publicly released Dataset-P&ID provides image and bounding-box annotations but does not always include the ground-truth graph in a direct format. Exporting `_graph.json` alongside every image addresses this gap and makes the synthetic dataset usable for both detection and graph-recovery benchmarks.
