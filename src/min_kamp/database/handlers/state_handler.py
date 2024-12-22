"""
Definerer state handler for tilstandshåndtering.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class StateHandler(BaseHandler):
    """Handler for tilstandshåndtering"""

    def lagre_tilstand(self, nokkel: str, verdi: str) -> bool:
        """Lagrer en tilstand

        Args:
            nokkel: Nøkkelen til tilstanden
            verdi: Verdien til tilstanden

        Returns:
            True hvis lagring var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO tilstander (nokkel, verdi)
                VALUES (?, ?)
                """,
                (nokkel, verdi),
            )
            self.db_handler.commit()

            logger.info("Lagret tilstand %s = %s", nokkel, verdi)
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved lagring av tilstand: %s", e)
            raise DatabaseError("Kunne ikke lagre tilstand") from e
        except Exception as e:
            logger.error("Uventet feil ved lagring av tilstand: %s", e)
            raise DatabaseError("Kunne ikke lagre tilstand") from e

    def hent_tilstand(self, nokkel: str) -> Optional[str]:
        """Henter en tilstand

        Args:
            nokkel: Nøkkelen til tilstanden

        Returns:
            Verdien til tilstanden hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute("SELECT verdi FROM tilstander WHERE nokkel = ?", (nokkel,))
            resultat = cursor.fetchone()

            if resultat:
                return resultat[0]
            return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av tilstand: %s", e)
            raise DatabaseError("Kunne ikke hente tilstand") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av tilstand: %s", e)
            raise DatabaseError("Kunne ikke hente tilstand") from e

    def slett_tilstand(self, nokkel: str) -> bool:
        """Sletter en tilstand

        Args:
            nokkel: Nøkkelen til tilstanden

        Returns:
            True hvis sletting var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute("DELETE FROM tilstander WHERE nokkel = ?", (nokkel,))
            self.db_handler.commit()

            logger.info("Slettet tilstand %s", nokkel)
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved sletting av tilstand: %s", e)
            raise DatabaseError("Kunne ikke slette tilstand") from e
        except Exception as e:
            logger.error("Uventet feil ved sletting av tilstand: %s", e)
            raise DatabaseError("Kunne ikke slette tilstand") from e
