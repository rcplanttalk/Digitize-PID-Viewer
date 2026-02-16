from pid_generator.graph_builder import create_logical_system
from pid_generator.validator import validate_pid_logic
from pid_generator.serialiser import export_graph
from pid_generator.layout import assign_grid_positions, to_pixel, snap_to_grid
from pid_generator.renderer import render_diagram


def main():
    # Stage 1 — build
    G = create_logical_system(seed=42)

    # Stage 2 — validate
    errors = validate_pid_logic(G)
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"Validation: {errors or 'OK'}")

    # Stage 3 — layout
    pos = assign_grid_positions(G)
    print("\nNode positions (normalised -> snapped pixels):")
    for node, (nx_, ny_) in sorted(pos.items()):
        px, py = snap_to_grid(*to_pixel(nx_, ny_))
        print(f"  {node:<14} norm=({nx_:.3f}, {ny_:.3f})  px=({px:4d}, {py:4d})")

    # Stages 4-8 — render
    render_diagram(G, pos, "output/pid_0001.png", apply_noise=False)
    print("\nDiagram rendered -> output/pid_0001.png")

    # Noisy variant (Stage 9)
    render_diagram(G, pos, "output/pid_0001_noisy.png", apply_noise=True)
    print("Noisy variant   -> output/pid_0001_noisy.png")

    # Export graph JSON
    export_graph(G, "output/pid_0001_graph.json")
    print("Graph exported  -> output/pid_0001_graph.json")


if __name__ == "__main__":
    main()
