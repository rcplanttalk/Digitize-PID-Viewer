from pid_generator.graph_builder import create_logical_system
from pid_generator.validator import validate_pid_logic
from pid_generator.serialiser import export_graph
from pid_generator.layout import assign_grid_positions, to_pixel, snap_to_grid


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

    # Export graph (includes pos attributes written by assign_grid_positions)
    export_graph(G, "output/pid_0001_graph.json")
    print("\nGraph exported -> output/pid_0001_graph.json")


if __name__ == "__main__":
    main()
