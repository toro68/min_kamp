"""
Rendrer sider i applikasjonen.
"""

import logging
import streamlit as st

from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.kamptropp_page import vis_kamptropp_side
from min_kamp.pages.kamp_page import vis_kamp_side
from min_kamp.pages.login_page import vis_login_side
from min_kamp.pages.oppsett_page import render_oppsett_page

logger = logging.getLogger(__name__)


# Mapping av sider til funksjoner
PAGES = {
    "login": vis_login_side,
    "kamptropp": vis_kamptropp_side,
    "bytteplan": vis_bytteplan_side,
    "kamp": vis_kamp_side,
    "oppsett": render_oppsett_page,
}


def render_page(page_name: str, **kwargs) -> None:
    """Rendrer en side basert på navnet.

    Args:
        page_name: Navnet på siden som skal rendres
        **kwargs: Argumenter som skal sendes til sidefunksjonen
    """
    try:
        if page_name not in PAGES:
            logger.error(f"Ukjent side: {page_name}")
            st.error(f"Fant ikke siden: {page_name}")
            return

        page_func = PAGES[page_name]
        page_func(**kwargs)
    except Exception as e:
        logger.error(f"Feil ved rendering av {page_name}: {e}")
        st.error("En feil oppstod ved lasting av siden")
