"""
Kamptropp utils.
"""

import logging

import streamlit as st
from min_kamp.db.handlers.app_handler import AppHandler

logger = logging.getLogger(__name__)


def hent_kamptropp(app_handler: AppHandler) -> None:
    """Henter kamptropp.

    Args:
        app_handler: App handler
    """
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

    # Vis kamptropp
    st.subheader("Kamptropp")
    for posisjon, spillere in kamptropp["spillere"].items():
        st.write(f"\n{posisjon}:")
        for spiller in spillere:
            st.write(f"- {spiller['navn']}")
