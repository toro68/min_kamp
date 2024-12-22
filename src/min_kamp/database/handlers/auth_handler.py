"""
Definerer autentiserings-handler for databaseoperasjoner.
"""

import logging
import hashlib
import os
from typing import Any, Dict, List, Optional

from min_kamp.database.errors import AuthenticationError, DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: str) -> str:
    """Hasher et passord med salt.

    Args:
        password: Passordet som skal hashes
        salt: Salt som skal brukes

    Returns:
        Hashet passord
    """
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def generate_salt() -> str:
    """Genererer et tilfeldig salt.

    Returns:
        Tilfeldig salt
    """
    return os.urandom(16).hex()


class AuthHandler(BaseHandler):
    """Handler for autentisering og autorisasjon.

    Denne klassen håndterer all autentisering og autorisasjon i applikasjonen,
    inkludert innlogging, utlogging, og tilgangskontroll.
    """

    def __init__(self, db_handler: Any) -> None:
        """Initialiserer auth handler.

        Args:
            db_handler: Database handler
        """
        super().__init__(db_handler)

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Henter brukerinformasjon.

        Args:
            username: Brukernavn

        Returns:
            Brukerinformasjon hvis brukeren finnes, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM brukere WHERE brukernavn = ?", (username,)
                )
                user = cursor.fetchone()
                return dict(user) if user else None

        except Exception as e:
            logger.error("Feil ved henting av bruker: %s", e)
            raise DatabaseError("Kunne ikke hente bruker") from e

    def authenticate(self, username: str, password: str) -> bool:
        """Autentiserer en bruker.

        Args:
            username: Brukernavn
            password: Passord

        Returns:
            True hvis autentisering er vellykket, False ellers

        Raises:
            AuthenticationError: Ved autentiseringsfeil
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT passord_hash, salt FROM brukere WHERE brukernavn = ?",
                    (username,),
                )
                result = cursor.fetchone()

                if not result:
                    raise AuthenticationError("Ugyldig brukernavn eller passord")

                stored_hash = result["passord_hash"]
                salt = result["salt"]

                # Hash det innsendte passordet med lagret salt
                password_hash = hash_password(password, salt)

                if password_hash != stored_hash:
                    raise AuthenticationError("Ugyldig brukernavn eller passord")

                return True

        except AuthenticationError as e:
            logger.error("Autentiseringsfeil: %s", e)
            raise
        except Exception as e:
            logger.error("Databasefeil ved autentisering: %s", e)
            raise DatabaseError("Kunne ikke autentisere bruker") from e

    def create_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Oppretter en ny bruker.

        Args:
            username: Brukernavn
            password: Passord

        Returns:
            Brukerinformasjon hvis opprettelse var vellykket, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            # Sjekk om brukeren allerede eksisterer
            if self.get_user(username):
                logger.warning("Bruker eksisterer allerede: %s", username)
                return None

            # Generer salt og hash passordet
            salt = generate_salt()
            password_hash = hash_password(password, salt)

            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO brukere (brukernavn, passord_hash, salt)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash, salt),
                )
                conn.commit()

            logger.info("Opprettet ny bruker: %s", username)
            return self.get_user(username)

        except Exception as e:
            logger.error("Feil ved opprettelse av bruker: %s", e)
            raise DatabaseError("Kunne ikke opprette bruker") from e

    def get_user_roles(self, username: str) -> List[str]:
        """Henter brukerens roller.

        Args:
            username: Brukernavn

        Returns:
            Liste med brukerens roller

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT r.rolle_navn
                    FROM bruker_roller ur
                    JOIN roller r ON ur.rolle_id = r.rolle_id
                    JOIN brukere b ON ur.bruker_id = b.id
                    WHERE b.brukernavn = ?
                    """,
                    (username,),
                )
                return [row["rolle_navn"] for row in cursor.fetchall()]

        except Exception as e:
            logger.error("Feil ved henting av brukerroller: %s", e)
            raise DatabaseError("Kunne ikke hente brukerroller") from e

    def has_role(self, username: str, role: str) -> bool:
        """Sjekker om brukeren har en spesifikk rolle.

        Args:
            username: Brukernavn
            role: Rolle å sjekke

        Returns:
            True hvis brukeren har rollen, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            roles = self.get_user_roles(username)
            return role in roles

        except Exception as e:
            logger.error("Feil ved sjekk av brukerrolle: %s", e)
            raise DatabaseError("Kunne ikke sjekke brukerrolle") from e
