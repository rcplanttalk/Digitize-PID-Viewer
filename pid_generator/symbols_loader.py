"""Symbol loading and management module for P&ID generation.

This module provides utilities to load symbol metadata from JSON files and
map class IDs to actual SVG symbol files from the symbols registry.
"""

import json
from pathlib import Path
from typing import Any

# Get the base path for symbols (relative to this file)
_SYMBOLS_BASE = Path(__file__).parent.parent / "symbols"
_REGISTRY_PATH = _SYMBOLS_BASE / "registry.json"


class SymbolRegistry:
    """Load and manage P&ID symbols from the symbols folder."""

    def __init__(self, standard: str = "isa"):
        """Initialize the symbol registry.

        Args:
            standard: The symbol standard to load (e.g., "isa", "din_19227").
        """
        self.standard = standard.lower()
        self.symbols: dict[str, dict[str, Any]] = {}
        self.class_id_map: dict[int, list[dict[str, Any]]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load the registry.json file and build lookup maps."""
        if not _REGISTRY_PATH.exists():
            print(f"Warning: Registry file not found at {_REGISTRY_PATH}")
            return

        try:
            with open(_REGISTRY_PATH, "r") as f:
                data = json.load(f)
                symbols = data.get("symbols", [])

                for symbol in symbols:
                    # Only load symbols for the selected standard
                    if symbol.get("standard", "").lower() != self.standard:
                        continue

                    symbol_id = symbol.get("id", "")
                    if symbol_id:
                        self.symbols[symbol_id] = symbol

                        # Build class_id map for quick lookup by class ID
                        # Try to extract a class ID from tags or metadata
                        class_id = self._extract_class_id(symbol)
                        if class_id is not None:
                            if class_id not in self.class_id_map:
                                self.class_id_map[class_id] = []
                            self.class_id_map[class_id].append(symbol)

        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading registry: {e}")

    def _extract_class_id(self, symbol: dict[str, Any]) -> int | None:
        """Extract a class ID from symbol metadata (heuristic).

        This is a placeholder. Ideally, symbols should have explicit class_id
        in their metadata. For now, we map by category.
        """
        category = symbol.get("category", "").lower()

        # Rough mapping from ISA categories to class IDs
        category_map = {
            "valve": 4,  # Isolation valve (arbitrary)
            "actuator": 32,  # Actuator (fitting)
            "instrument_bubble": 12,  # Instrument (transmitter)
            "equipment": 26,  # Equipment (heat exchanger)
            "regulator": 10,  # Regulator valve
            "relief_valve": 9,  # Relief valve
            "control_valve": 5,  # Control valve
            "primary_element": 17,  # Flow element
            "safety": 35,  # Safety (fitting)
            "logic": 38,  # Logic (fitting)
            "flow": 19,  # Flow control
            "connection": 40,  # Connection (fitting)
            "annotation": 41,  # Annotation (fitting)
            "fail_position": 11,  # Fail position (valve)
            "accessory": 39,  # Accessory (fitting)
        }

        return category_map.get(category, None)

    def get_symbol_by_id(self, symbol_id: str) -> dict[str, Any] | None:
        """Get a symbol by its full ID."""
        return self.symbols.get(symbol_id)

    def get_symbols_by_class_id(self, class_id: int) -> list[dict[str, Any]]:
        """Get all symbols that map to a given class ID."""
        return self.class_id_map.get(class_id, [])

    def get_svg_path(self, symbol: dict[str, Any]) -> Path | None:
        """Get the absolute SVG file path for a symbol."""
        standard = symbol.get("standard", "").lower()
        category = symbol.get("category", "").lower()
        filename = symbol.get("filename", "")

        if not standard or not category or not filename:
            return None

        svg_path = _SYMBOLS_BASE / standard / category / filename
        return svg_path if svg_path.exists() else None

    def list_categories(self) -> list[str]:
        """List all available symbol categories for this standard."""
        categories = set()
        for symbol in self.symbols.values():
            cat = symbol.get("category", "")
            if cat:
                categories.add(cat)
        return sorted(list(categories))

    def list_symbols_in_category(self, category: str) -> list[dict[str, Any]]:
        """List all symbols in a given category."""
        return [
            sym for sym in self.symbols.values()
            if sym.get("category", "").lower() == category.lower()
        ]

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about the loaded symbols."""
        return {
            "total_symbols": len(self.symbols),
            "categories": self.list_categories(),
            "class_ids": sorted(list(self.class_id_map.keys())),
        }


# Global registry instance (lazy-loaded)
_default_registry: SymbolRegistry | None = None


def get_registry(standard: str = "isa") -> SymbolRegistry:
    """Get or create the default symbol registry."""
    global _default_registry
    if _default_registry is None or _default_registry.standard != standard:
        _default_registry = SymbolRegistry(standard=standard)
    return _default_registry

