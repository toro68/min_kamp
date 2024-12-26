"""Script for å sjekke databasen mot forventet skjema."""

import sqlite3
import logging
from typing import List, Set, Tuple

from min_kamp.db.db_config import get_db_path

logger = logging.getLogger(__name__)


def hent_forventet_tabeller() -> Set[str]:
    """Henter forventede tabellnavn fra skjemafiler."""
    forventede_tabeller = {
        "brukere",
        "app_innstillinger",
        "kamper",
        "spillere",
        "kamptropp",
        "bytteplan",
        "spilletid",
        "migrations",
    }
    return forventede_tabeller


def hent_forventet_indekser() -> Set[str]:
    """Henter forventede indeksnavn fra skjemafiler."""
    forventede_indekser = {
        "idx_brukere_brukernavn",
        "idx_app_innstillinger_bruker_id",
        "idx_app_innstillinger_nokkel",
        "idx_kamper_bruker_id",
        "idx_kamper_dato",
        "idx_spillere_bruker_id",
        "idx_spillere_posisjon",
        "idx_spillere_navn",
        "idx_kamptropp_kamp_id",
        "idx_kamptropp_spiller_id",
        "idx_kamptropp_er_med",
        "idx_bytteplan_kamp_id",
        "idx_bytteplan_spiller_id",
        "idx_bytteplan_periode",
        "idx_spilletid_kamp_id",
        "idx_spilletid_spiller_id",
        "idx_migrations_navn",
    }
    return forventede_indekser


def hent_kolonneinfo(
    cursor: sqlite3.Cursor, tabell: str
) -> List[Tuple[str, str, bool]]:
    """Henter kolonneinformasjon for en tabell.

    Returns:
        Liste med tupler (kolonnenavn, type, nullable)
    """
    cursor.execute(f"PRAGMA table_info({tabell})")
    kolonner = []
    for row in cursor.fetchall():
        navn = row[1]
        type_ = row[2]
        nullable = not row[3]  # notnull er 1 hvis NOT NULL
        kolonner.append((navn, type_, nullable))
    return kolonner


def sjekk_foreign_keys(cursor: sqlite3.Cursor, tabell: str) -> List[str]:
    """Sjekker foreign key constraints for en tabell."""
    cursor.execute(f"PRAGMA foreign_key_list({tabell})")
    feil = []
    for fk in cursor.fetchall():
        ref_tabell = fk[2]  # Referert tabell
        from_col = fk[3]  # Lokal kolonne
        to_col = fk[4]  # Referert kolonne

        # Sjekk at referert tabell eksisterer
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (ref_tabell,),
        )
        if not cursor.fetchone():
            feil.append(
                f"Tabell {tabell}: Foreign key {from_col} refererer til "
                f"ikke-eksisterende tabell {ref_tabell}"
            )
            continue

        # Sjekk at referert kolonne eksisterer
        cursor.execute(f"PRAGMA table_info({ref_tabell})")
        kolonner = {row[1] for row in cursor.fetchall()}
        if to_col not in kolonner:
            feil.append(
                f"Tabell {tabell}: Foreign key {from_col} refererer til "
                f"ikke-eksisterende kolonne {to_col} i {ref_tabell}"
            )

    return feil


def er_sqlite_intern(navn: str) -> bool:
    """Sjekker om et objekt er internt for SQLite.

    Args:
        navn: Navnet på objektet

    Returns:
        bool: True hvis objektet er internt for SQLite
    """
    return navn.startswith("sqlite_") or navn.startswith("_sqlite_")


def sjekk_database() -> None:
    """Sjekk databasen mot forventet skjema."""
    try:
        db_path = get_db_path()
        logger.info("Sjekker database: %s", db_path)

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Aktiver foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Sjekk at foreign keys er aktivert
            cursor.execute("PRAGMA foreign_keys")
            if not cursor.fetchone()[0]:
                logger.error("ADVARSEL: Foreign keys er ikke aktivert!")

            # Hent faktiske tabeller
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            faktiske_tabeller = {
                row[0] for row in cursor.fetchall() if not er_sqlite_intern(row[0])
            }

            # Sjekk manglende tabeller
            forventede_tabeller = hent_forventet_tabeller()
            manglende_tabeller = forventede_tabeller - faktiske_tabeller
            if manglende_tabeller:
                logger.error("Manglende tabeller: %s", ", ".join(manglende_tabeller))

            # Sjekk uventede tabeller
            uventede_tabeller = faktiske_tabeller - forventede_tabeller
            if uventede_tabeller:
                logger.warning(
                    "Uventede tabeller funnet: %s", ", ".join(uventede_tabeller)
                )

            # Hent faktiske indekser
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            faktiske_indekser = {
                row[0] for row in cursor.fetchall() if not er_sqlite_intern(row[0])
            }

            # Sjekk manglende indekser
            forventede_indekser = hent_forventet_indekser()
            manglende_indekser = forventede_indekser - faktiske_indekser
            if manglende_indekser:
                logger.error("Manglende indekser: %s", ", ".join(manglende_indekser))

            # Sjekk uventede indekser
            uventede_indekser = faktiske_indekser - forventede_indekser
            if uventede_indekser:
                logger.warning(
                    "Uventede indekser funnet: %s", ", ".join(uventede_indekser)
                )

            # Sjekk kolonner og foreign keys for hver tabell
            for tabell in faktiske_tabeller:
                if er_sqlite_intern(tabell):
                    continue

                logger.info("Sjekker tabell: %s", tabell)

                # Sjekk kolonner
                kolonner = hent_kolonneinfo(cursor, tabell)
                logger.info("Kolonner i %s:", tabell)
                for navn, type_, nullable in kolonner:
                    logger.info(
                        "- %s: %s%s",
                        navn,
                        type_,
                        " (NULL)" if nullable else " (NOT NULL)",
                    )

                # Sjekk foreign keys
                fk_feil = sjekk_foreign_keys(cursor, tabell)
                if fk_feil:
                    for feil in fk_feil:
                        logger.error(feil)

    except Exception as e:
        logger.error("Feil ved sjekk av database: %s", e)
        raise


if __name__ == "__main__":
    # Sett opp logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Kjør sjekk
    sjekk_database()
