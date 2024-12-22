"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer konfigurasjon.
Se spesielt:
- avhengigheter.md -> Config
- system.md -> Config
"""

from min_kamp.config.constants import (
    DATABASE_FILE,
    DATABASE_PATH,
    SCHEMA_FILE,
    SCHEMA_PATH,
    MIN_SPILLERE,
    MAX_SPILLERE,
    MIN_PERIODER,
    MAX_PERIODER,
    POSISJONER,
)

__all__ = [
    "DATABASE_FILE",
    "DATABASE_PATH",
    "SCHEMA_FILE",
    "SCHEMA_PATH",
    "MIN_SPILLERE",
    "MAX_SPILLERE",
    "MIN_PERIODER",
    "MAX_PERIODER",
    "POSISJONER",
]
