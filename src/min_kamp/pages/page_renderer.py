"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging

import streamlit as st

from min_kamp.database.auth.auth_views import vis_login_side, check_auth
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.kamp_page import vis_kamp_side
from min_kamp.pages.kamptropp_page import vis_kamptropp_side
from min_kamp.pages.oppsett_page import render_oppsett_page
from min_kamp.pages.statistikk_page import vis_statistikk_side
from min_kamp.utils.sidebar import setup_sidebar

logger = logging.getLogger(__name__)


def render_page(page: str) -> None:
    """
    Rendrer den valgte siden.

    Args:
        page: Navnet på siden som skal vises
    """
    logger.info("Rendrer side: %s", page)

    # Hent auth_handler fra session state
    auth_handler = st.session_state.auth_handler

    # Sett opp sidebar
    setup_sidebar()

    # Definer gyldige sider og deres visningsfunksjoner
    gyldige_sider = {
        "oppsett": render_oppsett_page,
        "kamptropp": vis_kamptropp_side,
        "bytteplan": vis_bytteplan_side,
        "kamp": vis_kamp_side,
        "statistikk": vis_statistikk_side,
        "login": lambda: vis_login_side(auth_handler),
    }

    if page not in gyldige_sider:
        logger.error("Ugyldig side: %s", page)
        st.error(f"Ugyldig side: {page}")
        st.session_state.current_page = "login"
        st.rerun()
        return

    # Sjekk autentisering for alle sider unntatt login
    if page != "login":
        if not check_auth(auth_handler):
            logger.warning("Bruker ikke autentisert, omdirigerer til login")
            st.session_state.current_page = "login"
            st.rerun()
            return

    # Vis valgt side
    try:
        gyldige_sider[page]()
    except Exception as e:
        logger.error("Feil ved visning av side %s: %s", page, e, exc_info=True)
        st.error(f"Kunne ikke vise siden {page}. Vennligst prøv igjen senere.")
        if st.session_state.get("debug_mode"):
            st.exception(e)
