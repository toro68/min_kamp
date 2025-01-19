"""
Spilletid utils.
"""

import logging
from typing import Dict, List

import streamlit as st
from min_kamp.db.handlers.spilletid_handler import SpilletidHandler

logger = logging.getLogger(__name__)


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
        antall = sum(
            1
            for spiller_perioder in spilletider.values()
            if (periode < len(spiller_perioder) and spiller_perioder[periode])
        )
        resultat[periode] = antall
    return resultat


def oppdater_spilletid_summer(spilletid_handler: SpilletidHandler) -> bool:
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
        spilletid_data = spilletid_handler.hent_spilletid(int(str(kamp_id)))
        if spilletid_data is None:
            logger.error("Kunne ikke hente spilletid-data")
            return False

        # Finn spilletid for gjeldende spiller
        spiller_id = st.query_params.get("spiller_id")
        if not spiller_id:
            logger.warning("Ingen spiller_id funnet")
            return False

        spiller_spilletid = None
        for spilletid_rad in spilletid_data:
            if spilletid_rad["spiller_id"] == int(spiller_id):
                spiller_spilletid = spilletid_rad["minutter"]
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
