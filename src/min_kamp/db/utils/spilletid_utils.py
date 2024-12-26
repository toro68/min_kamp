"""
Utility-funksjoner for håndtering av spilletid
"""

import logging
from typing import Any, Dict, List, Tuple

import pandas as pd

from min_kamp.db.handlers.spilletid_handler import SpilletidHandler
from min_kamp.utils.streamlit_utils import get_session_state, set_session_state

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
        kamp_id = get_session_state("current_kamp_id")
        if not kamp_id or not str(kamp_id).isdigit():
            logger.warning("Ingen gyldig kamp_id funnet")
            return False

        # Hent data via handler
        spilletid_data = spilletid_handler.hent_spilletid(int(str(kamp_id)))
        if spilletid_data is None:
            logger.error("Kunne ikke hente spilletid-data")
            return False

        # Finn spilletid for gjeldende spiller
        spiller_id = get_session_state("spiller_id")
        if not spiller_id:
            logger.warning("Ingen spiller_id funnet")
            return False

        spiller_spilletid = None
        for spilletid_rad in spilletid_data:
            if spilletid_rad["spiller_id"] == spiller_id:
                spiller_spilletid = spilletid_rad["minutter"]
                break

        if spiller_spilletid is None:
            logger.warning("Ingen spilletid funnet for spiller %s", spiller_id)
            return False

        # Oppdater session state
        set_session_state("spilletid", spiller_spilletid)
        set_session_state("perioder", list(range(spiller_spilletid)))

        # Tell opp spillere per periode
        spillere_per_periode = tell_spillere_per_periode(
            {str(spiller_id): [True] * spiller_spilletid}, spiller_spilletid
        )
        set_session_state("spillere_per_periode", spillere_per_periode)

        logger.debug("Oppdaterte spilletid: %s", spiller_spilletid)
        logger.debug("Oppdaterte spillere per periode: %s", spillere_per_periode)
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

        # Hent spilletid for alle spillere
        spilletid_data = spilletid_handler.hent_spilletid(int(kamp_id))
        if spilletid_data:
            spillere_data = get_session_state("spillere", {})
            spillere: Dict[str, Dict[str, Any]] = (
                spillere_data if isinstance(spillere_data, dict) else {}
            )

            for spilletid_rad in spilletid_data:
                spiller_id = str(spilletid_rad["spiller_id"])
                minutter = spilletid_rad["minutter"]

                if (
                    minutter is not None
                    and isinstance(spillere, dict)
                    and spiller_id in spillere
                ):
                    total_spilletid += minutter
                    spiller_info = spillere[spiller_id]
                    spilletid_per_spiller.append(
                        {
                            "spiller_id": spiller_id,
                            "navn": spiller_info.get("navn", "Ukjent"),
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
