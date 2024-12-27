"""
Auth handler.
"""

import logging
import threading
import traceback
from typing import Any, Dict, Optional
import bcrypt

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


class AuthHandler:
    """Handler for autentisering."""

    _instance = None
    _lock = threading.Lock()
    _bcrypt_lock = threading.Lock()  # Separat lås for bcrypt-operasjoner

    def __new__(cls, *args, **kwargs):
        """Implementer singleton pattern på en thread-safe måte."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        if not hasattr(self, "_initialized"):
            self._database_handler = db_handler
            self._initialized = True
            logger.info("AuthHandler initialisert i tråd %d", threading.get_ident())

    def _hash_passord(self, passord: str) -> tuple[bytes, bytes]:
        """Hash passord på en thread-safe måte.

        Args:
            passord: Passordet som skal hashes

        Returns:
            Tuple med (hashed_passord, salt)
        """
        thread_id = threading.get_ident()
        logger.debug("Starter hashing av passord i tråd %d", thread_id)

        with self._bcrypt_lock:
            try:
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(passord.encode(), salt)
                logger.debug("Fullførte hashing av passord i tråd %d", thread_id)
                return hashed, salt
            except Exception as e:
                logger.error(
                    "Feil ved hashing av passord i tråd %d:\n%s\n%s",
                    thread_id,
                    str(e),
                    traceback.format_exc(),
                )
                raise

    def _sjekk_passord_match(self, passord: str, stored_hash: bytes) -> bool:
        """Sjekk passord match på en thread-safe måte.

        Args:
            passord: Passordet som skal sjekkes
            stored_hash: Lagret hash å sjekke mot

        Returns:
            True hvis passord matcher
        """
        thread_id = threading.get_ident()
        logger.debug("Starter passordsjekk i tråd %d", thread_id)

        with self._bcrypt_lock:
            try:
                matches = bcrypt.checkpw(passord.encode(), stored_hash)
                logger.debug(
                    "Fullførte passordsjekk i tråd %d (match: %s)", thread_id, matches
                )
                return matches
            except Exception as e:
                logger.error(
                    "Feil ved sjekk av passord i tråd %d:\n%s\n%s",
                    thread_id,
                    str(e),
                    traceback.format_exc(),
                )
                raise

    def hent_bruker(self, bruker_id: int) -> Optional[Dict[str, Any]]:
        """Henter brukerinfo.

        Args:
            bruker_id: ID for brukeren

        Returns:
            Dict med brukerinfo eller None hvis ikke funnet
        """
        thread_id = threading.get_ident()
        logger.debug("Starter henting av bruker %d i tråd %d", bruker_id, thread_id)

        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, brukernavn
                    FROM brukere
                    WHERE id = ?
                    """,
                    (bruker_id,),
                )
                result = cursor.fetchone()

                if result:
                    bruker = {"id": result[0], "brukernavn": result[1]}
                    logger.debug(
                        "Fant bruker %d i tråd %d: %s", bruker_id, thread_id, bruker
                    )
                    return bruker

                logger.debug("Fant ikke bruker %d i tråd %d", bruker_id, thread_id)
                return None

        except Exception as e:
            logger.error(
                "Feil ved henting av bruker %d i tråd %d:\n%s\n%s",
                bruker_id,
                thread_id,
                str(e),
                traceback.format_exc(),
            )
            raise DatabaseError(f"Kunne ikke hente bruker: {e}")

    def sjekk_passord(self, brukernavn: str, passord: str) -> Optional[Dict[str, Any]]:
        """Sjekker om passordet er riktig.

        Args:
            brukernavn: Brukernavnet
            passord: Passordet som skal sjekkes

        Returns:
            Dict med brukerinfo eller None hvis feil passord
        """
        thread_id = threading.get_ident()
        logger.debug(
            "Starter passordsjekk for bruker '%s' i tråd %d", brukernavn, thread_id
        )

        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, passord_hash
                    FROM brukere
                    WHERE brukernavn = ?
                    """,
                    (brukernavn,),
                )
                result = cursor.fetchone()

                if not result:
                    logger.warning(
                        "Bruker '%s' ikke funnet i tråd %d", brukernavn, thread_id
                    )
                    return None

                bruker_id = result[0]
                stored_hash = result[1]

                try:
                    if self._sjekk_passord_match(passord, stored_hash):
                        bruker = {"id": bruker_id, "brukernavn": brukernavn}
                        logger.debug(
                            "Vellykket passordsjekk for bruker '%s' i tråd %d",
                            brukernavn,
                            thread_id,
                        )
                        return bruker

                    logger.warning(
                        "Feil passord for bruker '%s' i tråd %d", brukernavn, thread_id
                    )
                    return None

                except Exception as e:
                    logger.error(
                        "Feil ved sjekk av passord for bruker '%s' i tråd %d:\n%s\n%s",
                        brukernavn,
                        thread_id,
                        str(e),
                        traceback.format_exc(),
                    )
                    return None

        except Exception as e:
            logger.error(
                "Feil ved passordsjekk for bruker '%s' i tråd %d:\n%s\n%s",
                brukernavn,
                thread_id,
                str(e),
                traceback.format_exc(),
            )
            raise DatabaseError(f"Kunne ikke sjekke passord: {e}")

    def opprett_bruker(self, brukernavn: str, passord: str) -> Optional[int]:
        """Oppretter en ny bruker.

        Args:
            brukernavn: Brukernavnet
            passord: Passordet

        Returns:
            ID for den nye brukeren eller None ved feil
        """
        thread_id = threading.get_ident()
        logger.debug(
            "Starter opprettelse av bruker '%s' i tråd %d", brukernavn, thread_id
        )

        try:
            # Hash passord utenfor databasetransaksjonen
            hashed, salt = self._hash_passord(passord)

            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Sjekk om brukeren finnes
                cursor.execute(
                    """
                    SELECT id FROM brukere WHERE brukernavn = ?
                    """,
                    (brukernavn,),
                )
                if cursor.fetchone():
                    logger.warning(
                        "Bruker '%s' finnes allerede i tråd %d", brukernavn, thread_id
                    )
                    return None

                # Opprett bruker
                cursor.execute(
                    """
                    INSERT INTO brukere (brukernavn, passord_hash, salt)
                    VALUES (?, ?, ?)
                    """,
                    (brukernavn, hashed, salt),
                )
                bruker_id = cursor.lastrowid

                if not bruker_id:
                    logger.error(
                        "Kunne ikke opprette bruker '%s' i tråd %d",
                        brukernavn,
                        thread_id,
                    )
                    return None

                logger.info(
                    "Bruker '%s' (ID: %d) opprettet i tråd %d",
                    brukernavn,
                    bruker_id,
                    thread_id,
                )
                return bruker_id

        except Exception as e:
            logger.error(
                "Feil ved opprettelse av bruker '%s' i tråd %d:\n%s\n%s",
                brukernavn,
                thread_id,
                str(e),
                traceback.format_exc(),
            )
            raise DatabaseError(f"Kunne ikke opprette bruker: {e}")

    def logg_ut(self) -> None:
        """Logger ut brukeren ved å fjerne bruker_id fra session state."""
        from min_kamp.utils.streamlit_utils import set_session_state

        set_session_state("bruker_id", None)
        logger.debug("Bruker logget ut")
