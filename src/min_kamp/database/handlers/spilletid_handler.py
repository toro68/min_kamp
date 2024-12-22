"""
Definerer spilletid handler for spilletidhåndtering.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class SpilletidHandler(BaseHandler):
    """Handler for spilletidhåndtering"""

    def registrer_spilletid(self, kamp_id: int, spiller_id: int, minutter: int) -> bool:
        """Registrerer spilletid for en spiller i en kamp

        Args:
            kamp_id: ID til kampen
            spiller_id: ID til spilleren
            minutter: Antall minutter spilt

        Returns:
            True hvis registrering var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                INSERT INTO spilletid (kamp_id, spiller_id, minutter)
                VALUES (?, ?, ?)
                """,
                (kamp_id, spiller_id, minutter),
            )
            self.db_handler.commit()

            logger.info(
                "Registrerte %d minutter for spiller %d i kamp %d",
                minutter,
                spiller_id,
                kamp_id,
            )
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved registrering av spilletid: %s", e)
            raise DatabaseError("Kunne ikke registrere spilletid") from e
        except Exception as e:
            logger.error("Uventet feil ved registrering av spilletid: %s", e)
            raise DatabaseError("Kunne ikke registrere spilletid") from e

    def hent_spilletid(self, kamp_id: int, spiller_id: int) -> Optional[int]:
        """Henter spilletid for en spiller i en kamp

        Args:
            kamp_id: ID til kampen
            spiller_id: ID til spilleren

        Returns:
            Antall minutter spilt hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                "SELECT minutter FROM spilletid WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id),
            )
            resultat = cursor.fetchone()

            if resultat:
                return resultat[0]
            return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av spilletid: %s", e)
            raise DatabaseError("Kunne ikke hente spilletid") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av spilletid: %s", e)
            raise DatabaseError("Kunne ikke hente spilletid") from e

    def hent_total_spilletid(self, spiller_id: int) -> int:
        """Henter total spilletid for en spiller

        Args:
            spiller_id: ID til spilleren

        Returns:
            Totalt antall minutter spilt

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                "SELECT SUM(minutter) FROM spilletid WHERE spiller_id = ?",
                (spiller_id,),
            )
            resultat = cursor.fetchone()

            return resultat[0] if resultat[0] is not None else 0

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av total spilletid: %s", e)
            raise DatabaseError("Kunne ikke hente total spilletid") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av total spilletid: %s", e)
            raise DatabaseError("Kunne ikke hente total spilletid") from e
