"""
Database configuration.
"""

from pathlib import Path


def get_db_path() -> str:
    """Get the database path."""
    # Finn prosjektets rotmappe
    project_root = Path(__file__).parent.parent.parent.parent

    # Opprett database-mappen hvis den ikke finnes
    db_dir = project_root / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    return str(db_dir / "kampdata.db")
