"""
Håndterer databasemigrasjoner.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


def kjor_migrasjoner(db_handler: Any, migrasjoner_mappe: str) -> None:
    """Kjører alle migrasjoner som ikke er kjørt.

    Args:
        db_handler: DatabaseHandler instans
        migrasjoner_mappe: Sti til mappen med migrasjoner
    """
    try:
        # Opprett migrations-tabellen hvis den ikke finnes
        with db_handler.connection() as conn:
            cursor = conn.cursor()

            # Aktiver foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")

            # Sjekk om tabellen eksisterer
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table' AND name=?
                """,
                ("migrations",),
            )

            if not cursor.fetchone():
                # Opprett migrations-tabellen
                cursor.execute(
                    """
                    CREATE TABLE migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        navn TEXT NOT NULL UNIQUE,
                        kjort_dato TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
                        sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Opprett indeks
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_migrations_navn
                    ON migrations(navn)
                    """
                )

                conn.commit()

        # Hent alle migrasjoner som er kjørt
        kjorte_migrasjoner = _hent_kjorte_migrasjoner(db_handler)

        # Hent alle migrasjonsfiler
        migrasjoner = _hent_migrasjonsfiler(migrasjoner_mappe)

        # Kjør migrasjoner som ikke er kjørt
        for migrasjon in migrasjoner:
            if migrasjon.navn not in kjorte_migrasjoner:
                _kjor_migrasjon(db_handler, migrasjon)

    except Exception as e:
        logger.error("Feil ved kjøring av migrasjoner: %s", e)
        raise DatabaseError(f"Kunne ikke kjøre migrasjoner: {e}")


def _hent_kjorte_migrasjoner(db_handler: Any) -> Dict[str, datetime]:
    """Henter alle migrasjoner som er kjørt.

    Args:
        db_handler: DatabaseHandler instans

    Returns:
        Dict med migrasjonsnavn og kjøredato
    """
    try:
        with db_handler.connection() as conn:
            cursor = conn.cursor()

            # Aktiver foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")

            cursor.execute(
                """
                SELECT
                    navn,
                    kjort_dato,
                    opprettet_dato,
                    sist_oppdatert
                FROM migrations
                ORDER BY kjort_dato
                """
            )

            return {row[0]: row[1] for row in cursor.fetchall()}

    except Exception as e:
        logger.error("Feil ved henting av kjørte migrasjoner: %s", e)
        raise DatabaseError(f"Kunne ikke hente kjørte migrasjoner: {e}")


def _hent_migrasjonsfiler(mappe: str) -> List[Any]:
    """Henter alle migrasjonsfiler.

    Args:
        mappe: Sti til mappen med migrasjoner

    Returns:
        Liste med migrasjonsfiler
    """
    try:
        migrasjoner = []
        for fil in sorted(os.listdir(mappe)):
            if fil.endswith(".sql"):
                sti = os.path.join(mappe, fil)
                with open(sti, "r") as f:
                    sql = f.read()

                migrasjoner.append(Migrasjon(navn=fil, sql=sql, sti=sti))

        return migrasjoner

    except Exception as e:
        logger.error("Feil ved henting av migrasjonsfiler: %s", e)
        raise DatabaseError(f"Kunne ikke hente migrasjonsfiler: {e}")


def _kjor_migrasjon(db_handler: Any, migrasjon: Any) -> None:
    """Kjører en migrasjon.

    Args:
        db_handler: DatabaseHandler instans
        migrasjon: Migrasjon som skal kjøres
    """
    try:
        with db_handler.connection() as conn:
            cursor = conn.cursor()

            # Kjør migrasjonen
            cursor.executescript(migrasjon.sql)

            # Logg at migrasjonen er kjørt
            cursor.execute(
                """
                INSERT INTO migrations (navn)
                VALUES (?)
                """,
                (migrasjon.navn,),
            )

            conn.commit()

            logger.info("Kjørte migrasjon: %s", migrasjon.navn)

    except Exception as e:
        logger.error("Feil ved kjøring av migrasjon %s: %s", migrasjon.navn, e)
        raise DatabaseError(f"Kunne ikke kjøre migrasjon: {e}")


class Migrasjon:
    """Representerer en databasemigrasjon."""

    def __init__(self, navn: str, sql: str, sti: str):
        self.navn = navn
        self.sql = sql
        self.sti = sti
