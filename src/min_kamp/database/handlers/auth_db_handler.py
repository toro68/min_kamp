"""
Definerer auth db handler for autentiseringsdatabase.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class AuthDBHandler(BaseHandler):
    """Handler for autentiseringsdatabase.

    Denne klassen håndterer databaseoperasjoner relatert til autentisering,
    inkludert brukerregistrering, verifisering og bruker-ID oppslag.
    """

    def registrer_bruker(self, brukernavn: str, passord_hash: bytes) -> bool:
        """Registrerer en ny bruker i databasen.

        Args:
            brukernavn: Brukernavnet
            passord_hash: Hashet passord

        Returns:
            True hvis registrering var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                INSERT INTO brukere (brukernavn, passord_hash)
                VALUES (?, ?)
                """,
                (brukernavn, passord_hash),
            )
            self.db_handler.commit()

            logger.info("Registrerte bruker %s", brukernavn)
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved registrering av bruker: %s", e)
            raise DatabaseError("Kunne ikke registrere bruker") from e
        except Exception as e:
            logger.error("Uventet feil ved registrering av bruker: %s", e)
            raise DatabaseError("Kunne ikke registrere bruker") from e

    def hent_passord_hash(self, brukernavn: str) -> Optional[bytes]:
        """Henter passord-hash for en bruker.

        Args:
            brukernavn: Brukernavnet

        Returns:
            Passord-hash hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                "SELECT passord_hash FROM brukere WHERE brukernavn = ?",
                (brukernavn,),
            )
            resultat = cursor.fetchone()

            if resultat:
                return resultat[0]
            return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av passord-hash: %s", e)
            raise DatabaseError("Kunne ikke hente passord-hash") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av passord-hash: %s", e)
            raise DatabaseError("Kunne ikke hente passord-hash") from e

    def hent_bruker_id(self, brukernavn: str) -> Optional[int]:
        """Henter bruker-ID for et brukernavn.

        Args:
            brukernavn: Brukernavnet

        Returns:
            Bruker-ID hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                "SELECT id FROM brukere WHERE brukernavn = ?",
                (brukernavn,),
            )
            resultat = cursor.fetchone()

            if resultat:
                return resultat[0]
            return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av bruker-ID: %s", e)
            raise DatabaseError("Kunne ikke hente bruker-ID") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av bruker-ID: %s", e)
            raise DatabaseError("Kunne ikke hente bruker-ID") from e
