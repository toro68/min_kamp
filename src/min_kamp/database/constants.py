"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Database-relaterte konstanter.
Se spesielt:
- avhengigheter.md -> Database -> Constants
- system.md -> Database -> Constants
"""

import os

from dotenv import load_dotenv

# Last miljøvariabler
load_dotenv()

# Sjekk om vi er i testmiljø
IS_TEST = os.getenv("TESTING", "False").lower() == "true"

# Database
DATABASE_FILE = "test.db" if IS_TEST else "kampdata.db"
DATABASE_PATH = os.getenv(
    "TEST_DATABASE_PATH" if IS_TEST else "DATABASE_PATH",
    os.path.join("data", DATABASE_FILE),
)
SCHEMA_FILE = "schema.sql"
SCHEMA_PATH = os.getenv(
    "TEST_SCHEMA_PATH" if IS_TEST else "SCHEMA_PATH",
    os.path.join("src", "database", SCHEMA_FILE),
)

# Validering
MIN_SPILLERE = 5
MAX_SPILLERE = 7
MIN_PERIODER = 2
MAX_PERIODER = 4

# Sikre at paths eksisterer
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
