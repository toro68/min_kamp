"""
Tester for database schema.
"""

import logging
import os
import sqlite3
import unittest
from pathlib import Path
from typing import List, Tuple

from min_kamp.database.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)


class TestDatabaseSchema(unittest.TestCase):
    """Test suite for database schema"""

    def setUp(self) -> None:
        """Sett opp testmiljø"""
        os.environ["SCHEMA_PATH"] = "src/min_kamp/database/schema.sql"
        os.environ["DATABASE_PATH"] = "data/test_kampdata.db"
        self.db_handler = DatabaseHandler()

    def tearDown(self) -> None:
        """Rydd opp etter tester"""
        self.db_handler.close_connections()
        if Path(os.getenv("DATABASE_PATH", "")).exists():
            Path(os.getenv("DATABASE_PATH", "")).unlink()

    def test_database_initialisering(self) -> None:
        """Test at databasen initialiseres korrekt"""
        self.assertTrue(Path(os.getenv("DATABASE_PATH", "")).exists())
        with self.db_handler.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            self.assertIsNotNone(cursor.fetchone())

    def test_tabellstruktur(self) -> None:
        """Test at alle påkrevde tabeller eksisterer med riktig struktur"""
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Sjekk at alle påkrevde tabeller eksisterer
                påkrevde_tabeller = [
                    "schema_version",
                    "brukere",
                    "spillere",
                    "kamper",
                    "bytteplan",
                    "state",
                ]
                for tabell in påkrevde_tabeller:
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (tabell,),
                    )
                    self.assertIsNotNone(
                        cursor.fetchone(), f"Påkrevd tabell mangler: {tabell}"
                    )

                    # Sjekk kolonnestruktur
                    kolonner = self._hent_kolonner(tabell)
                    self.assertGreater(
                        len(kolonner), 0, f"Ingen kolonner funnet i {tabell}"
                    )

        except sqlite3.Error as e:
            self.fail(f"Database operasjon feilet: {e}")

    def _hent_kolonner(self, tabell: str) -> List[Tuple[str, str]]:
        """Hjelpemetode for å hente kolonneinfo fra en tabell"""
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({tabell})")
                kolonner = [(rad[1], rad[2]) for rad in cursor.fetchall()]
                return kolonner
        except sqlite3.Error as e:
            logger.error(f"Feil ved henting av kolonneinfo: {e}")
            return []


if __name__ == "__main__":
    unittest.main()
