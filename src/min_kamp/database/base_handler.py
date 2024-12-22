"""Base klasse for alle database handlers"""

import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class BaseHandler:
    def __init__(self, db_path: str, test_mode: bool = False) -> None:
        """
        Initialiserer en BaseHandler

        Args:
            db_path: Sti til databasefilen
            test_mode: Om handleren kjører i testmodus
        """
        self._db_path = db_path
        self._test_mode = test_mode
        self._connection = None

    @contextmanager
    def get_connection(self) -> Generator:
        """
        Kontekst-manager for databasetilkobling

        Yields:
            En aktiv databasetilkobling

        Raises:
            Exception: Hvis tilkobling feiler
        """
        try:
            if self._connection is None:
                import sqlite3

                self._connection = sqlite3.connect(
                    self._db_path, detect_types=sqlite3.PARSE_DECLTYPES
                )
                self._connection.row_factory = sqlite3.Row

            yield self._connection

        except Exception as e:
            logger.error(f"Feil ved databasetilkobling: {e}")
            raise

    def lukk_tilkobling(self) -> None:
        """Lukker databasetilkoblingen hvis den er åpen"""
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection = None
            except Exception as e:
                logger.error(f"Feil ved lukking av databasetilkobling: {e}")

    def tabell_eksisterer(self, tabell_navn: str) -> bool:
        """
        Sjekker om en tabell eksisterer i databasen

        Args:
            tabell_navn: Navnet på tabellen som skal sjekkes

        Returns:
            True hvis tabellen eksisterer, False ellers
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM sqlite_master
                    WHERE type='table' AND name=?
                    """,
                    (tabell_navn,),
                )
                return cursor.fetchone()[0] > 0

        except Exception as e:
            logger.error(f"Feil ved sjekk av tabell {tabell_navn}: {e}", exc_info=True)
            return False

    def verifiser_tilkobling(self) -> bool:
        """
        Verifiserer at databasetilkoblingen fungerer

        Returns:
            True hvis tilkoblingen er OK, False ellers
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Feil ved verifisering av databasetilkobling: {e}")
            return False
