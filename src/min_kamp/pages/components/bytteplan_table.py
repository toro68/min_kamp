"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import json
import logging
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from min_kamp.database.db_handler import DatabaseHandler
from min_kamp.database.handlers.bytteplan_handler import BytteplanHandler
from min_kamp.database.handlers.state_handler import StateHandler
from min_kamp.database.utils.bytteplan_utils import BytteplanUtils

logger = logging.getLogger(__name__)


class BytteplanTable:
    """Klasse for håndtering av bytteplan-tabellen"""

    def __init__(self):
        """Initialiserer BytteplanTable med nødvendige handlers"""
        self.db_handler = DatabaseHandler()
        self.bytteplan_handler = BytteplanHandler(self.db_handler)
        self.bytteplan_utils = BytteplanUtils(self.bytteplan_handler)
        self.state_handler = StateHandler(self.db_handler)

    def vis_bytteplan_table(
        self,
        kamptropp: Dict[str, Dict[str, Any]],
        antall_perioder: int,
        periode_lengde: int,
        alle_spilletider: Dict[str, List[bool]],
    ) -> None:
        """Hovedfunksjon for bytteplan-tabellen"""
        try:
            if not kamptropp:
                st.warning("Ingen spillere i kamptroppen")
                return

            # Beregn faktisk antall perioder og sjekk om endring
            kamptid = st.session_state.get("kamptid", 60)
            periode_lengde = st.session_state.get("periode_lengde", 5)
            faktisk_perioder = kamptid // periode_lengde

            # Hvis antall perioder har endret seg
            if faktisk_perioder != len(st.session_state.get("perioder", [])):
                logger.warning(
                    f"Antall perioder endret fra {len(st.session_state.get('perioder', []))} til {faktisk_perioder}"
                )

                # Oppdater state og rerun
                self.state_handler.lagre_tilstand("perioder", str(faktisk_perioder))
                st.rerun()
                return

            # Vis header med tidsmarkører
            cols = st.columns([3, 2] + [1] * faktisk_perioder)
            cols[0].write("Spiller")
            cols[1].write("Total tid")
            for i in range(faktisk_perioder):
                start_tid = i * periode_lengde
                slutt_tid = (i + 1) * periode_lengde
                cols[i + 2].write(f"{start_tid}'-{slutt_tid}'")

            # Vis spillerradene
            for spiller_id, spiller_info in kamptropp.items():
                spilletider = alle_spilletider.get(
                    spiller_id, [False] * faktisk_perioder
                )
                self._vis_spiller_rad(
                    spiller_id,
                    spiller_info["navn"],
                    faktisk_perioder,
                    periode_lengde,
                    spilletider[
                        :faktisk_perioder
                    ],  # Kutt eller utvid til riktig lengde
                )

        except Exception as e:
            logger.error(f"Feil i bytteplan_table: {e}", exc_info=True)
            st.error("Kunne ikke vise bytteplan")

    def vis_aktive_spillere(self, df: pd.DataFrame) -> None:
        """Viser aktive spillere i bytteplan-tabellen"""
        st.subheader("Spillere på banen")
        # Konverter DataFrame til liste av dict med streng-nøkler
        spillere_dict = [
            {str(k): v for k, v in record.items()}
            for record in df[df["er_paa_banen"]].to_dict("records")
        ]

        aktive_df = self.bytteplan_utils.generer_posisjonssortert_df(
            spillere_dict,
            st.session_state.get("current_periode", 0),
        )
        st.dataframe(aktive_df, hide_index=True)

    def vis_bytteplan(
        self,
        df: pd.DataFrame,
        antall_perioder: int,
        periode_lengde: int,
        alle_spilletider: Dict[str, List[bool]],
    ) -> None:
        """
        Viser bytteplan-tabellen

        Args:
            df: DataFrame med spillerdata
            antall_perioder: Antall perioder i kampen
            periode_lengde: Lengde per periode i minutter
            alle_spilletider: Dictionary med spilletider per spiller
        """
        st.subheader("Bytteplan")

        # Sorter spillere etter posisjon først
        posisjon_orden = {
            "Keeper": 1,
            "Forsvar": 2,
            "Midtbane": 3,
            "Angrep": 4,
            "Benk": 5,
        }

        if "posisjon" not in df.columns:
            logger.warning("Mangler posisjonskolonne i DataFrame")
            df["posisjon"] = "Benk"  # Sett standardposisjon

        df["posisjon_orden"] = df["posisjon"].map(posisjon_orden)
        df = df.sort_values(["posisjon_orden", "navn"])

        # Vis header
        cols = st.columns([3, 2] + [1] * antall_perioder)
        cols[0].write("Spiller")
        cols[1].write("Total tid")
        for i in range(antall_perioder):
            cols[i + 2].write(f"{i*periode_lengde}'")

        # Vis spillerdata
        for _, row in df.iterrows():
            self._vis_spiller_rad(
                spiller_id=row["spiller_id"],
                spillernavn=row["navn"],
                antall_perioder=antall_perioder,
                periode_lengde=periode_lengde,
                spilletider=alle_spilletider.get(
                    row["spiller_id"], [False] * antall_perioder
                ),
            )

    def _vis_spiller_rad(
        self,
        spiller_id: str,
        spillernavn: str,
        antall_perioder: int,
        periode_lengde: int,
        spilletider: List[bool],
    ) -> None:
        """Viser én rad i bytteplan-tabellen"""
        cols = st.columns([3, 2] + [1] * antall_perioder)

        # Navn og total spilletid
        cols[0].write(spillernavn)
        total_spilletid = sum(1 for x in spilletider if x) * periode_lengde
        cols[1].write(f"{total_spilletid} min")

        # Sjekk om vi trenger å nullstille checkboxer
        if len(spilletider) != antall_perioder:
            logger.warning(
                f"Feil antall perioder for {spillernavn} ({len(spilletider)} != {antall_perioder})"
            )
            # Fjern gamle checkbox states
            for i in range(max(len(spilletider), antall_perioder)):
                checkbox_key = f"check_{spiller_id}_{i}"
                if checkbox_key in st.session_state:
                    del st.session_state[checkbox_key]
                    logger.debug(f"Fjernet gammel checkbox state: {checkbox_key}")

            # Opprett nye spilletider
            spilletider = [False] * antall_perioder
            logger.info(f"Reinitialiserte spilletider for {spillernavn}")

        # Vis checkboxer
        for periode in range(antall_perioder):
            with cols[periode + 2]:
                checkbox_key = f"check_{spiller_id}_{periode}"

                # Initialiser checkbox-state hvis den ikke finnes
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = bool(spilletider[periode])

                st.checkbox(
                    "På banen",
                    key=checkbox_key,
                    value=st.session_state[checkbox_key],
                    label_visibility="collapsed",
                    on_change=self._on_checkbox_change,
                    args=(spiller_id, periode),
                )

    def _on_checkbox_change(self, spiller_id: str, periode: int) -> None:
        """
        Håndterer endringer i checkbox-status.

        Args:
            spiller_id: ID for spilleren som endres
            periode: Periodenummer som endres
        """
        try:
            checkbox_key = f"check_{spiller_id}_{periode}"
            logger.debug(f"Checkbox endret: {checkbox_key}")

            ny_verdi = st.session_state.get(checkbox_key, False)
            logger.debug(f"Ny verdi for {checkbox_key}: {ny_verdi}")

            # Sjekk om perioden fortsatt er gyldig
            perioder_str = self.state_handler.hent_tilstand("perioder")
            if not perioder_str:
                logger.warning("Ingen perioder funnet")
                return

            try:
                perioder = json.loads(perioder_str)
            except json.JSONDecodeError:
                perioder = int(perioder_str)
                perioder = list(range(perioder))

            if periode >= len(perioder):
                logger.warning(f"Ugyldig periode {periode} - resetter checkbox")
                self.state_handler.lagre_tilstand(checkbox_key, "false")
                return

            # Beregn ny verdi for antall på banen
            spillere_per_periode_str = self.state_handler.hent_tilstand(
                "spillere_per_periode"
            )
            if not spillere_per_periode_str:
                # Initialiser spillere_per_periode hvis den mangler
                antall_perioder = len(perioder)
                spillere_per_periode = [11] * antall_perioder
                self.state_handler.lagre_tilstand(
                    "spillere_per_periode", json.dumps(spillere_per_periode)
                )
                logger.info(
                    f"Reinitialiserte spillere_per_periode med {antall_perioder} perioder"
                )
            else:
                try:
                    spillere_per_periode = json.loads(spillere_per_periode_str)
                except json.JSONDecodeError:
                    logger.error("Kunne ikke laste spillere_per_periode")
                    return

            try:
                antall_på_banen_nå = int(spillere_per_periode[periode])
                min_spillere_str = self.state_handler.hent_tilstand("min_spillere")
                max_spillere_str = self.state_handler.hent_tilstand("max_spillere")
                min_spillere = int(min_spillere_str) if min_spillere_str else 7
                max_spillere = int(max_spillere_str) if max_spillere_str else 11

                # Sjekk om endringen er gyldig
                if ny_verdi and antall_på_banen_nå >= max_spillere:
                    st.error(f"Kan ikke ha mer enn {max_spillere} spillere på banen")
                    st.session_state[checkbox_key] = False
                    return

                if not ny_verdi and antall_på_banen_nå <= min_spillere:
                    st.error(f"Må ha minst {min_spillere} spillere på banen")
                    st.session_state[checkbox_key] = True
                    return

                # Oppdater antall på banen
                if ny_verdi:
                    antall_på_banen_nå += 1
                else:
                    antall_på_banen_nå = max(0, antall_på_banen_nå - 1)

                # Oppdater spillere_per_periode
                spillere_per_periode[periode] = antall_på_banen_nå
                self.state_handler.lagre_tilstand(
                    "spillere_per_periode", json.dumps(spillere_per_periode)
                )

            except (ValueError, IndexError) as e:
                logger.error(f"Feil ved oppdatering av spillere på banen: {e}")
                st.error("Kunne ikke oppdatere antall spillere på banen")

        except Exception as e:
            logger.error(f"Feil ved checkbox-endring: {e}")
            st.error("Kunne ikke oppdatere bytteplan")
