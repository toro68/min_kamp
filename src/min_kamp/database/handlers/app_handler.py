"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer app handler for applikasjonshåndtering.
Se spesielt:
- avhengigheter.md -> Database -> Handlers -> App
- system.md -> Database -> Handlers -> App
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional, Dict, Any

from min_kamp.database.handlers.auth_handler import AuthHandler
from min_kamp.database.handlers.base_handler import BaseHandler
from min_kamp.database.handlers.bytteplan_handler import BytteplanHandler
from min_kamp.database.handlers.kamp_handler import KampHandler
from min_kamp.database.handlers.spiller_handler import SpillerHandler
from min_kamp.database.handlers.state_handler import StateHandler

logger = logging.getLogger(__name__)


class AppHandler(BaseHandler):
    """Handler for applikasjonshåndtering"""

    def __init__(self, db_handler) -> None:
        """Initialiserer app handler

        Args:
            db_handler: Database handler
        """
        super().__init__(db_handler)

        # Initialiser handlers
        self.auth_handler = AuthHandler(db_handler)
        self.bytteplan_handler = BytteplanHandler(db_handler)
        self.kamp_handler = KampHandler(db_handler)
        self.spiller_handler = SpillerHandler(db_handler)
        self.state_handler = StateHandler(db_handler)

    def init_database(self) -> bool:
        """Initialiserer databasen

        Returns:
            bool: True hvis initialiseringen var vellykket, False ellers
        """
        try:
            logger.debug("Starter database-initialisering i AppHandler")
            # Opprett tabeller
            conn = self.db_handler.get_connection()
            if conn:
                logger.info("Database initialisert")
                return True
            return False

        except SQLiteError as e:
            logger.error("SQLite-feil ved initialisering av database: %s", e)
            return False
        except Exception as e:
            logger.error("Uventet feil ved initialisering av database: %s", e)
            return False

    def registrer_bruker(
        self, brukernavn: str, passord: str
    ) -> Optional[Dict[str, Any]]:
        """Registrerer en ny bruker

        Args:
            brukernavn: Brukernavnet
            passord: Passordet

        Returns:
            Brukerinformasjon hvis registrering var vellykket, None ellers
        """
        return self.auth_handler.create_user(brukernavn, passord)

    def verifiser_bruker(self, brukernavn: str, passord: str) -> bool:
        """Verifiserer en bruker

        Args:
            brukernavn: Brukernavnet
            passord: Passordet

        Returns:
            True hvis verifisering var vellykket, False ellers
        """
        return self.auth_handler.authenticate(brukernavn, passord)

    def hent_bruker_id(self, brukernavn: str) -> Optional[int]:
        """Henter bruker ID

        Args:
            brukernavn: Brukernavnet

        Returns:
            Bruker ID hvis funnet, None ellers
        """
        user = self.auth_handler.get_user(brukernavn)
        return user["id"] if user else None
