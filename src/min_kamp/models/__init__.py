"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Datamodeller for applikasjonen.
Se spesielt:
- avhengigheter.md -> Models
- system.md -> Models
"""

from .kamp_model import Kamp, KampDict
from .spiller_model import Spiller, SpillerDict
from .bytteplan_model import Bytteplan, BytteplanDict

__all__ = ["Kamp", "KampDict", "Spiller", "SpillerDict", "Bytteplan", "BytteplanDict"]
