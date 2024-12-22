"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer database handler for databasetilgang.
Se spesielt:
- avhengigheter.md -> Database -> Handler
- system.md -> Database -> Handler
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handler for databaseoperasjoner.

    Denne klassen håndterer alle databaseoperasjoner i applikasjonen,
    inkludert tilkobling, spørringer og oppdateringer.
    """

    def __init__(self) -> None:
        """Initialiserer database handler."""
        self.schema_path = os.getenv("SCHEMA_PATH", "src/min_kamp/database/schema.sql")
        if not self.schema_path:
            raise ValueError("SCHEMA_PATH miljøvariabel er ikke satt")

        self.db_path = os.getenv("DATABASE_PATH", "data/kampdata.db")
        if not self.db_path:
            raise ValueError("DATABASE_PATH miljøvariabel er ikke satt")

        logger.debug(
            f"DatabaseHandler initialiseres med SCHEMA_PATH: {self.schema_path}"
        )
        logger.debug(
            f"Absolutt sti til SCHEMA_PATH: {Path(self.schema_path).absolute()}"
        )
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialiserer databasen"""
        try:
            # Opprett database-mappe hvis den ikke finnes
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Opprett tabeller
            self._ensure_tables_exist()

            logger.info("Database initialisert")

        except Exception as e:
            logger.error(f"Feil ved initialisering av database: {e}")
            raise

    def _ensure_tables_exist(self) -> None:
        """Sørger for at alle tabeller eksisterer"""
        try:
            # Les SQL-schema
            schema_path = Path(self.schema_path)
            logger.debug(f"Prøver å lese schema fra: {schema_path.absolute()}")
            if not schema_path.exists():
                logger.error(f"Schema-fil ikke funnet på: {schema_path.absolute()}")
                logger.error(f"Gjeldende arbeidsmappe: {Path.cwd()}")
                raise FileNotFoundError(f"Schema-fil ikke funnet: {self.schema_path}")

            schema = schema_path.read_text()

            # Opprett tabeller
            with self.get_connection() as conn:
                conn.executescript(schema)

            logger.info("Database-tabeller opprettet")

        except Exception as e:
            logger.error(f"Feil ved opprettelse av tabeller: {e}")
            raise

    def get_connection(self) -> sqlite3.Connection:
        """Henter en ny databasetilkobling.

        Returns:
            sqlite3.Connection: En tilkobling til databasen
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_cursor(self) -> sqlite3.Cursor:
        """Henter en databasecursor.

        Returns:
            sqlite3.Cursor: En cursor for databaseoperasjoner
        """
        conn = self.get_connection()
        return conn.cursor()

    def commit(self) -> None:
        """Utfører commit på alle aktive tilkoblinger."""
        # Siden vi ikke lenger har en connection pool,
        # må hver operasjon håndtere sin egen commit
        pass

    def close_connections(self) -> None:
        """Lukker alle aktive databasetilkoblinger."""
        # Siden vi ikke lenger har en connection pool,
        # må hver operasjon håndtere sin egen lukking
        pass

    def get_active_connections(self) -> int:
        """Returnerer antall aktive databasetilkoblinger"""
        return 0  # Vi har ingen lagrede tilkoblinger lenger

    def get_kamp(self, kamp_id: Union[str, None]) -> Optional[Dict[str, Any]]:
        """Henter kampdata for gitt ID"""
        if not kamp_id:
            raise ValueError("Kamp ID kan ikke være tom")
        # Implementasjon her...
        return None

    def get_user_by_name(self, username: Union[str, None]) -> Optional[Dict[str, Any]]:
        """Henter brukerdata for gitt brukernavn"""
        if not username:
            raise ValueError("Brukernavn kan ikke være tomt")
        # Implementasjon her...
        return None

    def create_user(self, username: str, password: str) -> bool:
        """Oppretter en ny bruker"""
        if not username or not password:
            raise ValueError("Brukernavn og passord må være satt")
        # Implementasjon her...
        return True

    def execute_query(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Dict[str, Any]]:
        """Utfører en database spørring

        Args:
            query: SQL spørring
            params: Parametere til spørringen

        Returns:
            Liste med resultatrader som dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Feil ved utføring av spørring: {e}")
            raise

    def execute_update(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> int:
        """Utfører en database oppdatering

        Args:
            query: SQL spørring
            params: Parametere til spørringen

        Returns:
            ID til sist innsatte rad
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.lastrowid or 0

        except Exception as e:
            logger.error(f"Feil ved utføring av oppdatering: {e}")
            raise
