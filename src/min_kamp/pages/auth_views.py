"""
Autentisering views.
"""

import logging

import streamlit as st
from min_kamp.db.handlers.app_handler import AppHandler

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

        # Lagre bruker i query parameters
        st.query_params["bruker_id"] = str(bruker["id"])
        st.query_params["brukernavn"] = bruker["brukernavn"]
        st.rerun()

    st.markdown("---")

    if st.button("Opprett ny bruker"):
        st.query_params["vis_opprett_bruker"] = "true"
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
        st.query_params.pop("vis_opprett_bruker", None)
        st.rerun()

    st.markdown("---")

    if st.button("Tilbake til login"):
        st.query_params.pop("vis_opprett_bruker", None)
        st.rerun()


def vis_auth_side(app_handler: AppHandler) -> None:
    """Viser autentisering siden.

    Args:
        app_handler: App handler
    """
    if st.query_params.get("vis_opprett_bruker") == "true":
        vis_opprett_bruker_side(app_handler)
    else:
        vis_login_side(app_handler)
