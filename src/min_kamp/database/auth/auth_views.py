"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Autentiseringsviews.
Se spesielt:
- avhengigheter.md -> AuthHandler
- system.md -> AuthHandler
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import TYPE_CHECKING

import streamlit as st

from min_kamp.database.errors import DatabaseError

if TYPE_CHECKING:
    from min_kamp.database.handlers.auth_handler import AuthHandler

logger = logging.getLogger(__name__)


def vis_login_side(auth_handler: "AuthHandler") -> None:
    """
    Viser login-siden.

    Args:
        auth_handler: Handler for autentisering
    """
    st.title("Logg inn")

    # Vis registreringsknapp
    _, col2 = st.columns([4, 1])
    with col2:
        if st.button("Registrer"):
            st.session_state.show_register = True
            st.rerun()

    # Vis registreringsskjema eller login-skjema
    if st.session_state.get("show_register", False):
        vis_registrering(auth_handler)
    else:
        vis_login(auth_handler)


def vis_login(auth_handler: "AuthHandler") -> None:
    """
    Viser login-skjemaet.

    Args:
        auth_handler: Handler for autentisering
    """
    try:
        with st.form("login_form"):
            username = st.text_input("Brukernavn")
            password = st.text_input("Passord", type="password")

            if st.form_submit_button("Logg inn"):
                if not username or not password:
                    st.error("Både brukernavn og passord må fylles ut")
                    return

                try:
                    if auth_handler.authenticate(username, password):
                        user = auth_handler.get_user(username)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user["id"]
                            st.session_state.username = username
                            logger.info("Vellykket innlogging for bruker: %s", username)
                            st.success("Innlogget!")
                            st.session_state.current_page = "kamptropp"
                            st.rerun()
                        else:
                            logger.error("Kunne ikke hente brukerinformasjon")
                            st.error("En feil oppstod ved innlogging")
                    else:
                        logger.warning("Mislykket innlogging for bruker: %s", username)
                        st.error("Feil brukernavn eller passord")
                except (SQLiteError, DatabaseError) as e:
                    logger.error("Feil ved autentisering: %s", e)
                    st.error("En feil oppstod ved innlogging")

    except SQLiteError as e:
        logger.error("Feil ved visning av login-skjema: %s", e)
        st.error("En feil oppstod ved innlogging")


def vis_registrering(auth_handler: "AuthHandler") -> None:
    """
    Viser registreringsskjemaet.

    Args:
        auth_handler: Handler for autentisering
    """
    try:
        with st.form("register_form"):
            username = st.text_input("Velg brukernavn")
            password = st.text_input("Velg passord", type="password")
            password2 = st.text_input("Gjenta passord", type="password")

            if st.form_submit_button("Registrer"):
                if not username or not password:
                    st.error("Både brukernavn og passord må fylles ut")
                    return
                if password != password2:
                    st.error("Passordene må være like")
                    return

                try:
                    # Sjekk om brukeren allerede eksisterer
                    if auth_handler.get_user(username):
                        logger.warning("Bruker eksisterer allerede: %s", username)
                        st.error("Brukernavnet er allerede i bruk")
                        return

                    # Opprett ny bruker
                    user = auth_handler.create_user(username, password)
                    if user:
                        logger.info("Vellykket registrering av bruker: %s", username)
                        st.success("Registrering vellykket! Du kan nå logge inn.")
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        logger.warning(
                            "Mislykket registreringsforsøk for bruker: %s", username
                        )
                        st.error("Kunne ikke registrere bruker. Prøv igjen senere.")

                except (SQLiteError, DatabaseError) as e:
                    logger.error("Feil ved registrering av bruker: %s", e)
                    st.error("En feil oppstod ved registrering")

        # Vis tilbake-knapp
        if st.button("Tilbake til innlogging"):
            st.session_state.show_register = False
            st.rerun()

    except SQLiteError as e:
        logger.error("Feil ved visning av registreringsskjema: %s", e)
        st.error("En feil oppstod ved registrering")


def logout() -> None:
    """Håndterer utlogging av bruker"""
    try:
        if st.sidebar.button("Logg ut"):
            username = st.session_state.get("username")
            logger.info("Bruker logget ut: %s", username)

            # Nullstill state i henhold til StateHandler
            for key in [
                "user_id",
                "username",
                "current_kamp_id",
                "authenticated",
                "kamper",
                "spillere",
                "perioder",
                "spillere_per_periode",
            ]:
                if key in st.session_state:
                    del st.session_state[key]

            st.session_state.current_page = "login"
            st.rerun()

    except SQLiteError as e:
        logger.error("Feil ved utlogging: %s", e)


def check_auth(auth_handler: "AuthHandler") -> bool:
    """
    Hjelpefunksjon for å sjekke autentisering.

    Args:
        auth_handler: Handler for autentisering

    Returns:
        True hvis brukeren er autentisert, False ellers
    """
    try:
        if not st.session_state.get("authenticated"):
            logger.warning(
                "Autentisering feilet: authenticated=%s, user_id=%s",
                st.session_state.get("authenticated"),
                st.session_state.get("user_id"),
            )
            st.warning("Du må logge inn for å fortsette")
            st.session_state.current_page = "login"
            vis_login_side(auth_handler)
            return False
        return True

    except SQLiteError as e:
        logger.error("Feil ved autentiseringssjekk: %s", e)
        return False
