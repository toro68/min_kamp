"""
Autentisering og autorisasjon for Min Kamp
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AuthHandler:
    """Håndterer autentisering og autorisasjon."""

    def __init__(self, db_handler):
        """Initialiserer AuthHandler."""
        self.db_handler = db_handler
        self._user_id = None

    def er_autentisert(self) -> bool:
        """Sjekker om bruker er autentisert."""
        return True  # Midlertidig: alltid autentisert

    def hent_innlogget_bruker_id(self) -> Optional[str]:
        """Henter ID for innlogget bruker."""
        return "1"  # Midlertidig: returnerer fast bruker-ID
