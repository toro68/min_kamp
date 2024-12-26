"""
Streamlit app for Min Kamp.
"""

import logging
import os
import sys
import streamlit as st

# Sett opp Streamlit-siden (må være første Streamlit-kommando)
st.set_page_config(
    page_title="Min Kamp",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Legg til prosjektets rot-mappe i Python-stien
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")

# Fjern eventuelle duplikate stier og legg til src-mappen først
sys.path = list(dict.fromkeys([src_path] + sys.path))

# Skriv ut debug-informasjon
st.write("Debug info:")
st.write(f"Project root: {project_root}")
st.write(f"Src path: {src_path}")
st.write(f"Python path: {sys.path}")
st.write("Listing av src-mappe:")
if os.path.exists(src_path):
    st.write(os.listdir(src_path))

# Nå kan vi importere min_kamp-modulene
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.oppsett_page import vis_oppsett_side

# Sett opp logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%f",
)

# Initialiser database og handlers
database_dir = os.path.join(project_root, "database")
database_path = os.path.join(database_dir, "kampdata.db")
migrations_dir = os.path.join(project_root, "src", "min_kamp", "db", "migrations")

# Opprett database-mappen hvis den ikke eksisterer
os.makedirs(database_dir, exist_ok=True)

db_handler = DatabaseHandler(database_path)
app_handler = AppHandler(db_handler)

# Kjør migrasjoner
kjor_migrasjoner(db_handler, migrations_dir)

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
