"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import json
import logging
from typing import Any, Dict, List, TypeVar, cast

import streamlit as st

from min_kamp.database.db_handler import DatabaseHandler
from min_kamp.database.handlers.state_handler import StateHandler
from min_kamp.database.handlers.spilletid_handler import SpilletidHandler
from min_kamp.database.handlers.kamp_handler import KampHandler
from min_kamp.pages.components.bytteplan_table import BytteplanTable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BytteplanView:
    """Hovedkomponent for visning av bytteplan"""

    def __init__(self):
        """Initialiserer BytteplanView med nødvendige handlers"""
        self.db_handler = DatabaseHandler()
        self.state_handler = StateHandler(self.db_handler)
        self.spilletid_handler = SpilletidHandler(self.db_handler)
        self.kamp_handler = KampHandler(self.db_handler)
        self.bytteplan_table = BytteplanTable()

    def vis_kampkonfigurasjon(self, konfig: Dict[str, Any]) -> Dict[str, Any]:
        """
        Viser og håndterer kampkonfigurasjon.

        Args:
            konfig: Eksisterende kampkonfigurasjon

        Returns:
            Dict med oppdatert konfigurasjon
        """
        try:
            st.header("Kampkonfigurasjon")
            col1, col2, col3 = st.columns(3)

            with col1:
                if "kamptid" not in st.session_state:
                    st.session_state.kamptid = konfig.get("kamptid", 60)

                ny_kamptid: int = cast(
                    int,
                    st.number_input(
                        "Kamplengde (minutter)",
                        min_value=20,
                        max_value=90,
                        value=st.session_state.kamptid,
                        step=5,
                        key="kamptid_input",
                    ),
                )

            with col2:
                if "periode_lengde" not in st.session_state:
                    st.session_state.periode_lengde = konfig.get("periode_lengde", 5)

                ny_periode_lengde: int = cast(
                    int,
                    st.selectbox(
                        "Periodelengde (minutter)",
                        options=[5, 10, 15, 20],
                        index=[5, 10, 15, 20].index(st.session_state.periode_lengde),
                        key="periode_lengde_input",
                    ),
                )

            # Valider at kamptid er delelig med periode_lengde
            if ny_kamptid % ny_periode_lengde != 0:
                st.error(
                    f"Kamplengde ({ny_kamptid} min) må være delelig med periodelengde ({ny_periode_lengde} min)"
                )
                return konfig

            # Oppdater state bare hvis verdiene har endret seg og er gyldige
            if (
                ny_kamptid != st.session_state.kamptid
                or ny_periode_lengde != st.session_state.periode_lengde
            ):
                ny_antall_perioder = ny_kamptid // ny_periode_lengde
                if ny_antall_perioder < 2:
                    st.error("Kampen må ha minst 2 perioder")
                    return konfig

                st.session_state.kamptid = ny_kamptid
                st.session_state.periode_lengde = ny_periode_lengde
                st.session_state.antall_perioder = ny_antall_perioder

                # Vis oppsummering av endringer
                with col3:
                    st.info(f"Antall perioder: {ny_antall_perioder}")

                st.rerun()

            return {
                "kamptid": ny_kamptid,
                "periode_lengde": ny_periode_lengde,
                "antall_perioder": ny_kamptid // ny_periode_lengde,
            }

        except Exception as e:
            logger.error(f"Feil ved visning av kampkonfigurasjon: {e}")
            st.error("Kunne ikke oppdatere kampkonfigurasjon")
            return konfig

    def oppdater_spilletid_summer(self) -> bool:
        """Oppdaterer spilletid-summer via SpilletidHandler"""
        if not self.spilletid_handler:
            logger.error("SpilletidHandler ikke initialisert")
            return False

        try:
            kamp_id = st.session_state.get("current_kamp_id")
            if not kamp_id:
                logger.warning("Ingen aktiv kamp_id funnet")
                return False

            spiller_id = st.session_state.get("spiller_id")
            if not spiller_id:
                logger.warning("Ingen aktiv spiller_id funnet")
                return False

            minutter = self.spilletid_handler.hent_spilletid(
                int(kamp_id), int(spiller_id)
            )
            if minutter is None:
                logger.error("Kunne ikke hente spilletid")
                return False

            return True

        except Exception as e:
            logger.error(f"Feil ved oppdatering av spilletid-summer: {e}")
            return False

    def vis_bytteplan_view(self) -> None:
        """Hovedkomponent for visning av bytteplan"""
        try:
            # Beregn antall_perioder hvis det mangler
            if "antall_perioder" not in st.session_state:
                kamptid = st.session_state.get("kamptid", 60)
                periode_lengde = st.session_state.get("periode_lengde", 5)
                st.session_state.antall_perioder = kamptid // periode_lengde
                logger.debug(
                    f"Beregnet antall_perioder: {st.session_state.antall_perioder}"
                )

            # Sjekk at alle nødvendige verdier eksisterer
            required_values = [
                "antall_perioder",
                "kamptid",
                "periode_lengde",
                "perioder",
            ]
            missing_values = [
                value for value in required_values if value not in st.session_state
            ]
            if missing_values:
                raise KeyError(f"Mangler påkrevde verdier: {missing_values}")

            if not st.session_state.get("current_kamp_id"):
                st.warning("Ingen aktiv kamp valgt")
                return

            if not self.db_handler:
                st.error("Kunne ikke koble til databasen")
                return

            # Hent konfigurasjon fra state
            konfig = {
                "periode_lengde": st.session_state.get("periode_lengde", 5),
                "antall_perioder": st.session_state.get("antall_perioder", 12),
                "spillere_paa_banen": 7,
            }

            # Vis konfigurasjon øverst
            ny_konfig = self.vis_kampkonfigurasjon(konfig)

            # Oppdater hvis endret
            if ny_konfig != konfig:
                # Lagre konfigurasjon i state
                self.state_handler.lagre_tilstand(
                    "periode_lengde", str(ny_konfig["periode_lengde"])
                )
                self.state_handler.lagre_tilstand(
                    "antall_perioder", str(ny_konfig["antall_perioder"])
                )
                self.state_handler.lagre_tilstand("spillere_paa_banen", "7")

            # Oppdater spilletid
            if not self.oppdater_spilletid_summer():
                st.error("Kunne ikke oppdatere spilletid-summer")
                return

            # Hent kamptropp
            user_id = st.session_state.get("user_id")
            if not user_id:
                st.warning("Ingen bruker er logget inn")
                return

            # Hent kamp
            kamp_id = st.session_state.get("current_kamp_id")
            if not kamp_id:
                st.warning("Ingen aktiv kamp valgt")
                return

            kamp = self.kamp_handler.hent_kamp(int(kamp_id))
            if not kamp:
                st.warning("Kunne ikke finne valgt kamp")
                return

            # Hent spillere fra state
            spillere_str = self.state_handler.hent_tilstand("kamptropp")
            if not spillere_str:
                st.warning("Ingen spillere i kamptroppen")
                return

            try:
                kamptropp = json.loads(spillere_str)
            except json.JSONDecodeError:
                st.error("Kunne ikke laste kamptropp-data")
                return

            # Konverter spilletider til riktig format før du sender det til bytteplan_table
            alle_spilletider_konvertert: Dict[str, List[bool]] = {}

            for spiller_id in kamptropp:
                minutter = self.spilletid_handler.hent_spilletid(
                    int(kamp_id), int(spiller_id)
                )
                if minutter is not None:
                    perioder = [True] * (minutter // st.session_state.periode_lengde)
                    alle_spilletider_konvertert[str(spiller_id)] = perioder

            # Vis bytteplan nederst
            self.bytteplan_table.vis_bytteplan_table(
                kamptropp=kamptropp,
                antall_perioder=ny_konfig["antall_perioder"],
                periode_lengde=ny_konfig["periode_lengde"],
                alle_spilletider=alle_spilletider_konvertert,
            )
        except Exception as e:
            logger.error(f"Kunne ikke vise bytteplan: {str(e)}")
            st.error(
                "Kunne ikke vise bytteplan. Sjekk at alle nødvendige verdier er satt."
            )
