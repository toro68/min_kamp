"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer core-funksjoner.
Se spesielt:
- avhengigheter.md -> Core
- system.md -> Core

Importerer og eksporterer følgende:
- initialize_state fra session_state.py for initialisering av
  applikasjonstilstand
- safe_get_session_state fra session_state.py for sikker henting av
  sesjonstilstand
- safe_set_session_state fra session_state.py for sikker setting av
  sesjonstilstand
"""

from min_kamp.core.session_state import (
    initialize_state,
    safe_get_session_state,
    safe_set_session_state,
)

__all__ = ["initialize_state", "safe_get_session_state", "safe_set_session_state"]
