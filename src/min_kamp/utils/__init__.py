"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer utility-funksjoner.
Se spesielt:
- avhengigheter.md -> Utils
- system.md -> Utils

Importerer og eksporterer følgende:
- SchemaValidator fra database.utils.schema_validator for validering av
  databaseskjema
- ValidationResult fra database.utils.schema_validator for validering av
  resultater
- valider_antall_spillere fra validation.py for validering av antall spillere
- validate_and_convert fra validation.py for type-konvertering
- BytteplanValidator fra bytteplan_validator.py for validering av bytteplan
"""

from min_kamp.db.utils.schema_validator import SchemaValidator, ValidationResult
from min_kamp.utils.validation import valider_antall_spillere, validate_and_convert
from min_kamp.utils.bytteplan_validator import BytteplanValidator

__all__ = [
    "SchemaValidator",
    "ValidationResult",
    "valider_antall_spillere",
    "validate_and_convert",
    "BytteplanValidator",
]
