"""
Database configuration.
"""

from pathlib import Path


def get_db_path() -> str:
    """Get the database path."""
    # Bruk hjemmemappen som standard plassering
    home_dir = Path.home()
    db_dir = home_dir / ".min_kamp"

    # Opprett database-mappen hvis den ikke finnes
    db_dir.mkdir(parents=True, exist_ok=True)

    return str(db_dir / "kampdata.db")
