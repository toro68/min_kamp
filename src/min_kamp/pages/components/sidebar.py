"""
Sidebar-komponent for navigasjon.
"""

import logging

import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.handlers.app_handler import AppHandler

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

            # Hent gjeldende side, kamp ID og bruker ID fra query parameters
            selected_page = st.query_params.get("page", "oppsett")
            kamp_id = st.query_params.get("kamp_id")
            bruker_id = st.query_params.get("bruker_id")

            if not bruker_id:
                logger.warning("Ingen bruker_id i query parameters")
                st.error("Ingen bruker funnet")
                return

            # Navigasjonsknapper
            is_active = selected_page == "oppsett"
            btn_type = "primary" if is_active else "secondary"
            if st.button("Oppsett", type=btn_type):
                query_params = {"page": "oppsett"}
                if kamp_id:
                    query_params["kamp_id"] = kamp_id
                query_params["bruker_id"] = bruker_id
                st.query_params.update(query_params)
                st.rerun()

            is_active = selected_page == "kamptropp"
            btn_type = "primary" if is_active else "secondary"
            if st.button("Kamptropp", type=btn_type):
                query_params = {"page": "kamptropp"}
                if kamp_id:
                    query_params["kamp_id"] = kamp_id
                query_params["bruker_id"] = bruker_id
                st.query_params.update(query_params)
                st.rerun()

            is_active = selected_page == "kamp"
            btn_type = "primary" if is_active else "secondary"
            if st.button("Kamp", type=btn_type):
                query_params = {"page": "kamp"}
                if kamp_id:
                    query_params["kamp_id"] = kamp_id
                query_params["bruker_id"] = bruker_id
                st.query_params.update(query_params)
                st.rerun()

            is_active = selected_page == "bytteplan"
            btn_type = "primary" if is_active else "secondary"
            if st.button("Bytteplan", type=btn_type):
                query_params = {"page": "bytteplan"}
                if kamp_id:
                    query_params["kamp_id"] = kamp_id
                query_params["bruker_id"] = bruker_id
                st.query_params.update(query_params)
                st.rerun()

            is_active = selected_page == "formasjon"
            btn_type = "primary" if is_active else "secondary"
            if st.button("Formasjon", type=btn_type):
                query_params = {"page": "formasjon"}
                if kamp_id:
                    query_params["kamp_id"] = kamp_id
                query_params["bruker_id"] = bruker_id
                st.query_params.update(query_params)
                st.rerun()

            # Logg ut-knapp
            if st.button("Logg ut"):
                auth_handler.logg_ut()
                st.rerun()

    except Exception as e:
        logger.error("Feil ved oppsett av sidebar: %s", e)
        st.error("En feil oppstod ved lasting av navigasjon")
