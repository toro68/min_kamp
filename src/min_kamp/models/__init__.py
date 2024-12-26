"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer modeller.
Se spesielt:
- avhengigheter.md -> Models
- system.md -> Models

Importerer og eksporterer følgende:
- Kamp og KampDict fra kamp_model.py for kampdata
- Spiller og SpillerDict fra spiller_model.py for spillerdata
- Bytteplan og BytteplanDict fra bytteplan_model.py for bytteplandata
"""

from min_kamp.models.kamp_model import Kamp, KampDict
from min_kamp.models.spiller_model import Spiller, SpillerDict
from min_kamp.models.bytteplan_model import Bytteplan, BytteplanDict

__all__ = ["Kamp", "KampDict", "Spiller", "SpillerDict", "Bytteplan", "BytteplanDict"]
