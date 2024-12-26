"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Håndtering av session state i applikasjonen.
"""

import streamlit as st
from typing import Any


def initialize_state() -> None:
    """Initialiserer session state med standardverdier."""
    if "bruker_id" not in st.session_state:
        st.session_state.bruker_id = None
    if "brukernavn" not in st.session_state:
        st.session_state.brukernavn = None
    if "aktiv_kamp" not in st.session_state:
        st.session_state.aktiv_kamp = None
    if "aktiv_side" not in st.session_state:
        st.session_state.aktiv_side = "login"


def safe_get_session_state(key: str, default: Any = None) -> Any:
    """
    Henter en verdi fra session state på en sikker måte.

    Args:
        key: Nøkkelen til verdien
        default: Standardverdi hvis nøkkelen ikke finnes

    Returns:
        Verdien fra session state eller standardverdien
    """
    return getattr(st.session_state, key, default)


def safe_set_session_state(key: str, value: Any) -> None:
    """
    Setter en verdi i session state på en sikker måte.

    Args:
        key: Nøkkelen til verdien
        value: Verdien som skal settes
    """
    setattr(st.session_state, key, value)
