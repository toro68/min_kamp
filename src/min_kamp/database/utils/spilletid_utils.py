"""
Utility-funksjoner for håndtering av spilletid
"""

import logging
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from min_kamp.database.handlers.spilletid_handler import SpilletidHandler

logger = logging.getLogger(__name__)


def tell_spillere_per_periode(
    spilletid_summer: Dict[str, List[bool]], antall_perioder: int
) -> List[int]:
    """
    Teller antall spillere per periode med validering.

    Args:
        spilletid_summer: Dict med spiller_id som nøkkel og liste med
            boolske verdier for hver periode
        antall_perioder: Antall perioder som skal telles

    Returns:
        Liste med antall spillere per periode
    """
    if not isinstance(spilletid_summer, dict):
        logger.error("Ugyldig spilletid_summer type: %s", type(spilletid_summer))
        return [0] * antall_perioder

    if antall_perioder < 1:
        logger.error("Ugyldig antall_perioder: %d", antall_perioder)
        return [0]

    spillere_per_periode = [0] * antall_perioder

    try:
        for spiller_id, perioder in spilletid_summer.items():
            if len(perioder) != antall_perioder:
                logger.warning(
                    "Feil antall perioder for spiller %s: Forventet %d, fikk %d",
                    spiller_id,
                    antall_perioder,
                    len(perioder),
                )
                continue

            for periode, er_på in enumerate(perioder):
                if er_på:
                    spillere_per_periode[periode] += 1

        return spillere_per_periode

    except (TypeError, ValueError, AttributeError) as e:
        logger.error("Feil ved telling av spillere: %s", e)
        return [0] * antall_perioder


def oppdater_spilletid_summer(spilletid_handler: SpilletidHandler) -> bool:
    """
    Oppdaterer spilletid-summer i session state.

    Args:
        spilletid_handler: Handler for spilletid-operasjoner

    Returns:
        bool: True hvis oppdatering var vellykket
    """
    try:
        kamp_id = st.session_state.current_kamp_id
        if not kamp_id:
            logger.warning("Ingen aktiv kamp_id funnet")
            return False

        # Hent data via handler
        spilletid = spilletid_handler.hent_spilletid(
            int(kamp_id), int(st.session_state.spiller_id)
        )
        if spilletid is None:
            logger.error("Kunne ikke hente spilletid-data")
            return False

        # Oppdater session state
        st.session_state.spilletid = spilletid
        st.session_state.perioder = list(range(spilletid))

        # Tell opp spillere per periode
        st.session_state.spillere_per_periode = tell_spillere_per_periode(
            {str(st.session_state.spiller_id): [True] * spilletid}, spilletid
        )

        logger.debug("Oppdaterte spilletid: %s", spilletid)
        logger.debug(
            "Oppdaterte spillere per periode: %s", st.session_state.spillere_per_periode
        )
        return True

    except (KeyError, AttributeError, ValueError) as e:
        logger.error("Feil ved oppdatering av spilletid summer: %s", e)
        return False


def oppdater_spilletid_statistikk(
    spilletider: Dict[str, List[bool]], kamptropp: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Beregner spilletid-statistikk for hver spiller.

    Args:
        spilletider: Dict med spiller_id som nøkkel og liste med boolske verdier
        kamptropp: Liste med spillere i kamptroppen

    Returns:
        Dict med spiller_id som nøkkel og statistikk som verdi
    """
    try:
        statistikk = {}
        antall_perioder = len(next(iter(spilletider.values()))) if spilletider else 0

        for spiller in kamptropp:
            spiller_id = str(spiller["spiller_id"])
            perioder = spilletider.get(spiller_id, [False] * antall_perioder)

            statistikk[spiller_id] = {
                "navn": spiller["navn"],
                "posisjon": spiller["posisjon"],
                "spiller_nummer": spiller.get("spiller_nummer", ""),
                "perioder_spilt": sum(perioder),
                "prosent_spilt": (
                    round(sum(perioder) / antall_perioder * 100)
                    if antall_perioder
                    else 0
                ),
                "perioder_totalt": antall_perioder,
            }

        return statistikk
    except (KeyError, TypeError, ValueError, StopIteration) as e:
        logger.error("Feil ved oppdatering av spilletid-statistikk: %s", e)
        return {}


def analyser_spilletid(
    spilletid_handler: SpilletidHandler, kamp_id: str
) -> Tuple[pd.DataFrame, pd.Series, float, float]:
    """
    Analyserer spilletid for en gitt kamp.

    Args:
        spilletid_handler: Handler for spilletid-operasjoner
        kamp_id: ID for kampen som skal analyseres

    Returns:
        Tuple med:
        - DataFrame med spilletidsdata
        - Series med data for chart
        - Total spilletid
        - Gjennomsnittlig spilletid
    """
    try:
        total_spilletid = 0
        spilletid_per_spiller = []

        # Hent spilletid for hver spiller
        for spiller_id in st.session_state.kamptropp:
            minutter = spilletid_handler.hent_spilletid(int(kamp_id), spiller_id)
            if minutter is not None:
                total_spilletid += minutter
                spilletid_per_spiller.append(
                    {
                        "spiller_id": spiller_id,
                        "navn": st.session_state.spillere[spiller_id]["navn"],
                        "total_spilletid": minutter,
                    }
                )

        if not spilletid_per_spiller:
            return pd.DataFrame(), pd.Series(), 0.0, 0.0

        df = pd.DataFrame(spilletid_per_spiller)

        # Forbered data for Streamlit bar chart
        chart_data = (
            df.set_index("navn")["total_spilletid"] if not df.empty else pd.Series()
        )

        gjennomsnitt = (
            total_spilletid / len(spilletid_per_spiller)
            if spilletid_per_spiller
            else 0.0
        )

        return (df, chart_data, total_spilletid, gjennomsnitt)

    except (KeyError, ValueError, AttributeError) as e:
        logger.error("Feil ved analysering av spilletid: %s", e)
        return pd.DataFrame(), pd.Series(), 0.0, 0.0
