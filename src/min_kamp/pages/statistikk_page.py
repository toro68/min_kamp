"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Statistikkside for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
import streamlit as st

logger = logging.getLogger(__name__)


def vis_statistikk_side() -> None:
    """Viser statistikk-siden"""
    try:
        # Hent handlers fra session state
        auth_handler = st.session_state.auth_handler
        db_handler = st.session_state.db_handler

        # Sjekk autentisering
        if not auth_handler.sjekk_autentisering():
            return

        st.title("Statistikk")

        # Hent nødvendig data
        kamper = db_handler.kamp_handler.hent_kamper(st.session_state.user_id)
        if not kamper:
            st.info("Ingen kampdata tilgjengelig")
            return

        # Vis kampstatistikk
        st.header("Kampstatistikk")
        antall_kamper = len(kamper)
        st.metric("Antall kamper", antall_kamper)

        # Hent spilletidsstatistikk
        spilletid_data = db_handler.kamp_handler.hent_spilletid_statistikk(
            st.session_state.user_id
        )
        if spilletid_data:
            st.header("Spilletidsstatistikk")

            # Vis gjennomsnittlig spilletid per spiller
            st.subheader("Gjennomsnittlig spilletid")
            for spiller, stats in spilletid_data.items():
                col1, col2 = st.columns(2)
                with col1:
                    st.write(spiller)
                with col2:
                    st.write(f"{stats['snitt_spilletid']:.1f} min")

            # Vis total spilletid per spiller
            st.subheader("Total spilletid")
            for spiller, stats in spilletid_data.items():
                col1, col2 = st.columns(2)
                with col1:
                    st.write(spiller)
                with col2:
                    st.write(f"{stats['total_spilletid']} min")

    except Exception as e:
        logger.error("Feil ved visning av statistikk-side: %s", str(e))
        st.error("En feil oppstod ved visning av statistikk-siden")
