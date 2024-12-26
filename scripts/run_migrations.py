#!/usr/bin/env python3
"""
Kjører databasemigrasjoner.
"""

import logging
from min_kamp.db.migrations.migrations_handler import MigrationsHandler

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
        migrations_handler = MigrationsHandler()
        migrations_handler.run_migrations()
        logger.info("Migrasjoner fullført")

        # Vis status
        status = migrations_handler.get_migration_status()
        logger.info("\nMigrasjonsstatus:")
        for migration in status:
            logger.info(
                "%s: %s (fil eksisterer: %s)",
                migration["name"],
                "Kjørt" if migration["is_applied"] else "Ikke kjørt",
                migration["file_exists"],
            )

    except Exception as e:
        logger.error("Feil ved kjøring av migrasjoner: %s", e)
        raise


if __name__ == "__main__":
    main()
