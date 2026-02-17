"""Random topology generators for P&ID graphs (§31)."""

import random

import networkx as nx

from pid_generator.constants import ALL_CLASS_IDS, PIPE_SIZES, PIPE_SPEC_CODES, _type_from_class


def create_random_topology(
    min_nodes: int = 6,
    max_nodes: int = 20,
    edge_prob: float = 0.3,
) -> nx.DiGraph:
    """Build a purely random Erdős–Rényi directed graph (§31, Level 1).

    No domain constraints are applied — size and spec are random draws.
    Useful for maximum visual diversity before engineering rules are needed.

    Args:
        min_nodes: Minimum number of nodes (inclusive).
        max_nodes: Maximum number of nodes (inclusive).
        edge_prob: Probability of an edge between any node pair.

    Returns:
        A directed graph with node/edge attributes set.
    """
    n = random.randint(min_nodes, max_nodes)
    ug = nx.erdos_renyi_graph(n, edge_prob, seed=None)
    G = nx.DiGraph(ug)

    for i, node in enumerate(G.nodes()):
        cid = random.choice(ALL_CLASS_IDS)
        G.nodes[node].update(
            {
                "id": f"NODE_{i:03d}",
                "class_id": cid,
                "type": _type_from_class(cid),
                "size": random.choice(PIPE_SIZES),
                "tag": f"SYM-{i:03d}",
            }
        )

    for u, v in G.edges():
        G[u][v].update(
            {
                "size": random.choice(PIPE_SIZES),
                "spec": random.choice(PIPE_SPEC_CODES),
                "type": "process",
            }
        )

    return G


def create_balanced_random_topology(n_nodes: int = 42) -> nx.DiGraph:
    """Build a graph with at least one node per class ID (§31, stratified draw).

    Guarantees class balance: class IDs 0–41 are shuffled and assigned
    sequentially so every class appears at least once (up to ``n_nodes``).

    Args:
        n_nodes: Number of nodes to create (capped at 42 for full coverage).

    Returns:
        A directed graph with balanced class distribution.
    """
    G = nx.DiGraph()
    cids = list(range(42))
    random.shuffle(cids)

    for i, cid in enumerate(cids[:n_nodes]):
        G.add_node(i, class_id=cid, type=_type_from_class(cid), size=random.choice(PIPE_SIZES), tag=f"SYM-{i:03d}")

    nodes = list(G.nodes())
    for u in nodes:
        for v in nodes:
            if u != v and random.random() < 0.15:
                G.add_edge(u, v, size=random.choice(PIPE_SIZES), spec=random.choice(PIPE_SPEC_CODES), type="process")
    return G
