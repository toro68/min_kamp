"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer datamodell for spiller.
Se spesielt:
- avhengigheter.md -> Models -> Spiller
- system.md -> Models -> Spiller
"""

from dataclasses import dataclass
from typing import TypedDict


class SpillerDict(TypedDict):
    """Dictionary type for spillerdata"""

    navn: str
    posisjon: str
    aktiv: bool


@dataclass
class Spiller:
    """Dataklasse for spiller"""

    navn: str
    posisjon: str
    aktiv: bool = True
