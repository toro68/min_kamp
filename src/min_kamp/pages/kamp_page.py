"""
Kamp side.
"""

import logging
from typing import cast

import streamlit as st

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.utils.session_state import safe_get_session_state

logger = logging.getLogger(__name__)


def vis_kamp_side(app_handler: AppHandler) -> None:
    """Rendrer kamp-siden.

    Args:
        app_handler: AppHandler instans
    """
    try:
        # Sjekk autentisering
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            logger.debug("Bruker er ikke autentisert")
            return

        # Hent aktiv kamp
        current_kamp_id = safe_get_session_state("current_kamp_id")
        if not current_kamp_id or not current_kamp_id.success:
            st.warning("Ingen aktiv kamp valgt")
            return

        kamp_id = cast(int, current_kamp_id.value)
        if not kamp_id:
            st.warning("Ugyldig kamp-ID")
            return

        # Hent kamp-info
        kamp_info = app_handler.kamp_handler.hent_kamp(kamp_id)
        if not kamp_info:
            st.error("Kunne ikke hente kampinfo")
            return

        # Vis dato
        st.header(f"Dato: {kamp_info['dato']}")

        # Vis hjemme/borte
        st.subheader("Hjemmekamp" if kamp_info["hjemmebane"] else "Bortekamp")

        # Hent kamptropp
        bruker_id_result = safe_get_session_state("bruker_id")
        if not bruker_id_result or not bruker_id_result.success:
            st.error("Ingen bruker funnet")
            return
        bruker_id = cast(int, bruker_id_result.value)

        kamptropp = app_handler.kamp_handler.hent_kamptropp(kamp_id, bruker_id)
        if not kamptropp:
            st.error("Kunne ikke hente kamptropp")
            return

        # Vis antall spillere
        st.subheader("Antall spillere")
        antall = sum(
            len([s for s in spillere if s["er_med"]])
            for spillere in kamptropp["spillere"].values()
        )
        st.write(str(antall))

        # Grupper spillere etter posisjon
        keeper = kamptropp["spillere"]["Keeper"]
        forsvar = kamptropp["spillere"]["Forsvar"]
        midtbane = kamptropp["spillere"]["Midtbane"]
        angrep = kamptropp["spillere"]["Angrep"]

        # Vis spillere etter posisjon
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.subheader("Keeper")
            for spiller in keeper:
                if spiller["er_med"]:
                    st.write(f"- {spiller['navn']}")

        with col2:
            st.subheader("Forsvar")
            for spiller in forsvar:
                if spiller["er_med"]:
                    st.write(f"- {spiller['navn']}")

        with col3:
            st.subheader("Midtbane")
            for spiller in midtbane:
                if spiller["er_med"]:
                    st.write(f"- {spiller['navn']}")

        with col4:
            st.subheader("Angrep")
            for spiller in angrep:
                if spiller["er_med"]:
                    st.write(f"- {spiller['navn']}")

    except Exception as e:
        logger.error("Feil ved rendering av kamp-side: %s", e)
        st.error("En feil oppstod ved lasting av siden")
