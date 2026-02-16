from pid_generator.graph_builder import create_logical_system
from pid_generator.validator import validate_pid_logic
from pid_generator.serialiser import export_graph


def main():
    G = create_logical_system(seed=42)
    errors = validate_pid_logic(G)

    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"Validation: {errors or 'OK'}")

    export_graph(G, "output/pid_0001_graph.json")
    print("Graph exported -> output/pid_0001_graph.json")


if __name__ == "__main__":
    main()
