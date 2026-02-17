from pid_generator.batch import generate_dataset
from pid_generator.graph_builder import create_logical_system
from pid_generator.layout import assign_grid_positions, snap_to_grid, to_pixel
from pid_generator.renderer import render_diagram
from pid_generator.serialiser import export_graph
from pid_generator.validator import validate_pid_logic
from pid_generator.yolo import export_yolo_labels


def main():
    # -----------------------------------------------------------------------
    # Single-diagram demo (Stages 1-10)
    # -----------------------------------------------------------------------
    G = create_logical_system(seed=42)
    _ = validate_pid_logic(G)

    pos = assign_grid_positions(G)
    for _node, (nx_, ny_) in sorted(pos.items()):
        _px, _py = snap_to_grid(*to_pixel(nx_, ny_))

    render_diagram(G, pos, "output/pid_0001.png", apply_noise=False)
    render_diagram(G, pos, "output/pid_0001_noisy.png", apply_noise=True)
    export_yolo_labels(G, pos, "output/pid_0001.txt")
    export_graph(G, "output/pid_0001_graph.json")

    # -----------------------------------------------------------------------
    # Mini batch demo — 5 logical diagrams -> dataset/
    # -----------------------------------------------------------------------
    _ = generate_dataset(
        n=5,
        dataset_root="dataset",
        base_seed=42,
        topology="logical",
        apply_noise=True,
    )


if __name__ == "__main__":
    main()
