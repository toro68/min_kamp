"""
Streamlit app for Min Kamp.
"""

import logging
import os
import sys
import streamlit as st
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.oppsett_page import vis_oppsett_side

# Legg til prosjektets rot-mappe i Python-stien
if os.path.exists("/mount/src/min_kamp"):
    # På Streamlit Cloud
    project_root = "/mount/src/min_kamp"
else:
    # Lokalt miljø
    project_root = os.path.dirname(os.path.abspath(__file__))

# Fjern eventuelle duplikate stier fra sys.path
existing_paths = set()
new_sys_path = []
for path in sys.path:
    if path not in existing_paths and path != "streamlit_app.py":
        existing_paths.add(path)
        new_sys_path.append(path)
sys.path = new_sys_path

# Legg til src-mappen i Python-stien
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Skriv ut debug-informasjon før import
print("Debug info før import:")
print(f"Project root: {project_root}")
print(f"Src path: {src_path}")
print(f"Python path: {sys.path}")
print("Listing av src-mappe:")
if os.path.exists(src_path):
    print(os.listdir(src_path))
    print("Listing av min_kamp-mappe:")
    min_kamp_path = os.path.join(src_path, "min_kamp")
    if os.path.exists(min_kamp_path):
        print(os.listdir(min_kamp_path))
        print("Listing av db-mappe:")
        db_path = os.path.join(min_kamp_path, "db")
        if os.path.exists(db_path):
            print(os.listdir(db_path))
        else:
            print("db-mappe finnes ikke")
    else:
        print("min_kamp-mappe finnes ikke")
else:
    print("src-mappe finnes ikke")

# Sett opp logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%f",
)

# Initialiser database og handlers
database_dir = os.path.join(project_root, "database")
database_path = os.path.join(database_dir, "kampdata.db")
migrations_dir = os.path.join(
    project_root, "src", "min_kamp", "db", "migrations"
)

# Opprett database-mappen hvis den ikke eksisterer
os.makedirs(database_dir, exist_ok=True)

# Skriv ut debug-informasjon
st.write("Debug info:")
st.write(f"Project root: {project_root}")
st.write(f"Database path: {database_path}")
st.write(f"Migrations dir: {migrations_dir}")
st.write(f"Python path: {sys.path}")
st.write("Listing av src-mappe:")
if os.path.exists(os.path.join(project_root, "src")):
    st.write(os.listdir(os.path.join(project_root, "src")))
else:
    st.write("src-mappe finnes ikke")

db_handler = DatabaseHandler(database_path)
app_handler = AppHandler(db_handler)

# Kjør migrasjoner
kjor_migrasjoner(db_handler, migrations_dir)

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
