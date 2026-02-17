"""Logical P&ID graph builder (§6, §24).

Builds a domain-constrained ``nx.DiGraph`` representing a scalable process
system: parallel pump trains feeding into a series of processing stages with
randomised control loops, all terminated at a product storage vessel.
"""

import random

import networkx as nx

from pid_generator.constants import PIPE_SIZES, PIPE_SPEC_CODES
from pid_generator.tags import build_component_tag, build_pipe_tag

# Instrument class IDs per measurement variable (§11.2)

_TX_CLASS: dict[str, int] = {
    "P": 12,  # Pressure Transmitter
    "T": 15,  # Temperature Transmitter
    "F": 17,  # Flow Transmitter
    "L": 20,  # Level Transmitter
}

_CTL_CLASS: dict[str, int] = {
    "P": 14,  # Pressure Controller
    "T": 15,  # Temperature Controller
    "F": 19,  # Flow Controller
    "L": 22,  # Level Controller
}

# Equipment class IDs for intermediate inline process equipment (§11)
_INLINE_EQUIP_CLASSES: list[int] = [26, 27, 28, 29]  # heat exchangers, separators, …
_TANK_CLASSES: list[int] = [30, 31]                   # storage tanks, receivers
# Isolation valve class IDs (gate, globe, butterfly, ball, plug, angle, …)
_ISO_VALVE_CLASSES: list[int] = [4, 5, 6, 7, 9, 10, 11]


def _tx_class(variable: str) -> int:
    return _TX_CLASS.get(variable, 12)


def _ctl_class(variable: str) -> int:
    return _CTL_CLASS.get(variable, 14)


# Public API


def create_logical_system(seed: int | None = None, n_nodes: int | None = None) -> nx.DiGraph:
    """Build a validated process graph with variable complexity.

    Structure: OPC_IN → feed valve → [parallel pump trains] → [serial
    processing stages] → TANK.  The number of pumps, stages, and control
    loops is derived from *n_nodes* so diagrams scale from simple (~10 nodes)
    to complex (~50 nodes).

    Args:
        seed:    Optional RNG seed for reproducibility.
        n_nodes: Target node count.  Randomly chosen in [10, 50] if *None*.

    Returns:
        A directed graph (``nx.DiGraph``) with fully attributed nodes and edges.
    """
    if seed is not None:
        random.seed(seed)

    if n_nodes is None:
        n_nodes = random.randint(10, 50)

    # -----------------------------------------------------------------------
    # Structural budget calculation
    # -----------------------------------------------------------------------
    # Node costs:  OPC_IN(1) + GV_FEED(1) + TANK(1) = 3 fixed
    #              per pump train: GV_IN + PUMP + GV_OUT + CK = 4
    #              suction + discharge headers (if multi-pump): 2
    #              per stage: STR + EQ = 2
    #              per control loop: TX + CTL + CV = 3

    n_pumps = random.randint(1, min(3, max(1, n_nodes // 10)))
    multi_pump = n_pumps > 1
    overhead = 3 + n_pumps * 4 + (2 if multi_pump else 0)
    remaining = max(2, n_nodes - overhead)

    # Allocate ~half the remaining budget to stages (2 nodes each),
    # use the rest for control loops (3 nodes each).
    n_stages = max(1, remaining // 4)
    n_loops = max(0, min((remaining - n_stages * 2) // 3, n_stages + n_pumps))

    # -----------------------------------------------------------------------
    # Counters and inline helpers
    # -----------------------------------------------------------------------
    G = nx.DiGraph()
    spec = random.choice(PIPE_SPEC_CODES)
    size = random.choice(PIPE_SIZES)

    _seq = {"pipe": 1, "gv": 1, "ck": 1, "pump": 1, "str": 1, "eq": 1, "tee": 1}

    def _pe() -> dict:
        tag = build_pipe_tag(size, spec, _seq["pipe"])
        _seq["pipe"] += 1
        return {"size": size, "spec": spec, "type": "process", "tag": tag}

    def _add(nid: str, ntype: str, class_id: int, tag: str) -> None:
        G.add_node(nid, type=ntype, class_id=class_id, size=size, tag=tag)

    def _link(u: str, v: str) -> None:
        G.add_edge(u, v, **_pe())

    def _next_gv() -> tuple[str, str]:
        i = _seq["gv"]
        _seq["gv"] += 1
        return f"GV_{i:02d}", build_component_tag("GV", i)

    def _next_ck() -> tuple[str, str]:
        i = _seq["ck"]
        _seq["ck"] += 1
        return f"CK_{i:02d}", build_component_tag("CK", i)

    def _next_pump() -> tuple[str, str]:
        i = _seq["pump"]
        _seq["pump"] += 1
        return f"PUMP_{i:02d}", build_component_tag("P", 100 + i)

    def _next_str() -> tuple[str, str]:
        i = _seq["str"]
        _seq["str"] += 1
        return f"STR_{i:02d}", build_component_tag("STR", i)

    def _next_eq() -> tuple[str, str]:
        i = _seq["eq"]
        _seq["eq"] += 1
        return f"EQ_{i:02d}", build_component_tag("E", 100 + i)

    def _next_tee() -> tuple[str, str]:
        i = _seq["tee"]
        _seq["tee"] += 1
        return f"TEE_{i:02d}", build_component_tag("TEE", i)

    def _next_iso() -> tuple[str, str, int]:
        i = _seq["gv"]
        _seq["gv"] += 1
        return f"GV_{i:02d}", build_component_tag("GV", i), random.choice(_ISO_VALVE_CLASSES)

    # -----------------------------------------------------------------------
    # Feed inlet
    # -----------------------------------------------------------------------
    _add("OPC_IN_01", "off_page", 38, "OPC-IN-001")
    G.nodes["OPC_IN_01"].update({"direction": "in", "ref_sheet": 0, "ref_line": "FEED"})

    gv_feed_id, gv_feed_tag = _next_gv()
    _add(gv_feed_id, "valve", 4, gv_feed_tag)
    _link("OPC_IN_01", gv_feed_id)

    # -----------------------------------------------------------------------
    # Suction header (only when multiple pump trains share one suction line)
    # -----------------------------------------------------------------------
    if multi_pump:
        _add("HDR_SUCT_01", "fitting", 35, "HDR-S-001")
        _link(gv_feed_id, "HDR_SUCT_01")
        suct_source = "HDR_SUCT_01"
    else:
        suct_source = gv_feed_id

    # -----------------------------------------------------------------------
    # Parallel pump trains
    # -----------------------------------------------------------------------
    pump_outlets: list[str] = []
    for _ in range(n_pumps):
        gv_in_id,  gv_in_tag  = _next_gv()
        pump_id,   pump_tag   = _next_pump()
        gv_out_id, gv_out_tag = _next_gv()
        ck_id,     ck_tag     = _next_ck()

        _add(gv_in_id,  "valve",     4,                              gv_in_tag)
        _add(pump_id,   "equipment", random.choice([24, 25]),        pump_tag)
        _add(gv_out_id, "valve",     4,                              gv_out_tag)
        _add(ck_id,     "valve",     2,                              ck_tag)

        _link(suct_source, gv_in_id)
        _link(gv_in_id, pump_id)
        _link(pump_id, gv_out_id)
        _link(gv_out_id, ck_id)
        pump_outlets.append(ck_id)

    # -----------------------------------------------------------------------
    # Discharge header (merges parallel pump outlets)
    # -----------------------------------------------------------------------
    if multi_pump:
        _add("HDR_DISCH_01", "fitting", 35, "HDR-D-001")
        for po in pump_outlets:
            _link(po, "HDR_DISCH_01")
        current_tail = "HDR_DISCH_01"
    else:
        current_tail = pump_outlets[0]

    # -----------------------------------------------------------------------
    # Serial processing stages (varied composition)
    # -----------------------------------------------------------------------
    # Stage types and their approximate node cost:
    #   bare      — 1 node  (equipment only)
    #   simple    — 2 nodes (strainer + equipment)
    #   isolated  — 3 nodes (iso-valve + equipment + iso-valve)
    #   bypass    — 5 nodes (strainer + tee + equipment + bypass-valve + tee)
    _STAGE_TYPES   = ["bare", "simple", "isolated", "bypass"]
    _STAGE_WEIGHTS = [15, 35, 25, 25]

    stage_edges: list[tuple[str, str]] = []  # candidates for control loops

    for _ in range(n_stages):
        eq_class   = random.choice(_INLINE_EQUIP_CLASSES)
        stage_type = random.choices(_STAGE_TYPES, weights=_STAGE_WEIGHTS)[0]

        if stage_type == "bare":
            eq_id, eq_tag = _next_eq()
            _add(eq_id, "equipment", eq_class, eq_tag)
            _link(current_tail, eq_id)
            stage_edges.append((current_tail, eq_id))
            current_tail = eq_id

        elif stage_type == "simple":
            str_id, str_tag = _next_str()
            eq_id,  eq_tag  = _next_eq()
            _add(str_id, "fitting",   34,       str_tag)
            _add(eq_id,  "equipment", eq_class, eq_tag)
            _link(current_tail, str_id)
            _link(str_id, eq_id)
            stage_edges.extend([(current_tail, str_id), (str_id, eq_id)])
            current_tail = eq_id

        elif stage_type == "isolated":
            gv_in_id,  gv_in_tag,  gv_in_cls  = _next_iso()
            eq_id,     eq_tag                  = _next_eq()
            gv_out_id, gv_out_tag, gv_out_cls = _next_iso()
            _add(gv_in_id,  "valve",     gv_in_cls,  gv_in_tag)
            _add(eq_id,     "equipment", eq_class,    eq_tag)
            _add(gv_out_id, "valve",     gv_out_cls, gv_out_tag)
            _link(current_tail, gv_in_id)
            _link(gv_in_id, eq_id)
            _link(eq_id, gv_out_id)
            stage_edges.extend([
                (current_tail, gv_in_id),
                (gv_in_id, eq_id),
                (eq_id, gv_out_id),
            ])
            current_tail = gv_out_id

        else:  # bypass
            str_id,     str_tag             = _next_str()
            tee_in_id,  tee_in_tag          = _next_tee()
            eq_id,      eq_tag              = _next_eq()
            bv_id,      bv_tag, bv_cls      = _next_iso()
            tee_out_id, tee_out_tag         = _next_tee()
            _add(str_id,     "fitting",   34,       str_tag)
            _add(tee_in_id,  "fitting",   36,       tee_in_tag)
            _add(eq_id,      "equipment", eq_class, eq_tag)
            _add(bv_id,      "valve",     bv_cls,   bv_tag)
            _add(tee_out_id, "fitting",   36,       tee_out_tag)
            _link(current_tail, str_id)
            _link(str_id,    tee_in_id)
            _link(tee_in_id, eq_id)
            _link(tee_in_id, bv_id)
            _link(eq_id,     tee_out_id)
            _link(bv_id,     tee_out_id)
            stage_edges.extend([
                (current_tail, str_id),
                (str_id,    tee_in_id),
                (tee_in_id, eq_id),
                (eq_id,     tee_out_id),
            ])
            current_tail = tee_out_id

    # -----------------------------------------------------------------------
    # Product storage
    # -----------------------------------------------------------------------
    _add("TANK_01", "equipment", random.choice(_TANK_CLASSES), build_component_tag("T", 101))
    _link(current_tail, "TANK_01")
    stage_edges.append((current_tail, "TANK_01"))

    # -----------------------------------------------------------------------
    # Control loops on randomly selected process edges
    # -----------------------------------------------------------------------
    ctrl_vars = ["P", "T", "F", "L"] * ((n_loops // 4) + 1)
    random.shuffle(ctrl_vars)

    candidates = [e for e in stage_edges if G.has_edge(*e)]
    random.shuffle(candidates)

    loop_num = 101
    for (u, v), var in zip(candidates[:n_loops], ctrl_vars):
        if G.has_edge(u, v):
            add_control_loop(G, (u, v, G[u][v]), variable=var, loop_num=loop_num)
            loop_num += 1

    return G


def add_control_loop(
    G: nx.DiGraph,
    pipe_edge: tuple,
    variable: str,
    loop_num: int,
) -> None:
    """Insert a Transmitter–Controller–ControlValve trio onto a process pipe (§24).

    The original edge ``(u → v)`` is removed and replaced with:
    ``(u → CV) → (CV → v)`` for process flow, plus signal edges
    ``TX → CTL → CV``.

    Args:
        G:          The graph to modify in place.
        pipe_edge:  A ``(u, v, data)`` tuple identifying the target edge.
        variable:   Measurement variable letter: ``"P"``, ``"F"``, ``"L"``, ``"T"``.
        loop_num:   Integer loop number (e.g. 101).
    """
    u, v, data = pipe_edge
    size = data["size"]
    spec = data["spec"]

    cv_id = f"{variable}V_{loop_num:03d}"
    tx_id = f"{variable}T_{loop_num:03d}"
    ctl_id = f"{variable}IC_{loop_num:03d}"

    G.remove_edge(u, v)

    G.add_node(cv_id, type="valve", class_id=3, size=size, tag=f"{variable}V-{loop_num}", loop=loop_num)
    G.add_node(
        tx_id, type="instrument", class_id=_tx_class(variable), size=size, tag=f"{variable}T-{loop_num}", loop=loop_num
    )
    G.add_node(
        ctl_id,
        type="instrument",
        class_id=_ctl_class(variable),
        size=size,
        tag=f"{variable}IC-{loop_num}",
        loop=loop_num,
    )

    pipe_tag_cv_in = build_pipe_tag(size, spec, 900 + loop_num)
    pipe_tag_cv_out = build_pipe_tag(size, spec, 901 + loop_num)

    G.add_edge(u, cv_id, size=size, spec=spec, type="process", tag=pipe_tag_cv_in)
    G.add_edge(cv_id, v, size=size, spec=spec, type="process", tag=pipe_tag_cv_out)
    G.add_edge(tx_id, ctl_id, type="signal_electric")
    G.add_edge(ctl_id, cv_id, type="signal_electric")
