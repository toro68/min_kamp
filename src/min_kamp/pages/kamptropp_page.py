"""
Kamptropp-side for applikasjonen.
"""

import logging
import time
from typing import Any, Dict, Optional, Set

import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.errors import DatabaseError
from min_kamp.db.handlers.app_handler import AppHandler

logger = logging.getLogger(__name__)


def get_bruker_id() -> int:
    """Henter bruker ID fra query parameters."""
    bruker_id_str = st.query_params.get("bruker_id")
    if not bruker_id_str:
        error_msg = "Ingen bruker-ID funnet"
        logger.error(error_msg)
        raise ValueError(error_msg)
    try:
        return int(bruker_id_str)
    except (ValueError, TypeError):
        error_msg = "Ugyldig bruker-ID"
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_kamp_id() -> Optional[int]:
    """Henter kamp ID fra query parameters."""
    kamp_id_str = st.query_params.get("kamp_id")
    if not kamp_id_str:
        return None
    try:
        return int(kamp_id_str)
    except (ValueError, TypeError):
        return None


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


def slett_spiller_fra_kamptropp(
    app_handler: AppHandler, kamp_id: int, spiller_id: int
) -> None:
    """Sletter en spiller fra kamptroppen.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID til aktiv kamp
        spiller_id: ID til spilleren som skal slettes
    """
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM kamptropp WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id),
            )
            conn.commit()
        logger.info("Slettet spiller %s fra kamp %s", spiller_id, kamp_id)
    except Exception as e:
        logger.error(
            "Feil ved sletting av spiller %s fra kamp %s: %s",
            spiller_id,
            kamp_id,
            e,
        )
        st.error(f"Kunne ikke slette spiller med ID {spiller_id}")


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
                            kamp_id=kamp_id,
                            spiller_id=spiller["id"],
                            er_med=True,
                        )
                        st.rerun()
                else:
                    # Spiller er ikke valgt - oppdater i database
                    if spiller["er_med"]:
                        app_handler.kamp_handler.oppdater_spiller_status(
                            kamp_id=kamp_id,
                            spiller_id=spiller["id"],
                            er_med=False,
                        )
                        st.rerun()
                # Legg til en knapp for å slette spilleren
                if st.button("Slett", key=f"slett_{spiller['id']}"):
                    slett_spiller_fra_kamptropp(app_handler, kamp_id, spiller["id"])
                    st.success(f"{spiller['navn']} slettet")
                    st.rerun()

    except Exception as e:
        logger.error("Feil ved visning av spillere for %s: %s", posisjon, e)


def vis_valgt_tropp(kamptropp: Dict[str, Any], valgte_spillere: Set[int]) -> None:
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
        kamp_id = get_kamp_id()
        if not kamp_id:
            st.warning("Ingen aktiv kamp valgt")
            if st.button("Gå til oppsett for å velge kamp"):
                st.query_params["page"] = "oppsett"
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
