"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer database-utils.
Se spesielt:
- avhengigheter.md -> Database -> Utils
- system.md -> Database -> Utils
"""

from min_kamp.database.utils.session_state import init_session_state

__all__ = [
    "init_session_state",
]
