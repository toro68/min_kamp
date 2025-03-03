"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for Min Kamp.
Se spesielt:
- avhengigheter.md -> Frontend -> App
- system.md -> Frontend -> App
"""

import logging
import os

from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.pages.components.sidebar import setup_sidebar
from min_kamp.pages.page_renderer import render_page
from streamlit import error as st_error
from streamlit import set_page_config

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s - %(name)s - " "%(levelname)s - %(message)s"),
)
logger = logging.getLogger(__name__)


def setup_streamlit() -> None:
    """Setter opp Streamlit-konfigurasjon."""
    set_page_config(
        page_title="Min Kamp",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def main() -> None:
    """Hovedfunksjon for applikasjonen."""
    try:
        # Sett opp Streamlit
        setup_streamlit()

        # Opprett app_handler
        database_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "database", "kampdata.db"
        )
        db_handler = DatabaseHandler(database_path=database_path)

        # Kjør migrasjoner
        migrasjoner_mappe = os.path.join(
            os.path.dirname(__file__), "..", "db", "migrations"
        )
        kjor_migrasjoner(db_handler, migrasjoner_mappe)

        app_handler = AppHandler(db_handler)

        # Sjekk autentisering og vis login-side hvis ikke autentisert
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            logger.debug("Bruker ikke autentisert, viser login-side")
            render_page("login", app_handler=app_handler)
            return

        # Setup sidebar med app_handler
        setup_sidebar(app_handler=app_handler)

    except Exception as e:
        err_msg = f"Kritisk feil i hovedapplikasjon: {str(e)}"
        logger.error(err_msg, exc_info=True)
        st_error("En feil oppstod i applikasjonen. Vennligst prøv igjen senere.")


if __name__ == "__main__":
    main()
