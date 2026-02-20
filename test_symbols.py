#!/usr/bin/env python
"""Test the symbol loader."""

import sys
sys.path.insert(0, '.')

print("Starting test...", flush=True)

try:
    from pid_generator.symbols_loader import get_registry
    print("Imported get_registry", flush=True)

    reg = get_registry('isa')
    print(f"Loaded {len(reg.symbols)} symbols", flush=True)

    categories = reg.list_categories()
    print(f"Categories: {categories[:3]}", flush=True)

    # Test getting a symbol by class ID
    symbols_for_4 = reg.get_symbols_by_class_id(4)
    print(f"Found {len(symbols_for_4)} symbols for class ID 4", flush=True)

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()

