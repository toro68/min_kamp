"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Datamodeller for bytteplan.
Se spesielt:
- avhengigheter.md -> Models
- system.md -> Models
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict


class BytteplanDict(TypedDict):
    """TypedDict for bytteplandata"""

    kamp_id: int
    spiller_id: int
    periode: int
    er_paa: bool


@dataclass
class Bytteplan:
    """Dataklasse for bytteplan"""

    bytteplan_id: int
    kamp_id: int
    spiller_id: int
    periode: int
    er_paa: bool
    opprettet: datetime
    oppdatert: Optional[datetime] = None


@dataclass
class Spilletid:
    spiller_id: int
    kamp_id: int
    minutter: int
