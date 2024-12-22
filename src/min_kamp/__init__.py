"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedmodul for Min Kamp applikasjonen.
Se spesielt:
- avhengigheter.md
- system.md
"""

from min_kamp.database import (
    DatabaseHandler,
    AppHandler,
    AuthHandler,
    BaseHandler,
    BytteplanHandler,
    KampHandler,
    SpillerHandler,
    StateHandler,
)

__version__ = "1.0.0"

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
