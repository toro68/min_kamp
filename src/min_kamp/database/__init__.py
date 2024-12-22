"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer databasemodulen.
Se spesielt:
- avhengigheter.md -> Database
- system.md -> Database
"""

from min_kamp.database.db_handler import DatabaseHandler
from min_kamp.database.handlers import (
    AppHandler,
    AuthHandler,
    BaseHandler,
    BytteplanHandler,
    KampHandler,
    SpillerHandler,
    StateHandler,
)

__all__ = [
    "DatabaseHandler",
    "AppHandler",
    "AuthHandler",
    "BaseHandler",
    "BytteplanHandler",
    "KampHandler",
    "SpillerHandler",
    "StateHandler",
]
