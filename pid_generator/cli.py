"""Command-line interface for the P&ID synthetic data generator.

Usage
-----
pid-gen generate [options]   - batch-generate N diagrams into a YOLO dataset
pid-gen single   [options]   - render one diagram; auto-increments output index

Examples:
--------
    pid-gen generate --n 100 --output output/dataset/ --seed 42
    pid-gen generate --n 50  --topology random --no-noise
    pid-gen single   --output output/single/ --seed 7
    pid-gen single   --output output/single/ --no-noise
"""

from __future__ import annotations

import argparse
import logging
import os
import random

logger = logging.getLogger(__name__)


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

    base_seed = args.seed if args.seed is not None else random.randint(0, 0xFFFF_FFFF)
    logger.info("Generating %d diagram(s) -> %s", args.n, os.path.normpath(args.output))
    logger.info("  topology=%s  noise=%s  seed=%s", args.topology, args.noise, base_seed)

    manifest = generate_dataset(
        n=args.n,
        dataset_root=args.output,
        base_seed=base_seed,
        topology=args.topology,
        apply_noise=args.noise,
        n_nodes=args.nodes,
        crossing_style=args.crossing_style,
    )
    logger.info("Done. Manifest ->%s", manifest)


def cmd_single(args: argparse.Namespace) -> None:
    """Render one diagram; automatically increments the output index."""
    from pid_generator.constants import CANVAS_H, CANVAS_W, MARGIN, TITLE_BLOCK_H, TITLE_BLOCK_W
    from pid_generator.graph_builder import create_logical_system
    from pid_generator.layout import assign_grid_positions
    from pid_generator.renderer import render_diagram
    from pid_generator.serialiser import export_graph, graph_filename
    from pid_generator.title_block import generate_title_block_metadata
    from pid_generator.validator import validate_pid_logic
    from pid_generator.yolo import export_yolo_labels, image_filename, label_filename

    seed = args.seed if args.seed is not None else random.randint(0, 0xFFFF_FFFF)

    os.makedirs(args.output, exist_ok=True)
    idx = _next_index(args.output)

    G      = create_logical_system(seed=seed, n_nodes=args.nodes)
    errors = validate_pid_logic(G)
    if errors:
        for e in errors:
            logger.warning("  [validation] %s", e)

    metadata = generate_title_block_metadata(idx=idx, seed=seed)
    position = metadata.get("position", "bottom")
    x_right_fraction  = TITLE_BLOCK_W / (CANVAS_W - 2 * MARGIN) if position == "right"  else 0.0
    y_bottom_fraction = TITLE_BLOCK_H / (CANVAS_H - 2 * MARGIN) if position == "bottom" else 0.0
    pos      = assign_grid_positions(G, x_right_fraction=x_right_fraction, y_bottom_fraction=y_bottom_fraction)
    img_path = os.path.join(args.output, image_filename(idx))
    lbl_path = os.path.join(args.output, label_filename(idx))
    grp_path = os.path.join(args.output, graph_filename(idx))

    render_diagram(G, pos, img_path, metadata=metadata, apply_noise=args.noise, idx=idx, seed=seed,
                   crossing_style=args.crossing_style)
    export_yolo_labels(G, pos, lbl_path)
    export_graph(G, grp_path)

    logger.info("Diagram #%04d", idx)
    logger.info("  image   -> %s", img_path)
    logger.info("  labels  -> %s", lbl_path)
    logger.info("  graph   -> %s", grp_path)
    logger.info("  seed=%s", seed)
    logger.info("  nodes=%s  edges=%s", G.number_of_nodes(), G.number_of_edges())
    logger.info("  validation: %s", errors or "OK")


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="pid-gen",
        description="Synthetic P&ID diagram generator for YOLO training data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate subcommand
    gen = sub.add_parser("generate", help="Batch-generate N diagrams into a dataset folder.")
    gen.add_argument("--n",        type=int,  default=10,        metavar="N",
                     help="Number of diagrams to generate (default: 10).")
    gen.add_argument("--output",   type=str,  default="output/dataset",
                     help="Output root directory (default: output/dataset/).")
    gen.add_argument("--seed",     type=int,  default=None,
                     help="Base RNG seed; each diagram uses seed+idx (default: random).")
    gen.add_argument("--topology", choices=["logical", "random"], default="logical",
                     help="Graph topology mode (default: logical).")
    gen.add_argument("--noise",    action=argparse.BooleanOptionalAction, default=True,
                     help="Apply Stage 9 noise augmentations (default: --noise).")
    gen.add_argument("--nodes",    type=int,  default=None,
                     help="Target node count per diagram (default: random 10-50).")
    gen.add_argument("--crossing-style", choices=["hop", "color_change"], default=None,
                     dest="crossing_style",
                     help="Pipe crossing style: 'hop' (arc) or 'color_change' (red highlight). Default: random per diagram.")

    # single subcommand
    sng = sub.add_parser("single", help="Render one diagram; auto-increments output index.")
    sng.add_argument("--output", type=str, default="output/single",
                     help="Output directory (default: output/single/).")
    sng.add_argument("--seed",   type=int, default=None,
                     help="RNG seed (default: random).")
    sng.add_argument("--noise",  action=argparse.BooleanOptionalAction, default=False,
                     help="Apply Stage 9 noise augmentations (default: --no-noise).")
    sng.add_argument("--nodes",  type=int, default=None,
                     help="Target node count (default: random 10-50).")
    sng.add_argument("--crossing-style", choices=["hop", "color_change"], default=None,
                     dest="crossing_style",
                     help="Pipe crossing style: 'hop' (arc) or 'color_change' (red highlight). Default: random.")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and execute the requested command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    parser = build_parser()
    args   = parser.parse_args(argv)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "single":
        cmd_single(args)


if __name__ == "__main__":
    main()
