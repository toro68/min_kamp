"""
Streamlit utils.
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def set_query_param(key: str, value: str) -> None:
    """Setter en query parameter.

    Args:
        key: Nøkkel
        value: Verdi
    """
    st.query_params[key] = value


def get_query_param(key: str) -> Optional[str]:
    """Henter en query parameter.

    Args:
        key: Nøkkel

    Returns:
        Verdien til query parameteren eller None hvis den ikke finnes
    """
    return st.query_params.get(key)
