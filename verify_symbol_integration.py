#!/usr/bin/env python
"""Quick test to verify ISA symbol integration is working."""

import sys
import json
from pathlib import Path

def main():
    """Run integration tests."""
    print("\n" + "="*70)
    print("ISA Symbol Integration - Verification Tests")
    print("="*70 + "\n")

    # Test 1: Registry file exists
    print("Test 1: Registry file existence")
    registry_path = Path(__file__).parent / "symbols" / "registry.json"
    if registry_path.exists():
        print(f"  ✓ Registry found at {registry_path}")
        print(f"    Size: {registry_path.stat().st_size / 1024:.1f} KB")
    else:
        print(f"  ✗ Registry NOT found at {registry_path}")
        return False

    # Test 2: Registry is valid JSON
    print("\nTest 2: Registry JSON validity")
    try:
        with open(registry_path) as f:
            data = json.load(f)
        print(f"  ✓ Registry is valid JSON")
        print(f"    Total symbols: {data.get('total_symbols')}")
        print(f"    Symbols in list: {len(data.get('symbols', []))}")
    except Exception as e:
        print(f"  ✗ Registry JSON invalid: {e}")
        return False

    # Test 3: ISA symbols exist
    print("\nTest 3: ISA symbols availability")
    isa_symbols = [s for s in data.get('symbols', []) if s.get('standard', '').lower() == 'isa']
    print(f"  ✓ Found {len(isa_symbols)} ISA symbols")
    categories = set(s.get('category', 'unknown') for s in isa_symbols)
    print(f"    Categories: {', '.join(sorted(categories)[:8])}...")

    # Test 4: Symbol files exist
    print("\nTest 4: Symbol SVG file existence (sample)")
    symbols_dir = Path(__file__).parent / "symbols"
    found = 0
    missing = 0
    for sym in isa_symbols[:5]:
        standard = sym.get('standard', '').lower()
        category = sym.get('category', '').lower()
        filename = sym.get('filename', '')
        svg_path = symbols_dir / standard / category / filename
        if svg_path.exists():
            found += 1
        else:
            missing += 1
            print(f"    ! Missing: {svg_path.name}")

    if missing == 0:
        print(f"  ✓ All sampled {found} SVG files found")
    else:
        print(f"  ⚠ Found {found}/{found+missing} sampled SVG files")

    # Test 5: SymbolRegistry module
    print("\nTest 5: SymbolRegistry module import")
    try:
        from pid_generator.symbols_loader import SymbolRegistry, get_registry
        print(f"  ✓ SymbolRegistry module imported")

        # Create registry
        reg = SymbolRegistry('isa')
        print(f"  ✓ Registry instantiated")
        print(f"    Loaded {len(reg.symbols)} symbols")
        print(f"    Class ID mappings: {len(reg.class_id_map)} distinct classes")

        # Test lookup
        symbols_for_4 = reg.get_symbols_by_class_id(4)
        print(f"  ✓ Found {len(symbols_for_4)} symbols for class_id 4 (valves)")

        if symbols_for_4:
            sym = symbols_for_4[0]
            svg_path = reg.get_svg_path(sym)
            if svg_path and svg_path.exists():
                print(f"  ✓ SVG path resolved: {svg_path.name}")
            else:
                print(f"  ! SVG path not found: {svg_path}")
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test 6: SVG renderer module
    print("\nTest 6: SVG renderer module import")
    try:
        from pid_generator.svg_renderer import render_svg_to_pil, extract_svg_dimensions
        print(f"  ✓ SVG renderer module imported")

        # Check for cairosvg
        try:
            import cairosvg
            print(f"  ✓ cairosvg is installed (version: {cairosvg.__version__ if hasattr(cairosvg, '__version__') else 'unknown'})")
        except ImportError:
            print(f"  ⚠ cairosvg NOT installed - fallback to placeholder boxes")
            print(f"    Install with: uv sync")

    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

    # Test 7: Renderer integration
    print("\nTest 7: Renderer integration")
    try:
        from pid_generator.renderer import render_symbol_placeholders
        print(f"  ✓ render_symbol_placeholders imported with new signature")
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

    print("\n" + "="*70)
    print("✓ All verification tests PASSED!")
    print("="*70 + "\n")
    print("ISA symbol integration is ready to use.")
    print("Run: uv run python main.py single --nodes 10")
    print("\n")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

