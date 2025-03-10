"""
Streamlit app for Min Kamp.

Trigger redeploy på Streamlit Cloud.
"""

import logging
import os
import platform
import sys
from pathlib import Path

import streamlit as st

# Sett opp Streamlit-siden - må være første Streamlit-kommando
st.set_page_config(
    page_title="Min Kamp",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Legg til prosjektmappen og src-mappen i Python-stien
project_root = str(Path(__file__).parent)
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

from min_kamp.config.logging_config import configure_logging
from min_kamp.db.auth.auth_views import check_auth, vis_login_side
from min_kamp.db.db_config import get_db_path
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.pages.bytteplan_page import vis_bytteplan_side
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.formation_page import vis_formasjon_side
from min_kamp.pages.kamp_page import vis_kamp_side
from min_kamp.pages.kamptropp_page import vis_kamptropp_side
from min_kamp.pages.oppsett_page import vis_oppsett_side

# Debug-informasjon
configure_logging()
logging.debug("=== System Info ===")
logging.debug(f"Platform: {platform.platform()}")
logging.debug(f"Python version: {sys.version}")
logging.debug(f"Current working directory: {os.getcwd()}")
logging.debug(f"Environment variables: {dict(os.environ)}")

logging.debug("\n=== Path Info ===")
logging.debug(f"Project root: {project_root}")
logging.debug(f"Src path: {src_path}")
logging.debug(f"Python path: {sys.path}")

# Sjekk mappestruktur
logging.debug("\n=== Directory Structure ===")
if os.path.exists(src_path):
    logging.debug(f"{src_path} eksisterer")
    logging.debug(f"Innhold: {os.listdir(src_path)}")
if os.path.exists(os.path.join(src_path, "min_kamp")):
    logging.debug(f"{os.path.join(src_path, 'min_kamp')} eksisterer")
    logging.debug(f"Innhold: {os.listdir(os.path.join(src_path, 'min_kamp'))}")

# Sett opp database-stier
database_path = get_db_path()
migrasjoner_mappe = os.path.join(src_path, "min_kamp", "db", "migrations")

logging.debug("\n=== Database Setup ===")
logging.debug(f"Database path: {database_path}")
logging.debug(f"Migrasjoner mappe: {migrasjoner_mappe}")


# Opprett databasetilkobling
@st.cache_resource
def get_database_handler(db_path):
    """Henter en cached DatabaseHandler-instans.

    Args:
        db_path: Sti til databasefilen

    Returns:
        DatabaseHandler: En instans av DatabaseHandler
    """
    logging.debug(f"Oppretter ny DatabaseHandler for {db_path}")
    return DatabaseHandler(db_path)


db_handler = get_database_handler(database_path)
app_handler = AppHandler(db_handler)

# Kjør migrasjoner
logging.debug("Kjører migrasjoner...")
kjor_migrasjoner(db_handler, migrasjoner_mappe)
logging.debug("Migrasjoner fullført")

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
st.title("Min Kamp")

# Vis valgt side basert på query parameters
selected_page = st.query_params.get("page", "oppsett")
logging.debug(f"Viser side: {selected_page}")

if selected_page == "oppsett":
    vis_oppsett_side(app_handler)
elif selected_page == "kamptropp":
    vis_kamptropp_side(app_handler)
elif selected_page == "kamp":
    vis_kamp_side(app_handler)
elif selected_page == "bytteplan":
    vis_bytteplan_side(app_handler)
elif selected_page == "formasjon":
    vis_formasjon_side(app_handler)

logging.debug("Side rendret")
logging.debug("App ferdig lastet")
