"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for Min Kamp.
Se spesielt:
- avhengigheter.md -> Frontend -> App
- system.md -> Frontend -> App
"""

import logging
import os
from pathlib import Path

import streamlit as st

from min_kamp.database.utils.session_state import init_session_state
from min_kamp.pages.page_renderer import render_page

logger = logging.getLogger(__name__)


def main() -> None:
    """Hovedfunksjon for applikasjonen"""
    try:
        logger.info("Starter applikasjon")

        # Initialiser session state
        init_session_state()

        # Sett opp logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Sett opp sidevisning
        st.set_page_config(
            page_title="Min Kamp",
            page_icon="⚽",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Logg miljøvariabler
        logger.debug("Starter database-initialisering")
        logger.debug(f"SCHEMA_PATH: {os.getenv('SCHEMA_PATH')}")
        logger.debug(f"DATABASE_PATH: {os.getenv('DATABASE_PATH')}")
        logger.debug(f"Gjeldende mappe: {Path.cwd()}")

        # Initialiser database
        if "db_handler" not in st.session_state:
            logger.error("Database initialisering feilet")
            return

        # Render gjeldende side
        render_page(st.session_state.current_page)

    except Exception as e:
        logger.error(f"Kritisk feil i hovedapplikasjon: {e}")
        raise


if __name__ == "__main__":
    main()
