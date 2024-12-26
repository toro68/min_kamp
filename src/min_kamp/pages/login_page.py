"""
Login-side for applikasjonen
"""

import logging
import streamlit as st
from min_kamp.db.auth.auth_views import vis_login_side as vis_login_skjema
from min_kamp.db.handlers.app_handler import AppHandler

logger = logging.getLogger(__name__)


def vis_login_side(app_handler: AppHandler) -> None:
    """Viser login-siden.

    Args:
        app_handler: AppHandler instans
    """
    try:
        if not isinstance(app_handler, AppHandler):
            logger.error("Ugyldig app_handler type: %s", type(app_handler))
            st.error("En feil oppstod ved lasting av login-siden")
            return

        # Vis login-side med app_handler
        vis_login_skjema(app_handler)

    except Exception as e:
        logger.error("Feil ved visning av login-side: %s", e)
        st.error("En feil oppstod ved lasting av login-siden")
