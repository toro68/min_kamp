"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
from typing import Dict, List, Tuple

import streamlit as st
from min_kamp.db.handlers.bytteplan_handler import BytteplanHandler

logger = logging.getLogger("kampplanlegger")


def tell_spillere_per_periode(
    spilletider: Dict[str, List[bool]], antall_perioder: int
) -> Dict[int, int]:
    """
    Teller antall spillere per periode.

    Args:
        spilletider: Dict med spilletider per spiller
        antall_perioder: Antall perioder totalt

    Returns:
        Dict med antall spillere per periode
    """
    resultat = {}
    for periode in range(antall_perioder):
        antall = 0
        for spiller_perioder in spilletider.values():
            if periode < len(spiller_perioder):
                if spiller_perioder[periode]:
                    antall += 1
        resultat[periode] = antall
    return resultat


def oppdater_spilletid_summer(spilletid_handler: BytteplanHandler) -> bool:
    """
    Oppdaterer spilletid-summer i query parameters.

    Args:
        spilletid_handler: Handler for spilletid-operasjoner

    Returns:
        bool: True hvis oppdatering var vellykket
    """
    try:
        kamp_id = st.query_params.get("kamp_id")
        if not kamp_id or not str(kamp_id).isdigit():
            logger.warning("Ingen gyldig kamp_id funnet")
            return False

        # Hent data via handler
        # NB: spilletid_data er en liste med dictionaries som inneholder
        # spiller_id og minutter, ikke en liste med Spilletid-objekter
        spilletid_data = spilletid_handler.hent_spilletid(int(str(kamp_id)))
        if not spilletid_data:
            logger.error("Kunne ikke hente spilletid-data")
            return False

        # Finn spilletid for gjeldende spiller
        spiller_id = st.query_params.get("spiller_id")
        if not spiller_id:
            logger.warning("Ingen spiller_id funnet")
            return False

        # Behandle spilletid_data som en liste med dictionaries
        spiller_spilletid = None
        for spilletid_rad in spilletid_data:
            if spilletid_rad["spiller_id"] == int(spiller_id):  # type: ignore
                spiller_spilletid = spilletid_rad["minutter"]  # type: ignore
                break

        if spiller_spilletid is None:
            logger.warning("Ingen spilletid funnet for spiller %s", spiller_id)
            return False

        # Oppdater query parameters
        st.query_params["spilletid"] = str(spiller_spilletid)
        st.query_params["perioder"] = ",".join(str(i) for i in range(spiller_spilletid))

        # Tell opp spillere per periode
        spillere_per_periode = tell_spillere_per_periode(
            {str(spiller_id): [True] * spiller_spilletid}, spiller_spilletid
        )
        st.query_params["spillere_per_periode"] = str(spillere_per_periode)

        logger.debug("Oppdaterte spilletid: %s", spiller_spilletid)
        logger.debug("Oppdaterte spillere per periode: %s", spillere_per_periode)
        return True

    except Exception as e:
        logger.error("Feil ved oppdatering av spilletid: %s", e)
        return False


def hent_bytter(spillere: dict, periode_idx: int) -> Tuple[List[str], List[str]]:
    """Henter bytter inn og ut mellom to perioder.

    Args:
        spillere: Dictionary med spillerdata
        periode_idx: Periode å hente bytter for

    Returns:
        Tuple med to lister - spillere som byttes inn og ut
    """
    bytter_inn = []
    bytter_ut = []

    if periode_idx > 0:  # Sjekker bare bytter etter første periode
        for navn, spiller in spillere.items():
            # Håndter både gammel (bool) og ny (dict) struktur
            forrige_periode = spiller["perioder"].get(periode_idx - 1, False)
            denne_periode = spiller["perioder"].get(periode_idx, False)

            # Konverter til bool hvis det er dict-struktur
            forrige = (
                forrige_periode.get("er_paa", False)
                if isinstance(forrige_periode, dict)
                else forrige_periode
            )
            denne = (
                denne_periode.get("er_paa", False)
                if isinstance(denne_periode, dict)
                else denne_periode
            )

            if not forrige and denne:  # Inn på banen
                bytter_inn.append(navn)
            elif forrige and not denne:  # Ut av banen
                bytter_ut.append(navn)

    return sorted(bytter_inn), sorted(bytter_ut)


def formater_bytter(bytter_inn: List[str], bytter_ut: List[str]) -> str:
    """Formaterer bytter til en lesbar streng.

    Args:
        bytter_inn: Liste med navn på spillere som kommer inn
        bytter_ut: Liste med navn på spillere som går ut

    Returns:
        Formatert streng med bytter, f.eks. "INN: Spiller1, Spiller2 |
        UT: Spiller3". Returnerer "-" hvis ingen bytter
    """
    if not bytter_inn and not bytter_ut:
        return "-"

    bytter_deler = []
    if bytter_inn:
        bytter_deler.append(f"INN: {', '.join(bytter_inn)}")
    if bytter_ut:
        bytter_deler.append(f"UT: {', '.join(bytter_ut)}")
    return " | ".join(bytter_deler)
