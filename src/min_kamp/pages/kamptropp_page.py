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
    app_handler: AppHandler,
    kamp_id: int,
    spiller_id: int,
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
            logger.debug(
                "Kaller slett_spiller_fra_kamptropp med kamp_id=%s, spiller_id=%s",
                kamp_id,
                spiller_id,
            )
            # Oppdaterer spillerens status til inaktiv (er_med = 0)
            cursor.execute(
                "UPDATE kamptropp SET er_med = 0 "
                "WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id),
            )
            rows = cursor.rowcount
            logger.debug("Antall oppdaterte rader: %s", rows)
            conn.commit()

        logger.info(
            "Sett spiller %s som inaktiv for kamp %s",
            spiller_id,
            kamp_id,
        )
    except Exception as e:
        logger.error(
            "Feil ved oppdatering av spiller %s til inaktiv for kamp %s: %s",
            spiller_id,
            kamp_id,
            e,
        )
        st.error(
            f"Kunne ikke sette spiller inaktiv med ID {spiller_id}"
        )


def vis_spillere(
    kamptropp: Dict[str, Any],
    posisjon: str,
    app_handler: AppHandler,
    kamp_id: int,
) -> None:
    """Viser spillere for en posisjon.

    Args:
        kamptropp: Kamptropp data
        posisjon: Posisjon å vise spillere for
        app_handler: AppHandler instans
        kamp_id: ID til aktiv kamp
    """
    try:
        # Filtrer kun aktive spillere
        active_spillere = [
            s
            for s in kamptropp["spillere"][posisjon]
            if s["er_med"]
        ]
        if not active_spillere:
            return

        st.write(f"### {posisjon}")

        # Vis hver aktiv spiller med navn og en 'Fjern'-knapp
        for spiller in active_spillere:
            col_name, col_action = st.columns([3, 1])
            with col_name:
                st.write(spiller["navn"])
            with col_action:
                if st.button(
                    "Fjern",
                    key=f"fjern_{spiller['id']}",
                ):
                    slett_spiller_fra_kamptropp(app_handler, kamp_id, spiller["id"])
                    st.success(
                        f"{spiller['navn']} fjernet"
                    )
                    st.rerun()
    except Exception as e:
        logger.error(
            "Feil ved visning av spillere for %s: %s",
            posisjon,
            e,
        )


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
