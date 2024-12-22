"""
Definerer base handler for databaseoperasjoner.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Any, List, Optional

from min_kamp.database.errors import DatabaseError

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base handler for databaseoperasjoner.

    Denne klassen inneholder felles funksjonalitet for alle database handlers,
    inkludert grunnleggende databaseoperasjoner og feilhåndtering.
    """

    def __init__(self, db_handler: Any) -> None:
        """Initialiserer base handler.

        Args:
            db_handler: Database handler
        """
        self.db_handler = db_handler

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Any]]:
        """Utfører en SELECT-spørring.

        Args:
            query: SQL-spørringen
            params: Parametere til spørringen

        Returns:
            Resultatet av spørringen hvis vellykket, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

        except SQLiteError as e:
            logger.error("SQLite-feil ved utføring av spørring: %s", e)
            raise DatabaseError("Kunne ikke utføre spørring") from e
        except Exception as e:
            logger.error("Uventet feil ved utføring av spørring: %s", e)
            raise DatabaseError("Kunne ikke utføre spørring") from e

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Utfører en UPDATE/INSERT/DELETE-spørring.

        Args:
            query: SQL-spørringen
            params: Parametere til spørringen

        Returns:
            True hvis oppdateringen var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(query, params)
            self.db_handler.commit()
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved oppdatering: %s", e)
            raise DatabaseError("Kunne ikke utføre oppdatering") from e
        except Exception as e:
            logger.error("Uventet feil ved oppdatering: %s", e)
            raise DatabaseError("Kunne ikke utføre oppdatering") from e

    def record_exists(self, table: str, column: str, value: Any) -> bool:
        """Sjekker om en rad eksisterer.

        Args:
            table: Tabellnavn
            column: Kolonnenavn
            value: Verdi å sjekke

        Returns:
            True hvis raden eksisterer, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (value,))
            antall = cursor.fetchone()[0]
            return antall > 0

        except SQLiteError as e:
            logger.error("SQLite-feil ved sjekk av rad: %s", e)
            raise DatabaseError("Kunne ikke sjekke om rad eksisterer") from e
        except Exception as e:
            logger.error("Uventet feil ved sjekk av rad: %s", e)
            raise DatabaseError("Kunne ikke sjekke om rad eksisterer") from e
