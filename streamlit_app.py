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

# Initialiser session state variabler
if "user_id" not in st.session_state:
    st.session_state.user_id = 1  # Midlertidig bruker-ID for testing

# Kjør hovedapplikasjonen
st.title("Min Kamp - Bytteplanlegger")
st.write("Velkommen til bytteplanleggeren!")

try:
    vis_bytteplan_side()
except Exception as e:
    st.error(f"En feil oppstod: {str(e)}")
    st.write("Vi jobber med å løse problemet.")
