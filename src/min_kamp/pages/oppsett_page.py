"""
Oppsett side.
"""

import logging
from typing import Any, Optional, cast
from datetime import datetime, date

import streamlit as st
import pandas as pd

from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.utils.session_state import safe_get_session_state, set_session_state

logger = logging.getLogger(__name__)


def get_active_match() -> Optional[int]:
    """Henter aktiv kamp fra session state."""
    state = safe_get_session_state("current_kamp_id")
    if not state or not state.success:
        return None
    return cast(int, state.value)


def importer_spillere_fra_excel(app_handler: AppHandler, fil: Any) -> None:
    """Importerer spillere fra Excel-fil.

    Args:
        app_handler: AppHandler instans
        fil: Opplastet fil
    """
    try:
        # Les Excel-fil
        df = pd.read_excel(fil)

        # Sjekk at nødvendige kolonner finnes
        if "navn" not in df.columns or "posisjon" not in df.columns:
            st.error("Excel-filen må inneholde kolonnene: navn, posisjon")
            return

        # Hent bruker_id fra session state
        bruker_state = safe_get_session_state("bruker_id")
        if not bruker_state or not bruker_state.success:
            st.error("Ingen bruker funnet")
            return
        bruker_id = cast(int, bruker_state.value)

        # Opprett spillere
        antall_opprettet = 0
        for _, row in df.iterrows():
            try:
                app_handler.spiller_handler.opprett_spiller(
                    navn=row["navn"], posisjon=row["posisjon"], bruker_id=bruker_id
                )
                antall_opprettet += 1
            except Exception as e:
                logger.error("Feil ved opprettelse av spiller %s: %s", row["navn"], e)
                continue

        if antall_opprettet > 0:
            st.success(f"Opprettet {antall_opprettet} spillere")
        else:
            st.warning("Ingen spillere ble opprettet")

    except Exception as e:
        logger.error("Feil ved import av spillere: %s", e)
        st.error("Kunne ikke importere spillere")


def vis_spillerposisjoner(app_handler: AppHandler) -> None:
    """Viser og lar brukeren endre spillerposisjoner.

    Args:
        app_handler: AppHandler instans
    """
    try:
        # Legg til CSS for knapper
        st.markdown(
            """
            <style>
            .stButton > button {
                width: 150px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        bruker_state = safe_get_session_state("bruker_id")
        if not bruker_state or not bruker_state.success:
            st.error("Ingen bruker funnet")
            return
        bruker_id = cast(int, bruker_state.value)

        # Hent alle spillere
        spillere = app_handler.spiller_handler.hent_spillere(bruker_id)
        if not spillere:
            st.info("Ingen spillere funnet")
            return

        st.header("Endre spillerposisjoner")

        # Standard posisjoner
        standard_posisjoner = ["Keeper", "Forsvar", "Midtbane", "Angrep"]

        # Hent lagrede egendefinerte posisjoner fra session state
        egne_posisjoner = st.session_state.get("egne_posisjoner", [])

        # Legg til ny posisjon
        col1, col2 = st.columns([3, 1])
        with col1:
            ny_posisjon = st.text_input(
                "Legg til ny posisjon",
                key="ny_posisjon",
                help="Skriv inn en ny posisjon og klikk 'Legg til'",
            )
        with col2:
            if st.button("Legg til") and ny_posisjon:
                if (
                    ny_posisjon not in standard_posisjoner
                    and ny_posisjon not in egne_posisjoner
                ):
                    egne_posisjoner.append(ny_posisjon)
                    st.session_state.egne_posisjoner = egne_posisjoner
                    st.success(f"La til posisjon: {ny_posisjon}")
                    st.rerun()

        # Kombiner standard og egendefinerte posisjoner
        posisjoner = standard_posisjoner + egne_posisjoner

        # Vis hver spiller med mulighet for å endre posisjon
        for spiller in spillere:
            if not spiller or not isinstance(spiller.id, int):
                continue

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.write(spiller.navn)

            with col2:
                # Hvis spilleren har en posisjon som ikke er i listen,
                # legg den til i egne_posisjoner
                if spiller.posisjon not in posisjoner:
                    egne_posisjoner.append(spiller.posisjon)
                    st.session_state.egne_posisjoner = egne_posisjoner
                    posisjoner = standard_posisjoner + egne_posisjoner

                try:
                    posisjon_index = posisjoner.index(spiller.posisjon)
                except ValueError:
                    posisjon_index = 0

                ny_posisjon = st.selectbox(
                    "Posisjon",
                    options=posisjoner,
                    key=f"pos_{spiller.id}",
                    index=posisjon_index,
                )

            with col3:
                if ny_posisjon != spiller.posisjon:
                    if st.button("Lagre", key=f"save_{spiller.id}"):
                        try:
                            app_handler.spiller_handler.oppdater_spiller(
                                spiller_id=spiller.id,
                                navn=spiller.navn,
                                posisjon=ny_posisjon,
                                bruker_id=bruker_id,
                            )
                            st.success("Posisjon oppdatert")
                            st.rerun()
                        except Exception as e:
                            logger.error("Feil ved oppdatering av spiller: %s", e)
                            st.error("Kunne ikke oppdatere posisjon")

        # Vis og administrer egendefinerte posisjoner
        if egne_posisjoner:
            st.markdown("---")
            st.subheader("Egendefinerte posisjoner")
            for pos in egne_posisjoner:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(pos)
                with col2:
                    if st.button("Fjern", key=f"remove_{pos}"):
                        egne_posisjoner.remove(pos)
                        st.session_state.egne_posisjoner = egne_posisjoner
                        st.success(f"Fjernet posisjon: {pos}")
                        st.rerun()

    except Exception as e:
        logger.error("Feil ved visning av spillerposisjoner: %s", e)
        st.error("Kunne ikke vise spillerposisjoner")


def vis_oppsett_side(app_handler: AppHandler) -> None:
    """Rendrer oppsett-siden.

    Args:
        app_handler: AppHandler instans
    """
    try:
        # Sjekk autentisering
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            logger.debug("Bruker er ikke autentisert")
            return

        st.title("Oppsett")

        # Hent bruker_id fra session state
        bruker_state = safe_get_session_state("bruker_id")
        if not bruker_state or not bruker_state.success:
            st.error("Ingen bruker funnet")
            return
        bruker_id = cast(int, bruker_state.value)

        # Hent aktiv kamp
        active_match = get_active_match()
        if active_match:
            kamp_info = app_handler.kamp_handler.hent_kamp(active_match)
            if kamp_info:
                kamp_tekst = (
                    f"Aktiv kamp: {kamp_info['motstander']} - " f"{kamp_info['dato']}"
                )
                st.success(kamp_tekst)
            else:
                st.warning("Kunne ikke hente info om aktiv kamp")

        # Hent alle kamper
        kamper = app_handler.kamp_handler.hent_kamper(bruker_id)

        # Lag mapping av kamp-ID til visningsnavn
        kamp_map = {}
        for kamp in kamper:
            kamp_tekst = f"{kamp['motstander']} - {kamp['dato']}"
            kamp_map[kamp_tekst] = kamp["id"]

        # Vis dropdown for å velge kamp
        st.subheader("Velg kamp")
        valgt_kamp = st.selectbox("Velg kamp", ["Velg kamp..."] + list(kamp_map.keys()))

        if valgt_kamp != "Velg kamp...":
            if st.button("Sett som aktiv kamp"):
                set_session_state("current_kamp_id", kamp_map[valgt_kamp])
                st.success(f"Satt {valgt_kamp} som aktiv kamp")
                st.rerun()

        # Opprett ny kamp
        st.header("Opprett ny kamp")
        with st.form("ny_kamp_form"):
            motstander = st.text_input("Motstander")
            valgt_dato = st.date_input("Dato", value=datetime.now().date())
            hjemmebane = st.checkbox("Hjemmekamp", value=True)

            if st.form_submit_button("Opprett kamp"):
                if not motstander:
                    st.error("Du må fylle inn motstander")
                    return

                try:
                    # Opprett kamp
                    if not isinstance(valgt_dato, date):
                        st.error("Ugyldig dato")
                        return

                    kamp_id = app_handler.kamp_handler.opprett_kamp(
                        bruker_id=bruker_id,
                        motstander=motstander,
                        dato=valgt_dato.strftime("%Y-%m-%d"),
                        hjemmebane=hjemmebane,
                    )

                    if kamp_id:
                        st.success("Kamp opprettet!")
                        # Sett som aktiv kamp
                        set_session_state("current_kamp_id", kamp_id)
                        st.rerun()
                    else:
                        st.error("Kunne ikke opprette kamp")

                except Exception as e:
                    logger.error("Feil ved opprettelse av kamp: %s", e)
                    st.error("En feil oppstod ved opprettelse av kamp")

        # Last opp Excel-fil med spillere
        st.header("Importer spillere")
        st.write(
            "Last opp en Excel-fil med spillere. "
            "Filen må inneholde kolonnene: navn, posisjon"
        )

        fil = st.file_uploader(
            "Velg Excel-fil", type=["xlsx", "xls"], key="spiller_excel"
        )

        if fil is not None:
            if st.button("Importer spillere"):
                importer_spillere_fra_excel(app_handler, fil)

        # Vis og endre spillerposisjoner
        st.markdown("---")
        vis_spillerposisjoner(app_handler)

    except Exception as e:
        logger.error("Feil ved visning av oppsett-side: %s", e)
        st.error("Kunne ikke vise oppsett-siden")
