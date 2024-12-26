"""
Sidebar-komponent for navigasjon.
"""

import logging
import streamlit as st

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.auth.auth_views import check_auth

logger = logging.getLogger(__name__)


def setup_sidebar(app_handler: AppHandler) -> None:
    """Setter opp sidebar med navigasjon.

    Args:
        app_handler: AppHandler instans
    """
    try:
        # Sjekk at app_handler er gyldig
        if not isinstance(app_handler, AppHandler):
            logger.error("Ugyldig app_handler type: %s", type(app_handler))
            st.error("Applikasjonen er ikke riktig initialisert")
            return

        # Sjekk autentisering
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            logger.debug("Bruker er ikke autentisert")
            return

        with st.sidebar:
            st.title("Min Kamp")

            # Hent gjeldende side fra session state
            selected_page = st.session_state.get("selected_page", "oppsett")

            # Navigasjonsknapper
            if st.button(
                "Oppsett", type="primary" if selected_page == "oppsett" else "secondary"
            ):
                st.session_state.selected_page = "oppsett"
                st.rerun()

            if st.button(
                "Kamptropp",
                type="primary" if selected_page == "kamptropp" else "secondary",
            ):
                st.session_state.selected_page = "kamptropp"
                st.rerun()

            if st.button(
                "Kamp", type="primary" if selected_page == "kamp" else "secondary"
            ):
                st.session_state.selected_page = "kamp"
                st.rerun()

            if st.button(
                "Bytteplan",
                type="primary" if selected_page == "bytteplan" else "secondary",
            ):
                st.session_state.selected_page = "bytteplan"
                st.rerun()

            # Logg ut-knapp
            if st.button("Logg ut"):
                auth_handler.logg_ut()
                st.rerun()

    except Exception as e:
        logger.error("Feil ved oppsett av sidebar: %s", e)
        st.error("En feil oppstod ved lasting av navigasjon")
