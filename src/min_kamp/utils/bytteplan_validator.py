"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Valideringsklasse for bytteplan.
Se spesielt:
- avhengigheter.md -> Utils -> Bytteplan
- system.md -> Utils -> Bytteplan
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValideringsResultat:
    """Holder resultatet av en validering."""

    er_gyldig: bool
    feilmeldinger: List[str]
    advarsler: List[str]


class BytteplanValidator:
    """Valideringsklasse for bytteplan."""

    def __init__(
        self, min_spillere: int = 5, max_spillere: int = 7, periode_lengde: int = 5
    ):
        self.min_spillere = min_spillere
        self.max_spillere = max_spillere
        self.periode_lengde = periode_lengde

    def valider_bytteplan(
        self, bytteplan: List[Dict[str, Any]], antall_perioder: int
    ) -> ValideringsResultat:
        """Validerer en komplett bytteplan.

        Args:
            bytteplan: Liste med bytter
            antall_perioder: Totalt antall perioder

        Returns:
            ValideringsResultat med status og eventuelle feilmeldinger/advarsler
        """
        feilmeldinger = []
        advarsler = []

        # Valider hver periode
        for periode in range(antall_perioder):
            periode_bytter = [b for b in bytteplan if b["periode"] == periode]

            # Tell antall spillere på banen
            spillere_paa = len([b for b in periode_bytter if b["er_paa"]])

            if spillere_paa < self.min_spillere:
                msg = (
                    "For få spillere på banen i periode "
                    f"{periode} ({spillere_paa}, minimum "
                    f"{self.min_spillere})"
                )
                feilmeldinger.append(msg)

            if spillere_paa > self.max_spillere:
                msg = (
                    "For mange spillere på banen i periode "
                    f"{periode} ({spillere_paa}, maksimum "
                    f"{self.max_spillere})"
                )
                feilmeldinger.append(msg)

        return ValideringsResultat(
            er_gyldig=len(feilmeldinger) == 0,
            feilmeldinger=feilmeldinger,
            advarsler=advarsler,
        )

    def valider_spilletid(
        self, spilletider: Dict[int, int], antall_perioder: int
    ) -> ValideringsResultat:
        """Validerer spilletidsfordeling.

        Args:
            spilletider: Dictionary med spiller_id -> minutter
            antall_perioder: Totalt antall perioder

        Returns:
            ValideringsResultat med status og eventuelle feilmeldinger/advarsler
        """
        feilmeldinger = []
        advarsler = []

        total_kamptid = antall_perioder * self.periode_lengde

        # Sjekk total spilletid
        for spiller_id, minutter in spilletider.items():
            if minutter > total_kamptid:
                msg = (
                    f"Spiller {spiller_id} har mer spilletid "
                    f"({minutter} min) enn total kamptid "
                    f"({total_kamptid} min)"
                )
                feilmeldinger.append(msg)

        # Sjekk balanse i spilletid
        if len(spilletider) > 1:
            gjennomsnitt = sum(spilletider.values()) / len(spilletider)
            max_avvik = total_kamptid * 0.2  # 20% avvik tillatt

            for spiller_id, minutter in spilletider.items():
                avvik = abs(minutter - gjennomsnitt)
                if avvik > max_avvik:
                    msg = (
                        f"Spiller {spiller_id} har stort avvik "
                        f"({minutter} min vs. gjennomsnitt "
                        f"{gjennomsnitt:.1f} min)"
                    )
                    advarsler.append(msg)

        return ValideringsResultat(
            er_gyldig=len(feilmeldinger) == 0,
            feilmeldinger=feilmeldinger,
            advarsler=advarsler,
        )

    def valider_posisjoner(
        self, bytteplan: Dict[str, Any], min_per_posisjon: Dict[str, int]
    ) -> ValideringsResultat:
        """Validerer posisjonsdekning i bytteplan.

        Args:
            bytteplan: Komplett bytteplan
            min_per_posisjon: Minimum antall spillere per posisjon

        Returns:
            ValideringsResultat med status og eventuelle feilmeldinger/advarsler
        """
        feilmeldinger = []
        advarsler = []

        # Tell spillere per posisjon som er på banen
        posisjoner: Dict[str, int] = {}
        for spiller_info in bytteplan.values():
            if spiller_info.get("er_paa", False):
                pos = spiller_info.get("posisjon", "ukjent")
                posisjoner[pos] = posisjoner.get(pos, 0) + 1

        # Sjekk minimumskrav
        for posisjon, minimum in min_per_posisjon.items():
            antall = posisjoner.get(posisjon, 0)
            if antall < minimum:
                msg = (
                    f"For få spillere i posisjon {posisjon} "
                    f"({antall}, minimum {minimum})"
                )
                feilmeldinger.append(msg)

        # Sjekk balanse
        if "Keeper" in posisjoner and posisjoner["Keeper"] > 1:
            msg = "Mer enn én keeper på banen " f"({posisjoner['Keeper']})"
            advarsler.append(msg)

        return ValideringsResultat(
            er_gyldig=len(feilmeldinger) == 0,
            feilmeldinger=feilmeldinger,
            advarsler=advarsler,
        )
