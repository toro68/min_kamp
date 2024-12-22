"""
Hovedapplikasjon for Min Kamp - Bytteplanlegger
"""

import streamlit as st
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.database.db_handler import DatabaseHandler
from min_kamp.database.handlers.app_handler import AppHandler
from min_kamp.database.handlers.auth_handler import AuthHandler

# Sett sidekonfigurasjon
st.set_page_config(
    page_title="Min Kamp - Bytteplanlegger",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialiser handlers
if "db_handler" not in st.session_state:
    st.session_state.db_handler = DatabaseHandler()

if "auth_handler" not in st.session_state:
    st.session_state.auth_handler = AuthHandler(st.session_state.db_handler)

if "app_handler" not in st.session_state:
    st.session_state.app_handler = AppHandler(st.session_state.db_handler)

# Kjør hovedapplikasjonen
vis_bytteplan_side()
