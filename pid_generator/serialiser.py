"""Graph serialisation and deserialisation utilities (§32)."""

import json
import os

import networkx as nx
from networkx.readwrite import node_link_data, node_link_graph


def export_graph(G: nx.DiGraph, out_path: str) -> None:
    """Serialise *G* to a JSON file using NetworkX node-link format (§32).

    The parent directory is created automatically if it does not exist.

    Args:
        G:        The directed graph to serialise.
        out_path: Destination file path (e.g. ``'output/pid_0001_graph.json'``).
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    data = node_link_data(G)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_graph(path: str) -> nx.DiGraph:
    """Deserialise a graph from a JSON file produced by :func:`export_graph` (§32).

    Args:
        path: Path to the ``_graph.json`` file.

    Returns:
        A directed, non-multigraph ``nx.DiGraph``.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return node_link_graph(data, directed=True, multigraph=False)


def graph_filename(idx: int) -> str:
    """Return the canonical graph JSON filename for diagram index *idx* (§32).

    Args:
        idx: Diagram index (1-based).

    Returns:
        Filename string, e.g. ``'pid_0001_graph.json'``.
    """
    return f"pid_{idx:04d}_graph.json"
