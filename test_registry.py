"""Quick diagnostic of symbol loading."""
import json
from pathlib import Path

symbols_base = Path(__file__).parent / "symbols"
registry_path = symbols_base / "registry.json"

print(f"Checking if registry exists: {registry_path.exists()}")
print(f"Registry path: {registry_path}")

if registry_path.exists():
    print(f"File size: {registry_path.stat().st_size} bytes")
    try:
        with open(registry_path, 'r') as f:
            data = json.load(f)
            print(f"Successfully loaded JSON")
            print(f"Total symbols: {data.get('total_symbols')}")
            print(f"Symbols in list: {len(data.get('symbols', []))}")

            # Filter ISA symbols
            isa_symbols = [s for s in data.get('symbols', []) if s.get('standard', '').lower() == 'isa']
            print(f"ISA symbols: {len(isa_symbols)}")

            if isa_symbols:
                sym = isa_symbols[0]
                print(f"\nFirst ISA symbol:")
                print(f"  ID: {sym.get('id')}")
                print(f"  Category: {sym.get('category')}")
                print(f"  Filename: {sym.get('filename')}")
    except Exception as e:
        print(f"Error loading registry: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Registry file not found!")
    print(f"Available in symbols dir: {list((symbols_base).glob('*'))[:10]}")

