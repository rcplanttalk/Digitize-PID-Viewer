from pid_generator.graph_builder import create_logical_system
from pid_generator.validator import validate_pid_logic
from pid_generator.serialiser import export_graph
from pid_generator.layout import assign_grid_positions, to_pixel, snap_to_grid
from pid_generator.renderer import render_diagram
from pid_generator.yolo import export_yolo_labels
from pid_generator.batch import generate_dataset


def main():
    # -----------------------------------------------------------------------
    # Single-diagram demo (Stages 1-10)
    # -----------------------------------------------------------------------
    G = create_logical_system(seed=42)
    errors = validate_pid_logic(G)
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"Validation: {errors or 'OK'}")

    pos = assign_grid_positions(G)
    print("\nNode positions (normalised -> snapped pixels):")
    for node, (nx_, ny_) in sorted(pos.items()):
        px, py = snap_to_grid(*to_pixel(nx_, ny_))
        print(f"  {node:<14} norm=({nx_:.3f}, {ny_:.3f})  px=({px:4d}, {py:4d})")

    render_diagram(G, pos, "output/pid_0001.png", apply_noise=False)
    render_diagram(G, pos, "output/pid_0001_noisy.png", apply_noise=True)
    export_yolo_labels(G, pos, "output/pid_0001.txt")
    export_graph(G, "output/pid_0001_graph.json")

    print("\nSingle diagram outputs:")
    print("  output/pid_0001.png")
    print("  output/pid_0001_noisy.png")
    print("  output/pid_0001.txt  (YOLO labels)")
    print("  output/pid_0001_graph.json")

    # -----------------------------------------------------------------------
    # Mini batch demo — 5 logical diagrams -> dataset/
    # -----------------------------------------------------------------------
    print("\nGenerating mini dataset (5 diagrams) ...")
    manifest = generate_dataset(
        n=5,
        dataset_root="dataset",
        base_seed=42,
        topology="logical",
        apply_noise=True,
    )
    print(f"\nManifest -> {manifest}")
    print("Dataset layout: dataset/images|labels|graphs/{train,val,test}/")
    print("                dataset/data.yaml")


if __name__ == "__main__":
    main()
