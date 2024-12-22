"""Håndterer sidebar-funksjonalitet"""

import logging
import streamlit as st

logger = logging.getLogger(__name__)


def setup_sidebar() -> None:
    """Setter opp sidebar med navigasjon og brukerinfo"""
    try:
        with st.sidebar:
            st.title("Min Kamp")

            # Vis brukerinfo hvis innlogget
            if st.session_state.get("authenticated"):
                st.write(f"Innlogget som: {st.session_state.get('username', 'Ukjent')}")

                # Navigasjonsknapper
                if st.button("Oppsett"):
                    st.session_state.current_page = "oppsett"
                    st.rerun()

                if st.button("Kamptropp"):
                    st.session_state.current_page = "kamptropp"
                    st.rerun()

                if st.button("Bytteplan"):
                    st.session_state.current_page = "bytteplan"
                    st.rerun()

                # Logg ut knapp nederst
                st.write("---")
                if st.button("Logg ut"):
                    # Reset session state
                    for key in ["authenticated", "username", "user_id"]:
                        if key in st.session_state:
                            st.session_state[key] = None
                    st.session_state.current_page = "login"
                    st.rerun()

    except Exception as e:
        logger.error(f"Feil ved oppsett av sidebar: {e}", exc_info=True)
        st.error("Kunne ikke sette opp navigasjonsmeny")
