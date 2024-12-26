"""
Kamptropp-side for applikasjonen.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, Optional

import streamlit as st

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.errors import DatabaseError
from min_kamp.utils.streamlit_utils import get_session_state, set_session_state

logger = logging.getLogger(__name__)


def get_typed_handler(handler_name: str) -> Optional[AppHandler]:
    """Henter typet handler fra session state."""
    if handler_name != "app_handler":
        logger.error("Forventet app_handler, fikk %s", handler_name)
        return None

    handler = get_session_state(handler_name)
    if not handler:
        logger.error("Kunne ikke hente handler")
        return None
    if not isinstance(handler, AppHandler):
        logger.error("Forventet AppHandler, fikk %s", type(handler))
        return None
    return handler


def get_typed_session_state(key: str, default: Any = None) -> Any:
    """Henter typet session state verdi."""
    value = get_session_state(key)
    if value is None:
        return default
    return value


def get_bruker_id() -> int:
    """Henter bruker ID fra session state."""
    bruker_id = get_session_state("bruker_id")
    logger.debug("Bruker ID: %s", bruker_id)
    if not bruker_id:
        error_msg = "Ingen bruker-ID funnet"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return bruker_id


def opprett_indekser(app_handler: AppHandler) -> None:
    """Oppretter nødvendige indekser for kamptropp-siden."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            # Indeks for kamptropp kamp_id og spiller_id
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kamptropp_kamp_spiller
                ON kamptropp(kamp_id, spiller_id)
                """
            )
            conn.commit()
    except Exception as e:
        logger.error("Feil ved opprettelse av indekser: %s", e)
        raise DatabaseError("Kunne ikke opprette indekser") from e


def opprett_spiller(
    app_handler: AppHandler, bruker_id: int, navn: str, posisjon: str
) -> Optional[int]:
    """Opprett en ny spiller.

    Args:
        app_handler: AppHandler instans
        bruker_id: ID til brukeren som oppretter spilleren
        navn: Navn på spilleren
        posisjon: Posisjon til spilleren

    Returns:
        Optional[int]: ID til den nye spilleren hvis vellykket
    """
    try:
        spiller_id = app_handler.spiller_handler.opprett_spiller(
            bruker_id=bruker_id, navn=navn, posisjon=posisjon
        )
        return spiller_id
    except Exception as e:
        logger.error("Feil ved opprettelse av spiller: %s", e)
        return None


def vis_kamptropp_side(app_handler: AppHandler) -> None:
    """Viser kamptropp-siden.

    Args:
        app_handler: AppHandler instans
    """
    try:
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            return

        st.title("Kamptropp")

        # Opprett ny spiller
        with st.expander("Opprett ny spiller"):
            spiller_navn = st.text_input("Navn", key="spiller_navn")
            spiller_posisjon = st.selectbox(
                "Posisjon",
                ["Keeper", "Forsvar", "Midtbane", "Angrep"],
                key="spiller_posisjon",
            )

            if st.button("Opprett spiller"):
                if spiller_navn:
                    try:
                        bruker_id = get_bruker_id()
                        spiller_id = opprett_spiller(
                            app_handler, bruker_id, spiller_navn, spiller_posisjon
                        )
                        if spiller_id:
                            logger.info(
                                "Opprettet spiller %s: %s", spiller_id, spiller_navn
                            )
                            st.success("Spiller opprettet!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            error_msg = "Kunne ikke opprette spiller"
                            logger.error(error_msg)
                            st.error(error_msg)
                    except Exception as e:
                        error_msg = "Feil ved opprettelse av spiller"
                        logger.error("%s: %s", error_msg, e)
                        st.error(error_msg)
                else:
                    logger.warning("Mangler spillernavn")
                    st.error("Du må fylle inn navn på spilleren")

        # Hent aktiv kamp
        kamp_id = get_typed_session_state("current_kamp_id")
        if not kamp_id:
            st.warning("Ingen aktiv kamp valgt")
            if st.button("Gå til oppsett for å velge kamp"):
                st.session_state.selected_page = "oppsett"
                st.rerun()
            return

        # Hent kamptropp
        bruker_id = get_bruker_id()
        kamptropp = app_handler.kamp_handler.hent_kamptropp(
            kamp_id=kamp_id, bruker_id=bruker_id
        )

        # Vis spillere etter posisjon
        for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
            vis_spillere(kamptropp, posisjon, app_handler, kamp_id)

        # Vis oversikt over valgt tropp
        valgte_spillere = set()
        for spillere in kamptropp["spillere"].values():
            for spiller in spillere:
                if spiller["er_med"]:
                    valgte_spillere.add(spiller["id"])
        vis_valgt_tropp(kamptropp, valgte_spillere)

    except Exception as e:
        error_msg = "En feil oppstod ved visning av kamptropp-siden"
        logger.error("Feil ved visning av kamptropp-side: %s", e)
        st.error(error_msg)


def vis_spillere(
    kamptropp: Dict[str, Any], posisjon: str, app_handler: AppHandler, kamp_id: int
) -> None:
    """Viser spillere for en posisjon.

    Args:
        kamptropp: Kamptropp data
        posisjon: Posisjon å vise spillere for
        app_handler: AppHandler instans
        kamp_id: ID til aktiv kamp
    """
    try:
        spillere = kamptropp["spillere"][posisjon]
        if not spillere:
            return

        st.write(f"### {posisjon}")

        # Vis spillere i en tabell
        cols = st.columns(4)
        for i, spiller in enumerate(spillere):
            col = cols[i % 4]
            with col:
                if st.checkbox(
                    spiller["navn"],
                    value=spiller["er_med"],
                    key=f"spiller_{spiller['id']}",
                ):
                    # Spiller er valgt - oppdater i database
                    if not spiller["er_med"]:
                        app_handler.kamp_handler.oppdater_spiller_status(
                            kamp_id=kamp_id, spiller_id=spiller["id"], er_med=True
                        )
                        st.rerun()
                else:
                    # Spiller er ikke valgt - oppdater i database
                    if spiller["er_med"]:
                        app_handler.kamp_handler.oppdater_spiller_status(
                            kamp_id=kamp_id, spiller_id=spiller["id"], er_med=False
                        )
                        st.rerun()

    except Exception as e:
        logger.error("Feil ved visning av spillere for %s: %s", posisjon, e)


def vis_valgt_tropp(kamptropp: Dict[str, Any], valgte_spillere: set) -> None:
    """Viser oversikt over valgt tropp.

    Args:
        kamptropp: Kamptropp data
        valgte_spillere: Set med ID-er til valgte spillere
    """
    try:
        st.write("### Valgt tropp")

        # Finn valgte spillere
        alle_spillere = []
        for spillere in kamptropp["spillere"].values():
            alle_spillere.extend(spillere)

        valgte = [s for s in alle_spillere if s["id"] in valgte_spillere]

        # Vis valgte spillere i en tabell
        if valgte:
            data = []
            for spiller in valgte:
                data.append({"Navn": spiller["navn"], "Posisjon": spiller["posisjon"]})
            st.table(data)
        else:
            st.info("Ingen spillere valgt")

    except Exception as e:
        logger.error("Feil ved visning av valgt tropp: %s", e)


def hent_kamptropp(
    app_handler: AppHandler, kamp_id: int, bruker_id: int
) -> Dict[str, Any]:
    """Henter kamptropp for en kamp.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID til kampen
        bruker_id: ID til brukeren

    Returns:
        Dict[str, Any]: Kamptropp data
    """
    try:
        # Hent alle spillere
        spillere = app_handler.spiller_handler.hent_spillere(bruker_id)

        # Hent valgte spillere for kampen
        valgte_spillere = app_handler.kamp_handler.hent_kamptropp(
            kamp_id=kamp_id, bruker_id=bruker_id
        )

        # Organiser spillere etter posisjon
        spillere_etter_posisjon = defaultdict(list)
        for spiller in spillere:
            spillere_etter_posisjon[spiller.posisjon].append(
                {
                    "id": spiller.id,
                    "navn": spiller.navn,
                    "posisjon": spiller.posisjon,
                    "valgt": spiller.id in valgte_spillere,
                }
            )

        return {"spillere": spillere_etter_posisjon, "valgte_spillere": valgte_spillere}

    except Exception as e:
        logger.error("Feil ved henting av kamptropp: %s", e)
        return {"spillere": defaultdict(list), "valgte_spillere": []}


def lagre_kamptropp(app_handler: AppHandler, kamp_id: int, bruker_id: int) -> bool:
    """Lagrer kamptropp.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID til kampen
        bruker_id: ID til brukeren

    Returns:
        bool: True hvis lagringen var vellykket
    """
    try:
        app_state = get_typed_session_state("app_state", {})
        valgte = app_state.get("valgte_spillere", [])
        spillere = [{"spiller_id": spiller_id} for spiller_id in valgte]

        if app_handler.kamp_handler.oppdater_kamptropp(kamp_id, spillere):
            app_state["melding"] = "Kamptropp lagret!"
            app_state["melding_type"] = "success"
            app_state["opprinnelige_valgte_spillere"] = list(valgte)
            app_state["endret"] = False
            set_session_state("app_state", app_state)
            return True
        else:
            app_state["melding"] = "Kunne ikke lagre kamptropp"
            app_state["melding_type"] = "error"
            set_session_state("app_state", app_state)
            return False
    except Exception as e:
        logger.error("Feil ved lagring av kamptropp: %s", e)
        app_state = get_typed_session_state("app_state", {})
        error_msg = "En feil oppstod ved lagring av kamptroppen"
        app_state["melding"] = error_msg
        app_state["melding_type"] = "error"
        set_session_state("app_state", app_state)
        return False
