"""Application constants."""

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
DB_DIR = SRC_DIR / "min_kamp" / "db" / "database"
MIGRATIONS_DIR = SRC_DIR / "min_kamp" / "db" / "migrations"

# Database
DATABASE_NAME = "kampdata.db"
DATABASE_PATH = DB_DIR / DATABASE_NAME

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Authentication
PASSWORD_SALT_LENGTH = 32
PASSWORD_HASH_ITERATIONS = 100000
PASSWORD_HASH_LENGTH = 32

# Application settings
DEFAULT_SPILLETID = 60  # minutter
DEFAULT_PERIODE_LENGDE = 15  # minutter
DEFAULT_ANTALL_PERIODER = 4
DEFAULT_SPILLERE_PAA_BANEN = 5

# Session state keys
SESSION_STATE_KEYS = {
    # Authentication
    "initialized": bool,
    "user_id": int,
    "username": str,
    "debug_mode": bool,
    "indekser_opprettet": bool,
}

# Error messages
ERROR_MESSAGES = {
    "auth": {
        "invalid_credentials": "Ugyldig brukernavn eller passord",
        "user_not_found": "Bruker ikke funnet",
        "user_exists": "Bruker eksisterer allerede",
        "registration_failed": "Registrering feilet",
    },
    "database": {
        "connection_failed": "Kunne ikke koble til databasen",
        "query_failed": "Databasespørring feilet",
        "migration_failed": "Databasemigrering feilet",
    },
    "validation": {
        "required_field": "Dette feltet er påkrevd",
        "invalid_input": "Ugyldig input",
    },
}
