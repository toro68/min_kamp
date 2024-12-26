"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer database-relaterte klasser og funksjoner.
Se spesielt:
- avhengigheter.md -> Database
- system.md -> Database

Importerer og eksporterer følgende:
- NotFoundError fra errors.py for håndtering av ikke-eksisterende ressurser
- AppHandler fra handlers.app_handler for håndtering av applikasjonsdata
- AuthHandler fra handlers.auth_handler for autentisering
- KampHandler fra handlers.kamp_handler for håndtering av kamper
- SpillerHandler fra handlers.spiller_handler for håndtering av spillere
- get_db_path fra db_config for å hente database-sti
"""

from min_kamp.db.errors import NotFoundError
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.handlers.auth_handler import AuthHandler
from min_kamp.db.handlers.kamp_handler import KampHandler
from min_kamp.db.handlers.spiller_handler import SpillerHandler
from min_kamp.db.db_config import get_db_path

__all__ = [
    "NotFoundError",
    "AppHandler",
    "AuthHandler",
    "KampHandler",
    "SpillerHandler",
    "get_db_path",
]
