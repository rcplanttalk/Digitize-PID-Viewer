"""Test PID generation with SVG symbols."""
import sys
import os
sys.path.insert(0, '.')

# Redirect output
output_log = []

try:
    output_log.append("Starting PID generation test...")

    from pid_generator.graph_builder import create_logical_system
    from pid_generator.layout import assign_grid_positions
    from pid_generator.renderer import render_diagram
    from pid_generator.title_block import generate_title_block_metadata
    from pid_generator.constants import CANVAS_H, CANVAS_W, MARGIN, TITLE_BLOCK_H, TITLE_BLOCK_W

    output_log.append("Imported modules successfully")

    # Create a small test graph
    G = create_logical_system(seed=42, n_nodes=5)
    output_log.append(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

    # Generate metadata
    metadata = generate_title_block_metadata(idx=1, seed=42)
    output_log.append("Generated title block metadata")

    # Assign positions
    position = metadata.get("position", "bottom")
    x_right_fraction = TITLE_BLOCK_W / (CANVAS_W - 2 * MARGIN) if position == "right" else 0.0
    y_bottom_fraction = TITLE_BLOCK_H / (CANVAS_H - 2 * MARGIN) if position == "bottom" else 0.0
    pos = assign_grid_positions(G, x_right_fraction=x_right_fraction, y_bottom_fraction=y_bottom_fraction)
    output_log.append(f"Assigned positions to {len(pos)} nodes")

    # Create output directory
    os.makedirs("output/test_svg", exist_ok=True)

    # Render diagram
    output_log.append("Rendering diagram with SVG symbols...")
    img = render_diagram(G, pos, "output/test_svg/pid_test_001.png", metadata=metadata,
                        apply_noise=False, idx=1, seed=42, crossing_style="hop")
    output_log.append(f"Successfully rendered diagram: {img.size}")
    output_log.append("✓ PID generation with SVG symbols PASSED!")

except Exception as e:
    output_log.append(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    output_log.append(traceback.format_exc())

# Write results to file
with open("test_generation_result.txt", "w") as f:
    f.write("\n".join(output_log))

# Also try to print
print("\n".join(output_log))

