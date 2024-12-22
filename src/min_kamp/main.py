"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedmodul for applikasjonen.
Se spesielt:
- avhengigheter.md -> Frontend -> Main
- system.md -> Frontend -> Main
"""

import logging

import streamlit as st

from min_kamp.database.utils.session_state import init_session_state
from min_kamp.pages.page_renderer import render_page

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Hovedfunksjon for applikasjonen"""
    try:
        # Sett opp Streamlit
        st.set_page_config(
            page_title="Min Kamp",
            page_icon="⚽",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Initialiser session state hvis ikke allerede initialisert
        if "initialized" not in st.session_state:
            logger.debug("Første gangs initialisering av session state")
            init_session_state()
            st.session_state.initialized = True
        else:
            logger.debug("Session state allerede initialisert")
            # Sjekk at nødvendige handlers fortsatt eksisterer
            if not all(
                key in st.session_state
                for key in ["db_handler", "app_handler", "auth_handler"]
            ):
                logger.warning("Manglende handlers, reinitialiserer session state")
                init_session_state()

        # Sett standardside hvis ingen er valgt
        if "current_page" not in st.session_state:
            st.session_state.current_page = "login"
            logger.debug("Satt standardside til login")

        # Vis riktig side basert på session state
        current_page = st.session_state.current_page
        logger.debug("Viser side: %s", current_page)
        render_page(current_page)

    except Exception as e:
        logger.error(f"Feil i hovedapplikasjon: {e}", exc_info=True)
        st.error("En feil oppstod i applikasjonen. Vennligst prøv igjen senere.")


if __name__ == "__main__":
    main()
