"""
Login-side for applikasjonen
"""

import logging
import streamlit as st

logger = logging.getLogger(__name__)


def vis_login_side() -> None:
    """Viser login-siden"""
    try:
        st.title("Logg inn")

        # Hent auth_handler fra session state
        auth_handler = st.session_state.db_handler.auth_handler

        # Login form
        with st.form("login_form"):
            username = st.text_input("Brukernavn")
            password = st.text_input("Passord", type="password")

            submitted = st.form_submit_button("Logg inn")

            if submitted:
                if username and password:
                    if auth_handler.verify_credentials(username, password):
                        # Sett autentisert status
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_id = auth_handler.get_user_id(username)
                        st.session_state.current_page = "oppsett"
                        st.rerun()
                    else:
                        st.error("Feil brukernavn eller passord")
                else:
                    st.error("Vennligst fyll inn både brukernavn og passord")

        # Registreringslenke
        st.write("---")
        st.write("Har du ikke en bruker?")
        if st.button("Registrer ny bruker"):
            st.session_state.current_page = "registrer"
            st.rerun()

    except Exception as e:
        logger.error(f"Feil ved visning av login-side: {e}", exc_info=True)
        st.error("Kunne ikke vise login-siden. Vennligst prøv igjen senere.")
