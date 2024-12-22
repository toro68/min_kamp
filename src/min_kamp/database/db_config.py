"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConfig:
    # Definerer bane til data-mappe og database
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    DB_PATH = DATA_DIR / "kampdata.db"

    @classmethod
    def setup(cls) -> bool:
        """Setter opp nødvendige mapper og filer"""
        try:
            # Sjekk om data-mappen eksisterer, opprett hvis ikke
            if not cls.DATA_DIR.exists():
                cls.DATA_DIR.mkdir(parents=True)

            # Sjekk om databasefilen eksisterer
            if not cls.DB_PATH.exists():
                # Opprett tom database
                conn = sqlite3.connect(cls.DB_PATH)
                conn.close()

            return True
        except Exception as e:
            logger.error(f"Feil ved database setup: {e}")
            return False

    @classmethod
    def get_connection_string(cls) -> str:
        """Returnerer connection string for databasen"""
        return str(cls.DB_PATH)
