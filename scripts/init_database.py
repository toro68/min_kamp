"""
Initialiserer databasen med migrasjoner og admin-bruker.
"""

from pathlib import Path
import logging
import sys

from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner
from min_kamp.db.handlers.auth_handler import AuthHandler
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.db_config import get_db_path

# Legg til src i PYTHONPATH
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

# Sett opp logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Hovedfunksjon for å initialisere databasen."""
    try:
        # Opprett database-mappe hvis den ikke finnes
        db_path = Path(get_db_path())
        db_dir = db_path.parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True)
            logger.info("Opprettet database-mappe: %s", db_dir)

        # Initialiser database-handler
        db_handler = DatabaseHandler(str(db_path))

        # Kjør migrasjoner
        logger.info("Starter kjøring av migrasjoner...")
        migrations_dir = (
            Path(__file__).parent.parent / "src" / "min_kamp" / "db" / "migrations"
        )
        kjor_migrasjoner(db_handler, str(migrations_dir))
        logger.info("Migrasjoner fullført")

        # Opprett admin-bruker
        logger.info("Oppretter admin-bruker...")
        auth_handler = AuthHandler(db_handler)

        # Opprett admin-bruker med standard passord
        password = "admin123"  # Standard admin-passord
        try:
            user_id = auth_handler.opprett_bruker("admin", password)
            logger.info("Admin-bruker opprettet med ID: %s", user_id)
            logger.info("Standard admin-passord er: %s", password)
        except Exception as e:
            if "already exists" in str(e):
                logger.info("Admin-bruker eksisterer allerede")
            else:
                raise

        logger.info("Database-initialisering fullført")

    except Exception as e:
        logger.error("Feil ved initialisering av database: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
