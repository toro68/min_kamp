"""
Auth views.
"""

import logging

import streamlit as st
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.handlers.auth_handler import AuthHandler

logger = logging.getLogger(__name__)


def check_auth(auth_handler: AuthHandler) -> bool:
    """Sjekker om bruker er autentisert.

    Args:
        auth_handler: AuthHandler instans

    Returns:
        bool: True hvis bruker er autentisert
    """
    bruker_id_str = st.query_params.get("bruker_id")
    if not bruker_id_str:
        return False

    try:
        bruker_id = int(bruker_id_str)
    except (ValueError, TypeError):
        return False

    bruker = auth_handler.hent_bruker(bruker_id)
    return bruker is not None


def vis_login_side(app_handler: AppHandler) -> None:
    """Viser login-siden.

    Args:
        app_handler: AppHandler instans
    """
    logger.info("Starter visning av login-side")

    tab1, tab2 = st.tabs(["Logg inn", "Registrer ny bruker"])

    with tab1:
        st.header("Logg inn")
        with st.form("login_form"):
            brukernavn = st.text_input("Brukernavn")
            passord = st.text_input("Passord", type="password")
            submit = st.form_submit_button("Logg inn")

            if submit and brukernavn and passord:
                bruker = app_handler.auth_handler.sjekk_passord(brukernavn, passord)
                if bruker:
                    st.query_params["bruker_id"] = str(bruker["id"])
                    st.success("Innlogget!")
                    st.rerun()
                else:
                    st.error("Feil brukernavn eller passord")

    with tab2:
        st.header("Registrer ny bruker")
        with st.form("register_form"):
            nytt_brukernavn = st.text_input("Velg brukernavn")
            nytt_passord = st.text_input("Velg passord", type="password")
            bekreft_passord = st.text_input("Bekreft passord", type="password")
            register = st.form_submit_button("Registrer")

            if register:
                if not nytt_brukernavn or not nytt_passord:
                    st.error("Du må fylle ut både brukernavn og passord")
                elif nytt_passord != bekreft_passord:
                    st.error("Passordene må være like")
                else:
                    bruker_id = app_handler.auth_handler.opprett_bruker(
                        nytt_brukernavn, nytt_passord
                    )
                    if bruker_id:
                        st.query_params["bruker_id"] = str(bruker_id)
                        st.success("Bruker opprettet!")
                        st.rerun()
                    else:
                        st.error(
                            "Kunne ikke opprette bruker. "
                            "Brukernavnet kan være opptatt."
                        )
