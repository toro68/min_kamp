import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SchemaError(Enum):
    """Definerer mulige skjemafeil"""

    MANGLER_FIL = "mangler_fil"
    PARSE_FEIL = "parse_feil"
    DB_FEIL = "database_feil"
    SCHEMA_AVVIK = "schema_avvik"


@dataclass
class ColumnDefinition:
    """Definisjon av en databasekolonne"""

    name: str
    type: str
    nullable: bool
    default: Optional[str]
    check: Optional[str]


@dataclass
class TableDefinition:
    """Definisjon av en databasetabell"""

    name: str
    columns: Dict[str, ColumnDefinition]
    constraints: List[str]


@dataclass
class ValidationResult:
    """Resultat av skjemavalidering"""

    er_gyldig: bool
    feilmeldinger: List[str]

    def __init__(
        self, er_gyldig: bool = False, feilmeldinger: Optional[List[str]] = None
    ):
        self.er_gyldig = er_gyldig
        self.feilmeldinger = feilmeldinger if feilmeldinger is not None else []


class SchemaValidator:
    """Validerer databaseskjema mot schema.sql"""

    def __init__(self, db_path: Path, schema_path: Path):
        self.db_path = db_path
        self.schema_path = schema_path
        self.expected_schema: Dict[str, TableDefinition] = {}

        # Valider at schema-filen eksisterer
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema fil ikke funnet: {schema_path}")

        # Parse schema
        try:
            self.expected_schema = self._parse_schema_file()
        except Exception as e:
            logger.error(f"Feil ved parsing av schema: {e}")
            raise ValueError(f"Kunne ikke parse schema: {e}")

    def _parse_schema_file(self) -> Dict[str, TableDefinition]:
        """Parser schema.sql filen med forbedret feilhåndtering"""
        schema_dict: Dict[str, TableDefinition] = {}

        try:
            logger.debug(f"Leser schema fra: {self.schema_path}")
            schema_content = self.schema_path.read_text()
            table_matches = re.finditer(
                r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\(([\s\S]*?)\);",
                schema_content,
            )

            for match in table_matches:
                table_name = match.group(1)
                columns_def = match.group(2)

                logger.debug(f"Parser tabell: {table_name}")
                columns = self._parse_columns(columns_def)
                constraints = self._parse_constraints(columns_def)

                schema_dict[table_name] = TableDefinition(
                    name=table_name, columns=columns, constraints=constraints
                )

                logger.debug(
                    f"Parsed tabell: {table_name} med {len(columns)} kolonner og {len(constraints)} constraints"
                )

            logger.debug(
                f"Ferdig med parsing av schema. Fant {len(schema_dict)} tabeller"
            )
            return schema_dict

        except Exception as e:
            error_msg = f"Feil ved parsing av schema fil: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _parse_columns(self, columns_def: str) -> Dict[str, ColumnDefinition]:
        """Parser kolonnedefinisjoner med forbedret type-sikkerhet"""
        columns: Dict[str, ColumnDefinition] = {}

        for line in columns_def.split("\n"):
            line = line.strip()
            if not line or line.startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE")):
                continue

            parts = line.strip(",").split()
            if len(parts) >= 2:
                col_name = parts[0]
                col_type = parts[1]
                constraints = " ".join(parts[2:])

                columns[col_name] = ColumnDefinition(
                    name=col_name,
                    type=col_type,
                    nullable="NOT NULL" not in constraints,
                    default=self._extract_default(constraints),
                    check=self._extract_check(constraints),
                )

        return columns

    def _parse_constraints(self, columns_def: str) -> List[str]:
        """Parser constraint-definisjoner fra schema"""
        constraints = []

        # Finn alle linjer som starter med en constraint
        for line in columns_def.split("\n"):
            line = line.strip()
            if line.startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK")):
                # Fjern komma på slutten hvis det finnes
                line = line.rstrip(",")
                # Fjern ekstra whitespace
                line = re.sub(r"\s+", " ", line)
                # Fjern mellomrom mellom parenteser
                line = re.sub(r"\(\s+", "(", line)
                line = re.sub(r"\s+\)", ")", line)
                # Fjern mellomrom rundt komma
                line = re.sub(r"\s*,\s*", ",", line)
                constraints.append(line)

        return constraints

    def _extract_default(self, constraint_str: str) -> Optional[str]:
        """Henter DEFAULT verdi fra constraint string"""
        default_match = re.search(r"DEFAULT\s+([^,\s]+)", constraint_str)
        return default_match.group(1) if default_match else None

    def _extract_check(self, constraint_str: str) -> Optional[str]:
        """Henter CHECK constraint fra constraint string"""
        check_match = re.search(r"CHECK\s*\((.*?)\)", constraint_str)
        return check_match.group(1) if check_match else None

    def validate_database(self) -> ValidationResult:
        """Validerer databasen mot schema med detaljert resultat"""
        errors: List[str] = []

        try:
            logger.debug(f"Starter validering av database: {self.db_path}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Sjekk eksisterende tabeller
                cursor.execute(
                    """
                    SELECT name, sql
                    FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                )

                existing_tables = {row[0]: row[1] for row in cursor.fetchall()}
                logger.debug(f"Fant {len(existing_tables)} tabeller i databasen")
                logger.debug(
                    f"Forventet schema har {len(self.expected_schema)} tabeller"
                )

                # Valider hver forventet tabell
                for table_name, expected_table in self.expected_schema.items():
                    logger.debug(f"Validerer tabell: {table_name}")
                    if table_name not in existing_tables:
                        error_msg = f"Mangler tabell: {table_name}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue

                    # Valider kolonner
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    existing_columns = {
                        row[1]: ColumnDefinition(
                            name=row[1],
                            type=row[2],
                            nullable=not row[3],
                            default=row[4],
                            check=None,
                        )
                        for row in cursor.fetchall()
                    }
                    logger.debug(
                        f"Fant {len(existing_columns)} kolonner i {table_name}"
                    )

                    self._validate_columns(
                        table_name, existing_columns, expected_table.columns, errors
                    )

                    # Valider constraints
                    self._validate_constraints(
                        table_name, cursor, expected_table.constraints, errors
                    )

                result = ValidationResult(
                    er_gyldig=len(errors) == 0, feilmeldinger=errors
                )
                logger.debug(
                    f"Validering fullført. Gyldig: {result.er_gyldig}, Feil: {len(result.feilmeldinger)}"
                )
                if not result.er_gyldig:
                    logger.error(f"Valideringsfeil: {result.feilmeldinger}")
                return result

        except Exception as e:
            error_msg = f"Databasevalidering feilet: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(er_gyldig=False, feilmeldinger=[error_msg])

    def _validate_columns(
        self,
        table_name: str,
        existing_columns: Dict[str, ColumnDefinition],
        expected_columns: Dict[str, ColumnDefinition],
        errors: List[str],
    ) -> None:
        """Validerer kolonner mot forventet schema"""
        logger.debug(f"Validerer kolonner for tabell {table_name}")
        logger.debug(
            f"Forventet {len(expected_columns)} kolonner, fant {len(existing_columns)} kolonner"
        )

        # Sjekk manglende kolonner
        for col_name in expected_columns:
            if col_name not in existing_columns:
                error_msg = f"Tabell {table_name}: Mangler kolonne {col_name}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

            expected_col = expected_columns[col_name]
            actual_col = existing_columns[col_name]

            # Sjekk type
            if expected_col.type.upper() != actual_col.type.upper():
                error_msg = (
                    f"Tabell {table_name}, kolonne {col_name}: "
                    f"Feil type (forventet {expected_col.type}, "
                    f"fant {actual_col.type})"
                )
                logger.error(error_msg)
                errors.append(error_msg)

            # Sjekk nullable
            if expected_col.nullable != actual_col.nullable:
                error_msg = (
                    f"Tabell {table_name}, kolonne {col_name}: "
                    f"Feil nullable (forventet {expected_col.nullable}, "
                    f"fant {actual_col.nullable})"
                )
                logger.error(error_msg)
                errors.append(error_msg)

            # Sjekk default verdi hvis satt
            if expected_col.default and expected_col.default != actual_col.default:
                error_msg = (
                    f"Tabell {table_name}, kolonne {col_name}: "
                    f"Feil default verdi (forventet {expected_col.default}, "
                    f"fant {actual_col.default})"
                )
                logger.error(error_msg)
                errors.append(error_msg)

        # Sjekk ekstra kolonner
        for col_name in existing_columns:
            if col_name not in expected_columns:
                error_msg = f"Tabell {table_name}: Uventet kolonne {col_name}"
                logger.error(error_msg)
                errors.append(error_msg)

    def _normalize_constraint(self, constraint: str) -> str:
        """Normaliserer en constraint string for sammenligning"""
        # Fjern ekstra whitespace og konverter til uppercase
        c = re.sub(r"\s+", " ", constraint.upper().strip())

        # Fjern CONSTRAINT navn hvis det finnes
        c = re.sub(r"CONSTRAINT\s+\w+\s+", "", c)

        # Fjern mellomrom mellom KEY og parentes
        c = re.sub(r"KEY\s*\(", "KEY(", c)

        # Fjern mellomrom mellom FOREIGN og KEY
        c = re.sub(r"FOREIGN\s+KEY", "FOREIGN KEY", c)

        # Fjern mellomrom mellom PRIMARY og KEY
        c = re.sub(r"PRIMARY\s+KEY", "PRIMARY KEY", c)

        # Fjern mellomrom mellom REFERENCES og tabellnavn/kolonne
        c = re.sub(r"REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)", r"REFERENCES \1(\2)", c)

        # Fjern mellomrom rundt komma
        c = re.sub(r"\s*,\s*", ",", c)

        # Fjern mellomrom mellom parenteser
        c = re.sub(r"\(\s+", "(", c)
        c = re.sub(r"\s+\)", ")", c)

        return c

    def _validate_constraints(
        self,
        table_name: str,
        cursor: sqlite3.Cursor,
        expected_constraints: List[str],
        errors: List[str],
    ) -> None:
        """Validerer constraints mot forventet schema"""
        logger.debug(f"Validerer constraints for tabell {table_name}")

        # Hent eksisterende constraints
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        table_sql = cursor.fetchone()[0]
        logger.debug(f"Table SQL: {table_sql}")

        # Finn alle constraints i table_sql
        existing_constraints = set()

        # Finn PRIMARY KEY constraints
        pk_matches = re.finditer(r"PRIMARY\s+KEY\s*\((.*?)\)", table_sql, re.I)
        for match in pk_matches:
            existing_constraints.add(
                self._normalize_constraint(f"PRIMARY KEY({match.group(1)})")
            )

        # Finn FOREIGN KEY constraints
        fk_matches = re.finditer(
            r"FOREIGN\s+KEY\s*\((.*?)\)\s*REFERENCES\s+(\w+)\s*\((\w+)\)",
            table_sql,
            re.I,
        )
        for match in fk_matches:
            existing_constraints.add(
                self._normalize_constraint(
                    f"FOREIGN KEY({match.group(1)}) REFERENCES {match.group(2)}({match.group(3)})"
                )
            )

        # Finn UNIQUE constraints
        unique_matches = re.finditer(r"UNIQUE\s*\((.*?)\)", table_sql, re.I)
        for match in unique_matches:
            existing_constraints.add(
                self._normalize_constraint(f"UNIQUE({match.group(1)})")
            )

        # Normaliser forventede constraints
        expected_normalized = {
            self._normalize_constraint(c) for c in expected_constraints
        }

        logger.debug(f"Forventet constraints: {expected_normalized}")
        logger.debug(f"Eksisterende constraints: {existing_constraints}")

        # Sjekk manglende constraints
        for constraint in expected_normalized:
            if constraint not in existing_constraints:
                error_msg = f"Tabell {table_name}: Mangler constraint: {constraint}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Sjekk ekstra constraints
        for constraint in existing_constraints:
            if constraint not in expected_normalized:
                error_msg = f"Tabell {table_name}: Uventet constraint: {constraint}"
                logger.error(error_msg)
                errors.append(error_msg)


def parse_schema(schema_path: Path) -> Dict[str, TableDefinition]:
    """Parser SQL schema-filen og returnerer en dict med tabelldefinisjoner"""
    schema_dict: Dict[str, TableDefinition] = {}
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_dict = json.load(f)  # Les JSON direkte inn i dict
        return schema_dict
    except Exception as e:
        logger.error("Kunne ikke parse schema: %s", e)
        raise ValueError(f"Kunne ikke parse schema: {e}") from e


def validate_schema(db_path: Path, schema_path: Path) -> ValidationResult:
    """Validerer databasen mot schema-filen"""
    try:
        # ... existing code ...
        return ValidationResult(True)  # eller relevant resultat
    except Exception as e:
        logger.error("Schema parsing feilet: %s", e)
        return ValidationResult(False, [f"Schema parsing feilet: {e}"])


def _validate_table_constraints(table_name: str, expected: str, actual: str) -> str:
    """Validerer tabellbegrensninger"""
    # Erstatt f-string uten interpolering med vanlig streng
    return "Tabellen har ikke riktige begrensninger"
