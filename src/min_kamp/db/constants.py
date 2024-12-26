"""Database constants."""

import os
from pathlib import Path

from min_kamp.db.db_config import get_db_path

# Miljøvariabler
IS_TEST = os.getenv("IS_TEST", "false").lower() == "true"

# Database
DATABASE_FILE = get_db_path()
if IS_TEST:
    # For tester, bruk en egen testdatabase
    test_db_dir = Path(DATABASE_FILE).parent
    DATABASE_FILE = str(test_db_dir / "test.db")
