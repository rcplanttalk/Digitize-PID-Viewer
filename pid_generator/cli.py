"""Command-line interface for the P&ID synthetic data generator.

Usage
-----
pid-gen generate [options]   — batch-generate N diagrams into a YOLO dataset
pid-gen single   [options]   — render one diagram; auto-increments output index

Examples
--------
    pid-gen generate --n 100 --output dataset/ --seed 42
    pid-gen generate --n 50  --topology random --no-noise
    pid-gen single   --output output/ --seed 7
    pid-gen single   --output output/ --no-noise
"""

from __future__ import annotations

import argparse
import os
import sys


def _next_index(directory: str, prefix: str = "pid_", ext: str = ".png") -> int:
    """Return the next available 1-based file index in *directory*.

    Scans for existing ``{prefix}NNNN{ext}`` files and returns max+1 so
    repeated calls to ``single`` never overwrite previous outputs.
    """
    if not os.path.isdir(directory):
        return 1
    indices = []
    for name in os.listdir(directory):
        if name.startswith(prefix) and name.endswith(ext):
            stem = name[len(prefix):-len(ext)]
            if stem.isdigit():
                indices.append(int(stem))
    return max(indices, default=0) + 1


def cmd_generate(args: argparse.Namespace) -> None:
    """Batch-generate N diagrams into a YOLO dataset folder."""
    from pid_generator.batch import generate_dataset

    print(f"Generating {args.n} diagram(s) -> {os.path.normpath(args.output)}")
    print(f"  topology={args.topology}  noise={args.noise}  seed={args.seed}")

    manifest = generate_dataset(
        n=args.n,
        dataset_root=args.output,
        base_seed=args.seed,
        topology=args.topology,
        apply_noise=args.noise,
    )
    print(f"Done. Manifest ->{manifest}")


def cmd_single(args: argparse.Namespace) -> None:
    """Render one diagram; automatically increments the output index."""
    from pid_generator.graph_builder import create_logical_system
    from pid_generator.layout import assign_grid_positions
    from pid_generator.renderer import render_diagram
    from pid_generator.serialiser import export_graph
    from pid_generator.validator import validate_pid_logic
    from pid_generator.yolo import export_yolo_labels, image_filename, label_filename
    from pid_generator.serialiser import graph_filename

    os.makedirs(args.output, exist_ok=True)
    idx = _next_index(args.output)

    G      = create_logical_system(seed=args.seed)
    errors = validate_pid_logic(G)
    if errors:
        for e in errors:
            print(f"  [validation] {e}", file=sys.stderr)

    pos      = assign_grid_positions(G)
    img_path = os.path.join(args.output, image_filename(idx))
    lbl_path = os.path.join(args.output, label_filename(idx))
    grp_path = os.path.join(args.output, graph_filename(idx))

    render_diagram(G, pos, img_path, apply_noise=args.noise, idx=idx, seed=args.seed)
    export_yolo_labels(G, pos, lbl_path)
    export_graph(G, grp_path)

    print(f"Diagram #{idx:04d}")
    print(f"  image   -> {img_path}")
    print(f"  labels  -> {lbl_path}")
    print(f"  graph   -> {grp_path}")
    print(f"  nodes={G.number_of_nodes()}  edges={G.number_of_edges()}")
    print(f"  validation: {errors or 'OK'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pid-gen",
        description="Synthetic P&ID diagram generator for YOLO training data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate subcommand
    gen = sub.add_parser("generate", help="Batch-generate N diagrams into a dataset folder.")
    gen.add_argument("--n",        type=int,  default=10,        metavar="N",
                     help="Number of diagrams to generate (default: 10).")
    gen.add_argument("--output",   type=str,  default="dataset",
                     help="Output root directory (default: dataset/).")
    gen.add_argument("--seed",     type=int,  default=42,
                     help="Base RNG seed; each diagram uses seed+idx (default: 42).")
    gen.add_argument("--topology", choices=["logical", "random"], default="logical",
                     help="Graph topology mode (default: logical).")
    gen.add_argument("--noise",    action=argparse.BooleanOptionalAction, default=True,
                     help="Apply Stage 9 noise augmentations (default: --noise).")

    # single subcommand
    sng = sub.add_parser("single", help="Render one diagram; auto-increments output index.")
    sng.add_argument("--output", type=str, default="output",
                     help="Output directory (default: output/).")
    sng.add_argument("--seed",   type=int, default=42,
                     help="RNG seed (default: 42).")
    sng.add_argument("--noise",  action=argparse.BooleanOptionalAction, default=False,
                     help="Apply Stage 9 noise augmentations (default: --no-noise).")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args   = parser.parse_args(argv)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "single":
        cmd_single(args)
