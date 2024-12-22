"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hjelpefunksjoner for applikasjonen.
Se spesielt:
- avhengigheter.md -> Utils
- system.md -> Utils
"""

from .periode_utils import (
    beregn_antall_perioder,
    er_gyldig,
    valider_periode_konfigurasjon,
)
from .validation import (
    ValidationResult,
    SchemaValidator,
    valider_antall_spillere,
    validate_and_convert,
)

__all__ = [
    "beregn_antall_perioder",
    "er_gyldig",
    "valider_periode_konfigurasjon",
    "valider_antall_spillere",
    "validate_and_convert",
    "ValidationResult",
    "SchemaValidator",
]
