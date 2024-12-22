"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
from typing import Dict, Optional, Tuple

import streamlit as st

from min_kamp.config.constants import POSISJONER
from min_kamp.database.handlers.kamp_handler import KampHandler

logger = logging.getLogger(__name__)


def vis_kamp_side() -> None:
    """Viser kampsiden med informasjon om valgt kamp og spillere."""
    try:
        if not st.session_state.get("current_kamp_id"):
            st.warning("Ingen aktiv kamp valgt")
            return

        # Hent handlers fra session state
        db_handler = st.session_state.db_handler
        kamp_handler = KampHandler(db_handler)
        auth_handler = st.session_state.auth_handler

        # Sjekk autentisering
        if not auth_handler.sjekk_autentisering():
            return

        # Hent kampinfo
        kamp_info: Optional[Tuple[str, str, bool]] = kamp_handler.hent_kamp(
            int(st.session_state.current_kamp_id)
        )
        if kamp_info:
            dato, motstander, hjemmebane = kamp_info
            st.header(f"Kamp mot {motstander}")
            st.subheader(f"Dato: {dato}")
            st.write(f"{'Hjemmekamp' if hjemmebane else 'Bortekamp'}")

        # Hent kamptropp fra state
        kamptropp_str = st.session_state.get("kamptropp")
        if not kamptropp_str:
            st.info("Ingen spillere valgt for denne kampen")
            return

        try:
            kamptropp: Dict[str, Dict] = eval(
                kamptropp_str
            )  # Konverter string til dict
        except Exception as e:
            logger.error(f"Kunne ikke konvertere kamptropp: {e}")
            st.error("Feil ved lasting av kamptropp")
            return

        # Vis statistikk
        total_spillere = len([s for s in kamptropp.values() if s.get("er_med")])
        st.metric("Antall spillere", total_spillere)

        # Gruppér spillere etter posisjon
        spillere_per_posisjon: dict[str, list[str]] = {
            pos: []
            for pos in POSISJONER  # Initialiser tomme lister for hver posisjon
        }

        for spiller_navn, data in kamptropp.items():
            if data.get("er_med"):
                pos = data.get("posisjon", "Ukjent")
                if pos in POSISJONER:
                    spillere_per_posisjon[pos].append(
                        str(spiller_navn)
                    )  # Eksplisitt konvertering til str

        # Vis spillere etter posisjon
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("### Forsvar")
            for spiller in spillere_per_posisjon["Forsvar"]:
                st.write(f"- {spiller}")
        with col2:
            st.write("### Midtbane")
            for spiller in spillere_per_posisjon["Midtbane"]:
                st.write(f"- {spiller}")
        with col3:
            st.write("### Angrep")
            for spiller in spillere_per_posisjon["Angrep"]:
                st.write(f"- {spiller}")

        # Vis detaljert spillerinfo i expanders
        st.write("### Spillerdetaljer")
        for spiller_navn, data in kamptropp.items():
            with st.expander(f"{spiller_navn}", expanded=False):
                st.write(f"Posisjon: {data.get('posisjon', 'Ikke satt')}")
                st.write(f"Er med: {'Ja' if data.get('er_med', False) else 'Nei'}")
                if data.get("startposisjon"):
                    st.write(f"Startposisjon: {data['startposisjon']}")

    except Exception as e:
        logger.error(f"Feil i vis_kamp_side: {str(e)}")
        st.error("En feil oppstod ved lasting av kampdata")
        if st.session_state.get("debug_mode"):
            st.exception(e)


if __name__ == "__main__":
    vis_kamp_side()
