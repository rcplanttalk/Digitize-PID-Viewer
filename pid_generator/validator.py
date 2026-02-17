"""P&ID graph validator — E001–E008, W001–W004 (§28)."""

import networkx as nx

from pid_generator.constants import PIPE_SIZES, PIPE_SPEC_CODES


def validate_pid_logic(G: nx.DiGraph) -> list[str]:
    """Validate a P&ID graph against domain rules.

    Checks errors (E001–E008) and warnings (W001–W004) defined in §28.

    Args:
        G: A directed graph produced by the graph builder.

    Returns:
        A list of error/warning strings. An empty list means the graph is valid.
    """
    issues: list[str] = []

    # -----------------------------------------------------------------------
    # Node-level checks
    # -----------------------------------------------------------------------
    for node, data in G.nodes(data=True):
        cid = data.get("class_id")
        ntype = data.get("type", "")

        # E001 — Check valve must have exactly one input
        if cid == 2 and G.in_degree(node) != 1:
            issues.append(
                f"E001: Check valve '{node}' has in_degree={G.in_degree(node)} (expected 1)",
            )

        # E002 — Pump must have in=1, out=1
        if ntype == "equipment" and cid in (24, 25) and (G.in_degree(node) != 1 or G.out_degree(node) != 1):
            issues.append(
                f"E002: Pump '{node}' degree constraint violated (in={G.in_degree(node)}, out={G.out_degree(node)})",
            )

        # E005 — Node size must match all connected process-pipe sizes (unless
        #         a reducer sits between them — we check only direct neighbours)
        node_size = data.get("size")
        if node_size is not None:
            for nbr in list(G.predecessors(node)) + list(G.successors(node)):
                # Get edge data; direction may vary
                edata = G[nbr][node] if G.has_edge(nbr, node) else G[node][nbr]
                edge_size = edata.get("size")
                edge_type = edata.get("type", "process")
                if edge_type == "process" and edge_size is not None and edge_size != node_size:
                    # Only flag if neither endpoint is a reducer (class_id 32/33)
                    nbr_cid = G.nodes[nbr].get("class_id")
                    if nbr_cid not in (32, 33) and cid not in (32, 33):
                        issues.append(
                            f"E005: Node '{node}' size={node_size} mismatches "
                            f"edge to '{nbr}' size={edge_size} (no reducer present)",
                        )

        # E006 — Control valve (class_id=3 or type='control_valve') needs a signal edge
        if cid == 3 or ntype == "control_valve":
            in_signal = any(
                G[u][node].get("type") in ("signal_electric", "signal_pneumatic", "signal_hydraulic")
                for u in G.predecessors(node)
            )
            if not in_signal:
                issues.append(
                    f"E006: Control valve '{node}' has no incoming signal line",
                )

        # W001 — Dangling valve (in_degree=0 or out_degree=0)
        # §28 specifies this check for valves only.
        if ntype == "valve" and (G.in_degree(node) == 0 or G.out_degree(node) == 0):
            issues.append(
                f"W001: valve '{node}' is dangling (in={G.in_degree(node)}, out={G.out_degree(node)})",
            )

    # -----------------------------------------------------------------------
    # Edge-level checks
    # -----------------------------------------------------------------------
    for u, v, edata in G.edges(data=True):
        edge_size = edata.get("size")
        edge_spec = edata.get("spec")

        # E003 — Edge size must be in PIPE_SIZES
        if edge_size is not None and edge_size not in PIPE_SIZES:
            issues.append(
                f"E003: Edge ('{u}'→'{v}') invalid size={edge_size}",
            )

        # E004 — Edge spec must be in PIPE_SPEC_CODES (only process pipes carry spec)
        if edata.get("type") == "process" and edge_spec is not None and edge_spec not in PIPE_SPEC_CODES:
            issues.append(
                f"E004: Edge ('{u}'→'{v}') invalid spec='{edge_spec}'",
            )

    # -----------------------------------------------------------------------
    # Graph-level checks
    # -----------------------------------------------------------------------

    # E007 — Graph must have at least one source (in_degree=0 non-off-page node)
    non_off_page = [n for n, d in G.nodes(data=True) if d.get("type") != "off_page"]
    sources = [n for n in non_off_page if G.in_degree(n) == 0]
    if not sources:
        issues.append("E007: Graph has no source node (no node with in_degree=0)")

    # E008 — Graph must have at least one sink (out_degree=0 non-off-page node)
    sinks = [n for n in non_off_page if G.out_degree(n) == 0]
    if not sinks:
        issues.append("E008: Graph has no sink node (no node with out_degree=0)")

    # W003 — Control loop members missing 'loop' attribute
    loop_nodes = [n for n, d in G.nodes(data=True) if d.get("class_id") == 3 or d.get("type") == "control_valve"]
    for cv in loop_nodes:
        if G.nodes[cv].get("loop") is None:
            issues.append(f"W003: Control valve '{cv}' missing 'loop' attribute")

    # W004 — Relief valve (class_id=8) outlet not connected to flare/vent
    for node, data in G.nodes(data=True):
        if data.get("class_id") == 8:
            successors = list(G.successors(node))
            has_flare = any(G.nodes[s].get("type") in ("off_page", "flare", "vent") for s in successors)
            if not has_flare:
                issues.append(
                    f"W004: Relief valve '{node}' outlet not connected to flare/vent",
                )

    return issues
