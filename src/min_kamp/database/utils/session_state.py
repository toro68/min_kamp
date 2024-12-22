"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Håndterer session state for applikasjonen.
Se spesielt:
- avhengigheter.md -> Frontend -> State
- system.md -> Frontend -> State
"""

import logging
import os

import streamlit as st

from min_kamp.database import AppHandler, DatabaseHandler
from min_kamp.database.handlers.auth_handler import AuthHandler

logger = logging.getLogger(__name__)


def init_session_state() -> None:
    """Initialiserer session state med standardverdier"""
    logger.debug("Starter initialisering av session state")

    # Behold eksisterende verdier
    existing_state = {
        key: value
        for key, value in st.session_state.items()
        if key
        in [
            "authenticated",
            "username",
            "user_id",
            "current_page",
            "db_handler",
            "app_handler",
            "auth_handler",
        ]
    }

    # Sett standardverdier hvis de ikke finnes
    if "current_page" not in st.session_state:
        st.session_state.current_page = "oppsett"
        logger.debug("Satt current_page til 'oppsett'")

    if "user" not in st.session_state:
        st.session_state.user = None
        logger.debug("Satt user til None")

    # Opprett handlers bare hvis de ikke finnes fra før
    if "db_handler" not in existing_state:
        logger.debug(
            f"Oppretter DatabaseHandler med SCHEMA_PATH: {os.getenv('SCHEMA_PATH')}"
        )
        st.session_state.db_handler = DatabaseHandler()
        logger.debug("DatabaseHandler opprettet")

        logger.debug("Oppretter AppHandler")
        st.session_state.app_handler = AppHandler(st.session_state.db_handler)
        logger.debug("AppHandler opprettet")

        logger.debug("Oppretter AuthHandler")
        st.session_state.auth_handler = AuthHandler(st.session_state.db_handler)
        logger.debug("AuthHandler opprettet")
    else:
        logger.debug("Gjenbruker eksisterende handlers")

    # Sett standardverdier for autentisering
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "username" not in st.session_state:
        st.session_state.username = None

    if "show_register" not in st.session_state:
        st.session_state.show_register = False

    # Gjenopprett eksisterende verdier
    for key, value in existing_state.items():
        if value is not None:
            st.session_state[key] = value
            logger.debug(f"Gjenopprettet {key}={value}")

    logger.debug("Session state initialisering fullført")
