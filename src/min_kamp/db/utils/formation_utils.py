"""Utilities for handling formations."""

from typing import Dict, List, Optional


def get_available_formations() -> List[str]:
    """Return a list of available formations."""
    return ["4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "3-4-3"]


def validate_formation(formation: str) -> bool:
    """Check if a formation is valid.

    Args:
        formation: The formation to validate (e.g. "4-4-2")

    Returns:
        bool: True if formation is valid, False otherwise
    """
    return formation in get_available_formations()


def get_formation_structure(formation: str) -> Optional[Dict[str, int]]:
    """Get the structure of a formation.

    Args:
        formation: The formation (e.g. "4-4-2")

    Returns:
        Dict with keys 'forsvar', 'midtbane', 'angrep' and their counts,
        or None if formation is invalid
    """
    if not validate_formation(formation):
        return None

    numbers = [int(n) for n in formation.split("-")]

    return {"forsvar": numbers[0], "midtbane": numbers[1], "angrep": numbers[2]}
