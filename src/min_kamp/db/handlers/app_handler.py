"""
Handler for applikasjonsinnstillinger.
"""

import logging
from typing import Optional, Any

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


class AppHandler:
    """Handler for applikasjonsinnstillinger."""

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        self._database_handler = db_handler
        self._auth_handler = None
        self._kamp_handler = None
        self._spiller_handler = None
        self._bytteplan_handler = None

    @property
    def auth_handler(self):
        """Henter auth handler.

        Returns:
            AuthHandler: Instans av AuthHandler
        """
        if self._auth_handler is None:
            from min_kamp.db.handlers.auth_handler import AuthHandler

            self._auth_handler = AuthHandler(self._database_handler)
        return self._auth_handler

    @property
    def kamp_handler(self):
        """Henter kamp handler.

        Returns:
            KampHandler: Instans av KampHandler
        """
        if self._kamp_handler is None:
            from min_kamp.db.handlers.kamp_handler import KampHandler

            self._kamp_handler = KampHandler(self._database_handler)
        return self._kamp_handler

    @property
    def spiller_handler(self):
        """Henter spiller handler.

        Returns:
            SpillerHandler: Instans av SpillerHandler
        """
        if self._spiller_handler is None:
            from min_kamp.db.handlers.spiller_handler import SpillerHandler

            self._spiller_handler = SpillerHandler(self._database_handler)
        return self._spiller_handler

    @property
    def bytteplan_handler(self):
        """Henter bytteplan handler.

        Returns:
            BytteplanHandler: Instans av BytteplanHandler
        """
        if self._bytteplan_handler is None:
            from min_kamp.db.handlers.bytteplan_handler import BytteplanHandler

            self._bytteplan_handler = BytteplanHandler(self._database_handler)
        return self._bytteplan_handler

    def lagre_innstilling(
        self, nokkel: str, verdi: str, bruker_id: Optional[int] = None
    ) -> None:
        """Lagrer en innstilling i databasen.

        Args:
            nokkel: Nøkkel for innstillingen
            verdi: Verdi for innstillingen
            bruker_id: ID for brukeren (None for globale innstillinger)
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                # Slett eksisterende innstilling
                cursor.execute(
                    """
                    DELETE FROM app_innstillinger
                    WHERE nokkel = ? AND (bruker_id = ? OR bruker_id IS NULL)
                    """,
                    (nokkel, bruker_id),
                )

                # Lagre ny innstilling
                cursor.execute(
                    """
                    INSERT INTO app_innstillinger (nokkel, verdi, bruker_id)
                    VALUES (?, ?, ?)
                    """,
                    (nokkel, verdi, bruker_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved lagring av innstilling: %s", e)
            raise DatabaseError(f"Kunne ikke lagre innstilling: {e}")

    def hent_innstilling(
        self, nokkel: str, bruker_id: Optional[int] = None
    ) -> Optional[str]:
        """Henter en innstilling fra databasen.

        Args:
            nokkel: Nøkkel for innstillingen
            bruker_id: ID for brukeren (None for globale innstillinger)

        Returns:
            Verdien for innstillingen eller None hvis ikke funnet
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT verdi
                    FROM app_innstillinger
                    WHERE nokkel = ? AND (bruker_id = ? OR bruker_id IS NULL)
                    """,
                    (nokkel, bruker_id),
                )
                result = cursor.fetchone()
                return result[0] if result else None

        except Exception as e:
            logger.error("Feil ved henting av innstilling: %s", e)
            raise DatabaseError(f"Kunne ikke hente innstilling: {e}")

    def slett_innstilling(self, nokkel: str, bruker_id: Optional[int] = None) -> None:
        """Sletter en innstilling fra databasen.

        Args:
            nokkel: Nøkkel for innstillingen
            bruker_id: ID for brukeren (None for globale innstillinger)
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM app_innstillinger
                    WHERE nokkel = ? AND (bruker_id = ? OR bruker_id IS NULL)
                    """,
                    (nokkel, bruker_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved sletting av innstilling: %s", e)
            raise DatabaseError(f"Kunne ikke slette innstilling: {e}")
