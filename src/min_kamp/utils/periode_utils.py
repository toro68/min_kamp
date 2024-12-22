"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hjelpefunksjoner for periodeberegning.
Se spesielt:
- avhengigheter.md -> Utils -> Periode
- system.md -> Utils -> Periode
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


def er_gyldig(periode: int, antall_perioder: int) -> bool:
    """
    Sjekker om en periode er gyldig

    Args:
        periode: Periodenummer
        antall_perioder: Totalt antall perioder

    Returns:
        bool: True hvis perioden er gyldig, False ellers
    """
    return 1 <= periode <= antall_perioder


def beregn_antall_perioder(kamptid: int, periode_lengde: int) -> int:
    """
    Beregner antall perioder basert på kamptid og periodelengde

    Args:
        kamptid: Total kamptid i minutter
        periode_lengde: Lengde på hver periode i minutter

    Returns:
        int: Antall perioder
    """
    return math.ceil(kamptid / periode_lengde)


def valider_periode_konfigurasjon(
    kamptid: int, periode_lengde: int, min_perioder: int, max_perioder: int
) -> Optional[str]:
    """
    Validerer periodekonfigurasjon

    Args:
        kamptid: Total kamptid i minutter
        periode_lengde: Lengde på hver periode i minutter
        min_perioder: Minimum antall perioder
        max_perioder: Maksimum antall perioder

    Returns:
        Optional[str]: Feilmelding hvis konfigurasjonen er ugyldig, None ellers
    """
    try:
        antall_perioder = beregn_antall_perioder(kamptid, periode_lengde)

        if antall_perioder < min_perioder:
            return f"For få perioder ({antall_perioder}). Minimum er {min_perioder}."

        if antall_perioder > max_perioder:
            return (
                f"For mange perioder ({antall_perioder}). Maksimum er {max_perioder}."
            )

        return None

    except Exception as e:
        logger.error(f"Feil ved validering av periodekonfigurasjon: {e}", exc_info=True)
        return "Kunne ikke validere periodekonfigurasjon"
