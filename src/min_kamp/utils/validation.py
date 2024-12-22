# validation.py
"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Valideringsverktøy for applikasjonen.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, List, Optional, Type, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


def valider_antall_spillere(
    antall: int, min_spillere: int, max_spillere: int
) -> Optional[str]:
    """
    Validerer antall spillere.

    Args:
        antall: Antall spillere å validere
        min_spillere: Minimum antall spillere
        max_spillere: Maksimum antall spillere

    Returns:
        Optional[str]: Feilmelding hvis antallet er ugyldig, None ellers
    """
    try:
        if antall < min_spillere:
            return f"For få spillere ({antall}). Minimum er {min_spillere}."

        if antall > max_spillere:
            return f"For mange spillere ({antall}). Maksimum er {max_spillere}."

        return None

    except Exception as e:
        logger.error("Feil ved validering av antall spillere: %s", e, exc_info=True)
        return "Kunne ikke validere antall spillere"


def validate_and_convert(value: Any, target_type: Type[T]) -> Optional[T]:
    """
    Validerer og konverterer en verdi til ønsket type.

    Args:
        value: Verdien som skal konverteres
        target_type: Måltypen

    Returns:
        Optional[T]: Den konverterte verdien hvis vellykket, None ellers
    """
    try:
        if value is None:
            return None

        if isinstance(value, target_type):
            return cast(T, value)

        # Spesialhåndtering for bool siden bool("False") == True
        if target_type is bool and isinstance(value, str):
            return cast(T, value.lower() == "true")

        # Spesialhåndtering for list og dict
        if target_type in (list, dict) and isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, target_type):
                    return cast(T, parsed)
                return None
            except json.JSONDecodeError:
                return None

        # Prøv å konvertere med type-spesifikke metoder
        if target_type is int:
            try:
                return cast(T, int(str(value)))
            except (ValueError, TypeError):
                return None
        elif target_type is float:
            try:
                return cast(T, float(str(value)))
            except (ValueError, TypeError):
                return None
        elif target_type is str:
            return cast(T, str(value))
        elif target_type is list:
            if isinstance(value, (list, tuple)):
                return cast(T, list(value))
            return None
        elif target_type is dict:
            if isinstance(value, dict):
                return cast(T, dict(value))
            return None

        return None

    except Exception as e:
        logger.error(
            "Feil ved konvertering av %s til %s: %s",
            value,
            target_type,
            e,
            exc_info=True,
        )
        return None


class ValidationResult:
    """Resultat av validering"""

    def __init__(
        self, er_gyldig: bool = True, feilmeldinger: Optional[List[str]] = None
    ):
        self.er_gyldig = er_gyldig
        self.feilmeldinger = feilmeldinger or []

    def __iter__(self):
        """Gjør det mulig å unpacke resultatet som en tuple"""
        yield self.er_gyldig
        yield self.feilmeldinger


class SchemaValidator:
    """Validerer databaseskjema"""

    def __init__(self, db_path: Path, schema_path: Path):
        """Initialiserer schema validator"""
        self.db_path = db_path
        self.schema_path = schema_path

    def validate_database_schema(self, schema: str) -> None:
        """Validerer et databaseskjema"""
        if not schema or not isinstance(schema, str):
            raise ValueError("Ugyldig skjema")
        # Implementasjon her...

    def validate_database_table(self, table_name: str) -> None:
        """Validerer en databasetabell"""
        if not table_name:
            raise ValueError("Tabellnavn kan ikke være tomt")
        # Implementasjon her...

    def validate_database(self) -> ValidationResult:
        """Validerer hele databasen"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Sjekk at databasen eksisterer og er tilgjengelig
                cursor.execute("SELECT 1")

                # Her kan vi legge til mer validering...

                return ValidationResult(True, [])

        except Exception as e:
            logger.error(f"Feil ved validering av database: {e}")
            return ValidationResult(False, [str(e)])
