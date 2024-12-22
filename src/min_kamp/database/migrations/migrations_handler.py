"""
Håndterer databasemigrasjoner
"""

import logging
from pathlib import Path
from typing import Any, List, Optional

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class MigrationsHandler(BaseHandler):
    """Handler for databasemigrasjoner.

    Denne klassen håndterer kjøring og sporing av databasemigrasjoner.
    """

    def __init__(self, db_handler: Any) -> None:
        """Initialiserer migrations handler.

        Args:
            db_handler: Database handler
        """
        super().__init__(db_handler)
        self._init_migrations_table()

    def _init_migrations_table(self) -> None:
        """Initialiserer migrations-tabellen"""
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.db_handler.commit()
        except Exception as e:
            logger.error("Feil ved initialisering av migrations-tabell: %s", e)
            raise DatabaseError("Kunne ikke initialisere migrations-tabell") from e

    def get_applied_migrations(self) -> List[str]:
        """Henter liste over anvendte migrasjoner.

        Returns:
            Liste med navn på anvendte migrasjoner.

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute("SELECT name FROM migrations ORDER BY id")
            return [row["name"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Feil ved henting av anvendte migrasjoner: %s", e)
            raise DatabaseError("Kunne ikke hente anvendte migrasjoner") from e

    def apply_migration(self, name: str, sql: str) -> bool:
        """Kjører en enkelt migrasjon.

        Args:
            name: Navn på migrasjonen
            sql: SQL-spørringen som skal kjøres

        Returns:
            True hvis migrasjonen ble kjørt vellykket, False ellers
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.executescript(sql)
            cursor.execute("INSERT INTO migrations (name) VALUES (?)", (name,))
            self.db_handler.commit()
            logger.info("Anvendte migrasjon: %s", name)
            return True
        except Exception as e:
            logger.error("Feil ved kjøring av migrasjon %s: %s", name, e)
            return False

    def run_migrations(self, migrations_dir: Optional[Path] = None) -> bool:
        """Kjører alle ventende migrasjoner.

        Args:
            migrations_dir: Mappe med migrasjonsfiler. Hvis None, brukes standard mappe.

        Returns:
            True hvis alle migrasjoner ble kjørt vellykket, False ellers
        """
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent / "sql"

        try:
            applied = set(self.get_applied_migrations())
            migration_files = sorted(migrations_dir.glob("*.sql"))

            for migration_file in migration_files:
                if migration_file.name not in applied:
                    logger.info("Kjører migrasjon: %s", migration_file.name)
                    sql = migration_file.read_text()
                    if not self.apply_migration(migration_file.name, sql):
                        return False

            return True

        except Exception as e:
            logger.error("Feil ved kjøring av migrasjoner: %s", e)
            return False

    def init_db(self) -> None:
        """Initialiserer databasen.

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            self._init_migrations_table()
            logger.info("Database initialisert")
        except Exception as e:
            logger.error("Feil ved initialisering av database: %s", e)
            raise DatabaseError("Kunne ikke initialisere database") from e

    def migrate_db(self) -> bool:
        """Kjører alle ventende migrasjoner.

        Returns:
            True hvis alle migrasjoner ble kjørt vellykket, False ellers
        """
        try:
            return self.run_migrations()
        except Exception as e:
            logger.error("Feil ved kjøring av migrasjoner: %s", e)
            return False
