"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer alle handlers.
Se spesielt:
- avhengigheter.md -> Database -> Handlers
- system.md -> Database -> Handlers
"""

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.handlers.auth_handler import AuthHandler
from min_kamp.db.handlers.bytteplan_handler import BytteplanHandler
from min_kamp.db.handlers.kamp_handler import KampHandler
from min_kamp.db.handlers.spiller_handler import SpillerHandler

__all__ = [
    "AppHandler",
    "AuthHandler",
    "BytteplanHandler",
    "KampHandler",
    "SpillerHandler",
]
