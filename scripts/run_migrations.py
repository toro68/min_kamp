#!/usr/bin/env python3
"""
Kjører databasemigrasjoner.
"""

import logging

from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.migrations.migrations_handler import kjor_migrasjoner

# Logging oppsett
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Hovedfunksjon som kjører migrasjonene."""
    try:
        logger.info("Starter kjøring av migrasjoner")
        database_path = "database/kampdata.db"
        db_handler = DatabaseHandler(database_path=database_path)
        migrasjoner_mappe = "src/min_kamp/db/migrations"
        kjor_migrasjoner(db_handler, migrasjoner_mappe)
        logger.info("Migrasjoner fullført")

        # Vis status
        # Merk: Status-visning er ikke tilgjengelig med kjor_migrasjoner-
        # funksjonen. Fjernet kode for å vise status.

    except Exception as e:
        logger.error("Feil ved kjøring av migrasjoner: %s", e)
        raise


if __name__ == "__main__":
    main()
