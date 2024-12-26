"""
Session state håndtering.
"""

import logging
from typing import Optional, TypeVar, Generic

from min_kamp.utils.streamlit_utils import get_session_state, set_session_state

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SessionStateResult(Generic[T]):
    """Resultat fra session state operasjon."""

    def __init__(self, success: bool, value: Optional[T] = None) -> None:
        """Initialiserer SessionStateResult.

        Args:
            success: Om operasjonen var vellykket
            value: Verdien fra session state
        """
        self.success = success
        self.value = value


def safe_get_session_state(key: str) -> SessionStateResult:
    """Henter en verdi fra session state på en trygg måte.

    Args:
        key: Nøkkel

    Returns:
        SessionStateResult: Resultat med success og value
    """
    try:
        value = get_session_state(key)
        return SessionStateResult(True, value)
    except Exception as e:
        logger.error("Feil ved henting fra session state: %s", e)
        return SessionStateResult(False)


def initialize_session_state() -> None:
    """Initialiserer session state."""
    try:
        logger.info("Initialiserer session state")

        # Initialiser session state med standardverdier
        defaults = {
            "bruker_id": None,
            "kamp_id": None,
            "kamptropp_id": None,
            "bytteplan_id": None,
            "spilletid_id": None,
            "app_handler": None,
            "auth_handler": None,
            "kamp_handler": None,
            "spiller_handler": None,
            "bytteplan_handler": None,
            "spilletid_handler": None,
            "current_kamp_id": None,
        }

        for key, value in defaults.items():
            if get_session_state(key) is None:
                set_session_state(key, value)

        logger.info("Session state initialized")

    except Exception as e:
        logger.error("Feil ved initialisering av session state: %s", e)
