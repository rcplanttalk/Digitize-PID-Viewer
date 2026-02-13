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

Real P&IDs carry text tags on every component. Use your `PREFIXES` lists to generate unique identifiers.

### Tag Formats

| Component | Format | Example | Placement |
|---|---|---|---|
| Pipes | `[Size]-[Spec]-[Service]-[Seq]` | `6"-JD-1001-ST` | Parallel to line, centred |
| Valves | `[Type]-[Seq]` | `GV-042` | Directly above/beside the valve |
| Instruments | `[Function]-[Seq]` | `PT-101` | Inside or below the instrument bubble |

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
