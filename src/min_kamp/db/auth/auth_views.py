"""
Auth views.
"""

import logging

import streamlit as st

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.handlers.auth_handler import AuthHandler
from min_kamp.utils.session_state import safe_get_session_state
from min_kamp.utils.streamlit_utils import set_session_state

logger = logging.getLogger(__name__)


def check_auth(auth_handler: AuthHandler) -> bool:
    """Sjekker om bruker er autentisert.

    Args:
        auth_handler: AuthHandler instans

    Returns:
        bool: True hvis bruker er autentisert
    """
    bruker_state = safe_get_session_state("bruker_id")
    if not bruker_state or not bruker_state.success:
        return False

    bruker_id = bruker_state.value
    if not bruker_id:
        return False

    bruker = auth_handler.hent_bruker(bruker_id)
    return bruker is not None


def vis_login_side(app_handler: AppHandler) -> None:
    """Viser login-siden.

    Args:
        app_handler: AppHandler instans
    """
    logger.info("Starter visning av login-side")

    st.title("Logg inn")

    # Vis innloggingsskjema
    with st.form("login_form"):
        brukernavn = st.text_input("Brukernavn")
        passord = st.text_input("Passord", type="password")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Logg inn")
        with col2:
            register = st.form_submit_button("Registrer")

    if submit and brukernavn and passord:
        bruker = app_handler.auth_handler.sjekk_passord(brukernavn, passord)
        if bruker:
            set_session_state("bruker_id", bruker["id"])
            st.success("Innlogget!")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord")

    elif register and brukernavn and passord:
        bruker_id = app_handler.auth_handler.opprett_bruker(brukernavn, passord)
        if bruker_id:
            set_session_state("bruker_id", bruker_id)
            st.success("Bruker opprettet!")
            st.rerun()
        else:
            st.error("Kunne ikke opprette bruker")
