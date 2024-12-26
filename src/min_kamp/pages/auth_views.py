"""
Autentisering views.
"""

import logging
import streamlit as st

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.utils.session_state import safe_get_session_state

logger = logging.getLogger(__name__)


def vis_login_side(app_handler: AppHandler) -> None:
    """Viser login siden.

    Args:
        app_handler: App handler
    """
    st.title("Logg inn")

    brukernavn = st.text_input("Brukernavn")
    passord = st.text_input("Passord", type="password")

    if st.button("Logg inn"):
        if not brukernavn or not passord:
            st.error("Vennligst fyll inn brukernavn og passord")
            return

        bruker = app_handler.auth_handler.sjekk_passord(brukernavn, passord)
        if not bruker:
            st.error("Feil brukernavn eller passord")
            return

        # Lagre bruker i session state
        st.session_state["bruker_id"] = bruker["id"]
        st.session_state["brukernavn"] = bruker["brukernavn"]
        st.rerun()

    st.markdown("---")

    if st.button("Opprett ny bruker"):
        st.session_state["vis_opprett_bruker"] = True
        st.rerun()


def vis_opprett_bruker_side(app_handler: AppHandler) -> None:
    """Viser siden for å opprette ny bruker.

    Args:
        app_handler: App handler
    """
    st.title("Opprett ny bruker")

    brukernavn = st.text_input("Brukernavn")
    passord = st.text_input("Passord", type="password")
    bekreft_passord = st.text_input("Bekreft passord", type="password")

    if st.button("Opprett bruker"):
        if not brukernavn or not passord or not bekreft_passord:
            st.error("Vennligst fyll inn alle feltene")
            return

        if passord != bekreft_passord:
            st.error("Passordene er ikke like")
            return

        bruker_id = app_handler.auth_handler.opprett_bruker(
            brukernavn=brukernavn, passord=passord
        )
        if not bruker_id:
            st.error("Kunne ikke opprette bruker")
            return

        st.success("Bruker opprettet!")
        st.session_state["vis_opprett_bruker"] = False
        st.rerun()

    st.markdown("---")

    if st.button("Tilbake til login"):
        st.session_state["vis_opprett_bruker"] = False
        st.rerun()


def vis_auth_side(app_handler: AppHandler) -> None:
    """Viser autentisering siden.

    Args:
        app_handler: App handler
    """
    if safe_get_session_state("vis_opprett_bruker", False):
        vis_opprett_bruker_side(app_handler)
    else:
        vis_login_side(app_handler)
