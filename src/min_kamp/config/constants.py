"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer konstanter for applikasjonen.
Se spesielt:
- avhengigheter.md -> Config -> Constants
- system.md -> Config -> Constants
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Sett opp logging
logger = logging.getLogger(__name__)

# Last inn miljøvariabler
load_dotenv()

# Database
DATABASE_FILE = "kampdata.db"
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path("data") / DATABASE_FILE))
logger.debug(f"DATABASE_PATH satt til: {DATABASE_PATH}")

SCHEMA_FILE = "schema.sql"
SCHEMA_PATH = os.getenv("SCHEMA_PATH", str(Path("src/min_kamp/database") / SCHEMA_FILE))
logger.debug(f"SCHEMA_PATH satt til: {SCHEMA_PATH}")
logger.debug(f"SCHEMA_PATH absolutt sti: {Path(SCHEMA_PATH).absolute()}")

# Validering
MIN_SPILLERE = 5
MAX_SPILLERE = 12
MIN_PERIODER = 2
MAX_PERIODER = 8

# Posisjoner
POSISJONER = [
    "Målvakt",
    "Venstreback",
    "Midtback",
    "Høyreback",
    "Venstreving",
    "Strek",
    "Høyreving",
]

# Sikre at paths eksisterer
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
