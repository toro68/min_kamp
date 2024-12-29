"""
Streamlit app for Min Kamp.
"""

import logging
import os
import sys
import platform
import streamlit as st

# Legg til prosjektmappen og src-mappen i Python-stien
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importer etter at stiene er satt opp
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.db.auth.auth_views import check_auth, vis_login_side
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.oppsett_page import vis_oppsett_side
from min_kamp.pages.kamptropp_page import vis_kamptropp_side
from min_kamp.pages.kamp_page import vis_kamp_side

# Sett opp stier
min_kamp_path = os.path.join(src_path, "min_kamp")
db_path = os.path.join(min_kamp_path, "db")

# Debug-informasjon
logging.basicConfig(level=logging.DEBUG)
logging.debug("=== System Info ===")
logging.debug(f"Platform: {platform.platform()}")
logging.debug(f"Python version: {sys.version}")
logging.debug(f"Current working directory: {os.getcwd()}")
logging.debug(f"Environment variables: {dict(os.environ)}")

logging.debug("\n=== Path Info ===")
logging.debug(f"Project root: {project_root}")
logging.debug(f"Src path: {src_path}")
logging.debug(f"Min Kamp path: {min_kamp_path}")
logging.debug(f"Python path: {sys.path}")

# Sjekk mappestruktur
logging.debug("\n=== Directory Structure ===")
if os.path.exists(src_path):
    logging.debug(f"{src_path} eksisterer")
    logging.debug(f"Innhold: {os.listdir(src_path)}")
if os.path.exists(min_kamp_path):
    logging.debug(f"{min_kamp_path} eksisterer")
    logging.debug(f"Innhold: {os.listdir(min_kamp_path)}")
if os.path.exists(db_path):
    logging.debug(f"DB path: {db_path}")
    logging.debug(f"DB innhold: {os.listdir(db_path)}")

# Sett opp database-stier
database_path = os.path.join(project_root, "database", "kampdata.db")
migrasjoner_mappe = os.path.join(min_kamp_path, "db", "migrations")

# Opprett databasetilkobling
logging.debug("\n=== Database Setup ===")
logging.debug(f"Oppretter DatabaseHandler med sti: {database_path}")
db_handler = DatabaseHandler(database_path)
app_handler = AppHandler(db_handler)

# Kjør migrasjoner
logging.debug("Kjører migrasjoner...")
kjor_migrasjoner(db_handler, migrasjoner_mappe)
logging.debug("Migrasjoner fullført")

# Sett opp Streamlit-siden
logging.debug("\n=== Streamlit Setup ===")
st.set_page_config(
    page_title="Min Kamp",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sjekk autentisering
logging.debug("Sjekker autentisering...")
auth_result = check_auth(app_handler.auth_handler)
logging.debug(f"Autentisering resultat: {auth_result}")

if not auth_result:
    logging.debug("Viser login-side")
    vis_login_side(app_handler)
    st.stop()

# Sett opp sidebar
logging.debug("Setter opp sidebar...")
setup_sidebar(app_handler)
logging.debug("Sidebar satt opp")

# Vis hovedsiden
logging.debug("Setter opp hovedsiden...")
st.title("Min Kamp")

# Vis valgt side basert på session state
selected_page = st.session_state.get("selected_page", "oppsett")
logging.debug(f"Viser side: {selected_page}")

if selected_page == "oppsett":
    vis_oppsett_side(app_handler)
elif selected_page == "kamptropp":
    vis_kamptropp_side(app_handler)
elif selected_page == "kamp":
    vis_kamp_side(app_handler)
elif selected_page == "bytteplan":
    vis_bytteplan_side(app_handler)

logging.debug("Side rendret")
logging.debug("App ferdig lastet")
