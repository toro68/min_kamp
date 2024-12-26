"""
Validerer databaseskjema.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultat av validering."""

    success: bool
    errors: List[str]

    @property
    def is_valid(self) -> bool:
        """Returnerer True hvis valideringen var vellykket."""
        return self.success and not self.errors


class SchemaValidator:
    """Validerer databaseskjema."""

    def __init__(self, db_handler: Any) -> None:
        """Initialiserer validator.

        Args:
            db_handler: DatabaseHandler instans
        """
        self.db_handler = db_handler

    def valider_skjema(self, skjema_fil: str) -> ValidationResult:
        """Validerer databaseskjemaet.

        Args:
            skjema_fil: Sti til skjemafilen

        Returns:
            ValidationResult med resultat av valideringen
        """
        try:
            errors = valider_skjema(self.db_handler, skjema_fil)
            return ValidationResult(success=True, errors=errors)
        except Exception as e:
            logger.error("Feil ved validering: %s", e)
            return ValidationResult(success=False, errors=[str(e)])


def valider_skjema(db_handler: Any, skjema_fil: str) -> List[str]:
    """Validerer databaseskjemaet.

    Args:
        db_handler: DatabaseHandler instans
        skjema_fil: Sti til skjemafilen

    Returns:
        Liste med feilmeldinger (tom hvis ingen feil)
    """
    try:
        # Les skjemafilen
        with open(skjema_fil, "r") as f:
            skjema_sql = f.read()

        # Opprett en midlertidig database i minnet
        with db_handler.get_connection() as conn:
            cursor = conn.cursor()

            # Aktiver foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")

            # Kjør skjemafilen
            cursor.executescript(skjema_sql)

            # Hent tabellinfo
            cursor.execute(
                """
                SELECT name, sql
                FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
            )

            tabeller = {row[0]: row[1] for row in cursor.fetchall()}

            # Valider hver tabell
            feil = []
            for tabell, sql in tabeller.items():
                tabell_feil = _valider_tabell(cursor, tabell)
                feil.extend(tabell_feil)

            return feil

    except Exception as e:
        logger.error("Feil ved validering av skjema: %s", e)
        raise DatabaseError(f"Kunne ikke validere skjema: {e}")


def _valider_tabell(cursor: Any, tabell: str) -> List[str]:
    """Validerer en tabell.

    Args:
        cursor: Database cursor
        tabell: Tabellnavn

    Returns:
        Liste med feilmeldinger
    """
    feil = []

    try:
        # Hent kolonneinfo
        cursor.execute(f"PRAGMA table_info({tabell})")
        kolonner = {
            row[1]: {"type": row[2], "notnull": bool(row[3]), "pk": bool(row[5])}
            for row in cursor.fetchall()
        }

        # Hent foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({tabell})")
        fks = [
            {"from": row[3], "to_table": row[2], "to_col": row[4]}
            for row in cursor.fetchall()
        ]

        # Valider kolonnetyper
        for kolonne, info in kolonner.items():
            kolonne_feil = _valider_kolonnetype(info["type"])
            if kolonne_feil:
                feil.append(
                    f"Ugyldig kolonnetype i {tabell}.{kolonne}: " f"{kolonne_feil}"
                )

        # Valider foreign keys
        for fk in fks:
            if not _valider_foreign_key(cursor, fk):
                feil.append(
                    f"Ugyldig foreign key i {tabell}: "
                    f"{fk['from']} -> {fk['to_table']}.{fk['to_col']}"
                )

        return feil

    except Exception as e:
        logger.error("Feil ved validering av tabell %s: %s", tabell, e)
        return [f"Kunne ikke validere tabell {tabell}: {e}"]


def _valider_kolonnetype(kolonnetype: str) -> Optional[str]:
    """Validerer en kolonnetype.

    Args:
        kolonnetype: Kolonnetypen som skal valideres

    Returns:
        Feilmelding eller None hvis OK
    """
    # Tillatte typer
    gyldige_typer = {
        "INTEGER",
        "TEXT",
        "BLOB",
        "REAL",
        "NUMERIC",
        "BOOLEAN",
        "DATETIME",
        "TIMESTAMP",
    }

    # Fjern størrelsesbegrensninger
    base_type = re.sub(r"\(.*\)", "", kolonnetype).upper()

    if base_type not in gyldige_typer:
        return f"Ugyldig type: {kolonnetype}"

    return None


def _valider_foreign_key(cursor: Any, fk: Dict[str, str]) -> bool:
    """Validerer en foreign key.

    Args:
        cursor: Database cursor
        fk: Foreign key info

    Returns:
        True hvis OK, False hvis ugyldig
    """
    try:
        # Sjekk at måltabellen eksisterer
        cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (fk["to_table"],),
        )
        if not cursor.fetchone():
            logger.error("Måltabell %s finnes ikke", fk["to_table"])
            return False

        # Sjekk at målkolonnen eksisterer
        cursor.execute(f"PRAGMA table_info({fk['to_table']})")
        kolonner = {row[1] for row in cursor.fetchall()}

        if fk["to_col"] not in kolonner:
            logger.error("Målkolonne %s.%s finnes ikke", fk["to_table"], fk["to_col"])
            return False

        return True

    except Exception as e:
        logger.error("Feil ved validering av foreign key: %s", e)
        return False
