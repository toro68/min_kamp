"""
Streamlit app for Min Kamp.
"""

import logging
import os
import sys
import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.oppsett_page import vis_oppsett_side

# Legg til prosjektets rot-mappe i Python-stien
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))

# Sett opp logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%f",
)

# Initialiser database og handlers
database_path = os.path.join("database", "kampdata.db")
migrasjoner_mappe = os.path.join("src", "min_kamp", "db", "migrations")

db_handler = DatabaseHandler(database_path)
app_handler = AppHandler(db_handler)

# Kjør migrasjoner
kjor_migrasjoner(db_handler, migrasjoner_mappe)

# Sett opp Streamlit-siden
st.set_page_config(
    page_title="Min Kamp",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sjekk autentisering
if not check_auth(app_handler.auth_handler):
    st.stop()

# Vis hovedside
st.title("Min Kamp")

# Sett opp sidebar
setup_sidebar(app_handler)

# Vis valgt side
valgt_side = st.session_state.get("current_page", "oppsett")
st.write(f"Viser valgt side: {valgt_side}")

if valgt_side == "oppsett":
    vis_oppsett_side(app_handler)
elif valgt_side == "bytteplan":
    vis_bytteplan_side(app_handler)
