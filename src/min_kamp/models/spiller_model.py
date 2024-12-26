"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Definerer datamodell for spiller.
Se spesielt:
- avhengigheter.md -> Models -> Spiller
- system.md -> Models -> Spiller
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict, Optional


class SpillerDict(TypedDict):
    """Dictionary type for spillerdata"""

    id: Optional[int]
    navn: str
    posisjon: str
    bruker_id: int
    aktiv: bool
    opprettet_dato: Optional[datetime]
    sist_oppdatert: Optional[datetime]


@dataclass
class Spiller:
    """Dataklasse for spiller"""

    navn: str
    posisjon: str
    bruker_id: int
    aktiv: bool = True
    id: Optional[int] = None
    opprettet_dato: Optional[datetime] = None
    sist_oppdatert: Optional[datetime] = None
