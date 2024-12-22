"""
Hovedapplikasjon for Min Kamp - Bytteplanlegger
"""

import streamlit as st
from min_kamp.pages.bytteplan_page import vis_bytteplan_side

# Sett sidekonfigurasjon
st.set_page_config(
    page_title="Min Kamp - Bytteplanlegger",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Kjør hovedapplikasjonen
vis_bytteplan_side()
