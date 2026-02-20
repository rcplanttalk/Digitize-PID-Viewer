"""Quick diagnostic of symbol loading - writes to file."""
import json
from pathlib import Path

output = []

symbols_base = Path(__file__).parent / "symbols"
registry_path = symbols_base / "registry.json"

output.append(f"Checking if registry exists: {registry_path.exists()}")
output.append(f"Registry path: {registry_path}")

if registry_path.exists():
    output.append(f"File size: {registry_path.stat().st_size} bytes")
    try:
        with open(registry_path, 'r') as f:
            data = json.load(f)
            output.append(f"Successfully loaded JSON")
            output.append(f"Total symbols: {data.get('total_symbols')}")
            output.append(f"Symbols in list: {len(data.get('symbols', []))}")

            # Filter ISA symbols
            isa_symbols = [s for s in data.get('symbols', []) if s.get('standard', '').lower() == 'isa']
            output.append(f"ISA symbols: {len(isa_symbols)}")

            if isa_symbols:
                sym = isa_symbols[0]
                output.append(f"\nFirst ISA symbol:")
                output.append(f"  ID: {sym.get('id')}")
                output.append(f"  Category: {sym.get('category')}")
                output.append(f"  Filename: {sym.get('filename')}")
    except Exception as e:
        output.append(f"Error loading registry: {e}")
        import traceback
        output.append(traceback.format_exc())
else:
    output.append("Registry file not found!")
    output.append(f"Available in symbols dir: {list((symbols_base).glob('*'))[:10]}")

# Write to file
with open("test_diagnostic.txt", "w") as f:
    f.write("\n".join(output))

print("Diagnostic written to test_diagnostic.txt")

