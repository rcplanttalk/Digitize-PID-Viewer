"""Logical P&ID graph builder (§6, §24).

Builds a domain-constrained ``nx.DiGraph`` representing a simple pump-to-tank
process system with a control loop.
"""

import random

import networkx as nx

from pid_generator.constants import PIPE_SPEC_CODES
from pid_generator.tags import build_component_tag, build_pipe_tag

# ---------------------------------------------------------------------------
# Instrument class IDs per measurement variable (§11.2)
# ---------------------------------------------------------------------------

_TX_CLASS: dict[str, int] = {
    "P": 12,  # Pressure Transmitter
    "T": 15,  # Temperature Transmitter
    "F": 17,  # Flow Transmitter
    "L": 20,  # Level Transmitter
}

_CTL_CLASS: dict[str, int] = {
    "P": 14,  # Pressure Controller
    "T": 15,  # Temperature Controller (TIC shares TT class_id in §11.2; use 15 for TT, use 14 placeholder)
    "F": 19,  # Flow Controller
    "L": 22,  # Level Controller
}


def _tx_class(variable: str) -> int:
    return _TX_CLASS.get(variable, 12)


def _ctl_class(variable: str) -> int:
    return _CTL_CLASS.get(variable, 14)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_logical_system(seed: int | None = None) -> nx.DiGraph:
    """Build a validated process graph: PUMP → isolation valve → strainer → tank.

    The graph follows the process logic rules in §5:
    - Isolation valves on pump inlet and outlet.
    - Check valve on pump discharge.
    - Strainer upstream of control valve.
    - One control loop (Flow) inserted on the main process line.

    Args:
        seed: Optional random seed for reproducibility.

    Returns:
        A directed graph (``nx.DiGraph``) with fully attributed nodes and edges.
    """
    if seed is not None:
        random.seed(seed)

    G = nx.DiGraph()
    spec = random.choice(PIPE_SPEC_CODES)
    size = 8  # main line size

    # -----------------------------------------------------------------------
    # Nodes
    # -----------------------------------------------------------------------
    # Off-page connector — feed inlet from upstream sheet
    G.add_node(
        "OPC_IN_01",
        type="off_page",
        direction="in",
        class_id=38,
        size=size,
        tag="OPC-IN-001",
        ref_sheet=0,
        ref_line="FEED",
    )

    G.add_node("PUMP_01", type="equipment", class_id=24, size=size, tag=build_component_tag("P", 101))

    # Inlet isolation valve (gate valve, class_id=4)
    G.add_node("GV_IN_01", type="valve", class_id=4, size=size, tag=build_component_tag("GV", 1))

    # Outlet isolation valve (gate valve, class_id=4)
    G.add_node("GV_OUT_01", type="valve", class_id=4, size=size, tag=build_component_tag("GV", 2))

    # Check valve on discharge (class_id=2)
    G.add_node("CK_01", type="valve", class_id=2, size=size, tag=build_component_tag("CK", 1))

    # Strainer upstream of control valve (class_id=34)
    G.add_node("STR_01", type="fitting", class_id=34, size=size, tag=build_component_tag("GV", 3))

    # Destination tank (storage tank, class_id=30)
    G.add_node("TANK_01", type="equipment", class_id=30, size=size, tag=build_component_tag("T", 101))

    # -----------------------------------------------------------------------
    # Edges (process flow direction: inlet → pump → discharge → tank)
    # -----------------------------------------------------------------------
    pipe_seq = 1

    def _pe(u: str, v: str) -> dict:
        nonlocal pipe_seq
        tag = build_pipe_tag(size, spec, pipe_seq)
        pipe_seq += 1
        return {"size": size, "spec": spec, "type": "process", "tag": tag}

    G.add_edge("OPC_IN_01", "GV_IN_01", **_pe("OPC_IN_01", "GV_IN_01"))
    G.add_edge("GV_IN_01", "PUMP_01", **_pe("GV_IN_01", "PUMP_01"))
    G.add_edge("PUMP_01", "GV_OUT_01", **_pe("PUMP_01", "GV_OUT_01"))
    G.add_edge("GV_OUT_01", "CK_01", **_pe("GV_OUT_01", "CK_01"))
    G.add_edge("CK_01", "STR_01", **_pe("CK_01", "STR_01"))

    # The STR_01 → TANK_01 edge will be split by the control loop below.
    G.add_edge("STR_01", "TANK_01", **_pe("STR_01", "TANK_01"))

    # -----------------------------------------------------------------------
    # Control loop on the strainer → tank pipe (flow measurement)
    # -----------------------------------------------------------------------
    pipe_edge = ("STR_01", "TANK_01", G["STR_01"]["TANK_01"])
    add_control_loop(G, pipe_edge, variable="F", loop_num=101)

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
