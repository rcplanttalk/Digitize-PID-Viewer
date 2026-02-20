## ISA Symbol Integration - User Guide

### Overview

The P&ID generator now renders actual ISA standardized symbols instead of simple placeholder boxes. Symbols are automatically loaded from the `symbols/registry.json` file and matched to nodes based on their class_id.

### Quick Start

The integration happens automatically when you generate diagrams:

```bash
# Generate a diagram with ISA symbols (automatic)
uv run python main.py single --output output/test --nodes 10

# Generate a batch with ISA symbols
uv run python main.py generate --n 5 --output output/dataset

# Diagrams now render with real ISA symbols!
```

### How It Works

1. **Symbol Loading**:
   - The `SymbolRegistry` class loads `symbols/registry.json` at diagram render time
   - Only ISA symbols are loaded by default (944+ symbols available)
   - Symbols are indexed by class_id for fast lookup

2. **Symbol Selection**:
   - Each node has a `class_id` attribute (0-41)
   - The renderer queries the registry for symbols matching that class_id
   - First available symbol is selected

3. **Rendering**:
   - SVG files are converted to PIL Images using cairosvg
   - Symbols are scaled to fit SYMBOL_BOX (64px) scaled by DPI
   - Rendered symbols preserve their aspect ratio

### Supported ISA Categories

The following ISA component categories are supported with their class_id mappings:

| Class ID | Category | Examples |
|----------|----------|----------|
| 4-11 | Valves | Gate, Globe, Ball, Check, Relief, Control, etc. |
| 12-23 | Instruments | Transmitters, Controllers, Indicators |
| 26-31 | Equipment | Heat exchangers, Separators, Tanks, Pumps |
| 32-41 | Fittings | Actuators, Safety, Logic, Accessories, Connections |

### Customization

#### Using a Different Symbol Standard

To use DIN 19227 symbols instead of ISA:

```python
# In renderer.py, modify the render_diagram() call:
render_symbol_placeholders(img, draw, G, pos, dpi_scale=dpi_scale, standard="din_19227")
```

Available standards in `symbols/` folder:
- `isa` (944 symbols) - Default
- `din_19227` 
- `iso_10628_2`
- `din_2429`
- `pip`
- `unknown`

#### Adding New Symbol Standards

1. Place SVG files in `symbols/{standard_name}/{category}/`
2. Add entries to `symbols/registry.json` with `"standard": "{standard_name}"`
3. Update class_id mapping in `symbols_loader.py`'s `_extract_class_id()` method

#### Symbol Size Adjustment

Modify `SYMBOL_BOX` constant in `pid_generator/constants.py`:

```python
SYMBOL_BOX: int = 64   # Current: 64px, increase for larger symbols
```

### Troubleshooting

#### "SVG file not found" warnings

This means the registry has a symbol entry but the SVG file is missing.

**Solution**: Verify the SVG file exists in the correct category folder:
```
symbols/isa/{category}/{filename}.svg
```

#### Symbols not rendering (showing colored boxes instead)

This can happen if:

1. **cairosvg not installed**: 
   ```bash
   uv sync  # Reinstall dependencies
   ```

2. **Invalid SVG file**:
   - Check the SVG is valid XML
   - Verify it has width/height attributes or viewBox

3. **Registry loading failed**:
   - Check `symbols/registry.json` is valid JSON
   - Verify the file is readable

#### Very small or distorted symbols

**Adjust DPI or SYMBOL_BOX**:
- Symbols scale proportionally with DPI (72-300)
- Increase `SYMBOL_BOX` constant for larger base size
- SVG aspect ratio is always preserved

### Performance Notes

- Symbol registry loads once at first render, then cached
- SVG rendering happens per-node at render time
- For large diagrams (50+ nodes), this may take a few seconds
- Consider reducing node count for interactive testing

### Advanced: Symbol Registry API

```python
from pid_generator.symbols_loader import get_registry

# Get the ISA symbol registry
registry = get_registry('isa')

# List all categories
categories = registry.list_categories()
print(categories)  # ['actuator', 'annotation', 'connection', ...]

# Find symbols for a class_id
symbols = registry.get_symbols_by_class_id(4)  # All valve symbols
print(f"Found {len(symbols)} symbols for class_id 4")

# Get metadata for a specific symbol
symbol = symbols[0]
print(symbol['display_name'])  # "Aaamatt Staging"
print(symbol['category'])      # "actuator"

# Get the SVG file path
svg_path = registry.get_svg_path(symbol)
print(svg_path)  # .../symbols/isa/actuator/isa_aaamatt_staging.svg

# Registry statistics
stats = registry.get_stats()
print(stats)
# {
#   'total_symbols': 944,
#   'categories': [...],
#   'class_ids': [0, 1, 2, ...]
# }
```

### See Also

- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `pid_generator/symbols_loader.py` - Symbol registry implementation
- `pid_generator/svg_renderer.py` - SVG rendering utilities
- `pid_generator/renderer.py` - Main rendering pipeline
- `symbols/registry.json` - Master symbol registry (944 symbols)

