"""
Forenklet bytteplan-side uten autentisering
"""

import streamlit as st


def vis_bytteplan_side() -> None:
    """Viser en forenklet bytteplan-side."""

    st.title("Bytteplan")
    st.write("Dette er en forenklet versjon av bytteplanleggeren.")

    # Demo-innhold
    st.subheader("Kampinformasjon")
    st.text_input("Motstander", value="Test Lag")
    st.date_input("Kampdato")

    st.subheader("Spillere")
    spillere = [
        "Spiller 1 (Keeper)",
        "Spiller 2 (Forsvar)",
        "Spiller 3 (Forsvar)",
        "Spiller 4 (Midtbane)",
        "Spiller 5 (Midtbane)",
        "Spiller 6 (Angrep)",
        "Spiller 7 (Angrep)",
    ]

    for spiller in spillere:
        st.checkbox(spiller)

    st.button("Lagre bytteplan", disabled=True)

    st.info("Dette er en demoversjon. Full funksjonalitet kommer snart!")
