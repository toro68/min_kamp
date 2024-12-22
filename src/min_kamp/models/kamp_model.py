"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer datamodell for kamp.
Se spesielt:
- avhengigheter.md -> Models -> Kamp
- system.md -> Models -> Kamp
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


class KampDict(TypedDict):
    """Dictionary type for kampdata"""

    dato: datetime
    motstander: str
    hjemmebane: bool
    antall_perioder: int
    spillere_per_periode: int


@dataclass
class Kamp:
    """Dataklasse for kamp"""

    dato: datetime
    motstander: str
    hjemmebane: bool
    antall_perioder: int
    spillere_per_periode: int
