"""
Streamlit-relaterte hjelpefunksjoner.
"""

import logging
import streamlit as st
from typing import Any, Optional

logger = logging.getLogger(__name__)


def set_session_state(key: str, value: Any) -> None:
    """Setter en verdi i session state.

    Args:
        key: Nøkkel
        value: Verdi
    """
    try:
        st.session_state[key] = value
        logger.debug("Session state oppdatert: %s = %s", key, value)
    except Exception as e:
        logger.error("Feil ved oppdatering av session state: %s", e)


def get_session_state(key: str) -> Optional[Any]:
    """Henter en verdi fra session state.

    Args:
        key: Nøkkel

    Returns:
        Optional[Any]: Verdi hvis funnet, None ellers
    """
    try:
        return st.session_state.get(key)
    except Exception as e:
        logger.error("Feil ved henting fra session state: %s", e)
        return None
