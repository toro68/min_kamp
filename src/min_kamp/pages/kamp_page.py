"""
Kamp side.
"""

import logging

import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.handlers.app_handler import AppHandler

logger = logging.getLogger(__name__)


def vis_kamp_side(app_handler: AppHandler) -> None:
    """Viser kamp siden.

    Args:
        app_handler: App handler
    """
    if not check_auth(app_handler.auth_handler):
        return

    st.title("Kamp")

    # Hent kamp ID fra query parameters
    kamp_id = st.query_params.get("kamp_id")
    if not kamp_id:
        st.warning("Ingen kamp valgt")
        return

    try:
        kamp_id = int(kamp_id)
    except ValueError:
        st.error("Ugyldig kamp ID")
        return

    kamp = app_handler.kamp_handler.hent_kamp(kamp_id)
    if not kamp:
        st.error(f"Fant ikke kamp med ID {kamp_id}")
        return

    st.write(f"Motstander: {kamp['motstander']}")
    st.write(f"Dato: {kamp['dato']}")
    st.write(f"Type: {'Hjemmekamp' if kamp['hjemmebane'] else 'Bortekamp'}")

    # Hent bruker ID fra query parameters
    bruker_id = st.query_params.get("bruker_id")
    if not bruker_id:
        st.error("Ingen bruker funnet")
        return

    try:
        bruker_id = int(bruker_id)
    except ValueError:
        st.error("Ugyldig bruker ID")
        return

    # Hent kamptropp
    kamptropp = app_handler.kamp_handler.hent_kamptropp(kamp_id, bruker_id)
    if not kamptropp:
        st.error("Kunne ikke hente kamptropp")
        return

    # Vis spillere etter posisjon
    st.header("Kamptropp")
    for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
        st.subheader(posisjon)
        spillere = kamptropp["spillere"][posisjon]
        for spiller in spillere:
            if spiller["er_med"]:
                st.write(f"- {spiller['navn']}")
