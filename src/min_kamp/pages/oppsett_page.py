"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
import io
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd
import streamlit as st


logger = logging.getLogger(__name__)

# Gyldige posisjoner
POSISJONER = ["Keeper", "Forsvar", "Midtbane", "Angrep"]


def valider_excel_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validerer data fra Excel-fil."""
    feilmeldinger = []

    # Sjekk at vi har minst én kolonne
    if len(df.columns) < 1:
        feilmeldinger.append("Excel-filen må ha minst én kolonne med navn")
        return False, feilmeldinger

    # Sjekk at første kolonne har data
    if df[df.columns[0]].isnull().all():
        feilmeldinger.append("Navnekolonnen kan ikke være tom")
        return False, feilmeldinger

    return len(feilmeldinger) == 0, feilmeldinger


def importer_spillertropp_fra_excel(
    excel_fil: io.BytesIO,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Importerer spillertropp fra Excel-fil

    Args:
        excel_fil: Excel-filen som skal importeres

    Returns:
        Dictionary med spillere der nøkkelen er spiller-ID og verdien er en dictionary med følgende nøkler:
        - navn: Navnet til spilleren
        - posisjon: Posisjonen til spilleren
        - er_aktiv: Om spilleren er aktiv
    """
    try:
        logger.debug("Starter import av Excel-fil")
        df = pd.read_excel(excel_fil)
        logger.debug("DEBUG: Full DataFrame:")
        logger.debug(df)

        # Standardiser kolonnenavn
        df.columns = [str(col).lower().strip() for col in df.columns]
        logger.debug("Leste Excel-fil med kolonner: %s", list(df.columns))
        logger.debug("Standardiserte kolonnenavn: %s", list(df.columns))

        # Finn navnekolonne
        navnekolonne = None
        for kolonne in df.columns:
            if "navn" in kolonne:
                navnekolonne = kolonne
                break

        if not navnekolonne:
            raise ValueError("Fant ikke navnekolonne i Excel-fil")

        logger.debug("DEBUG: Bruker navnekolonne: '%s'", navnekolonne)

        # Opprett spillertropp
        spillertropp = {}
        for index, row in df.iterrows():
            logger.debug("\nDEBUG: Rad %d rådata:", index)
            for kolonne in df.columns:
                logger.debug("  %s: '%s'", kolonne, row[kolonne])

            navn = row[navnekolonne]
            if pd.isna(navn):
                continue

            posisjon = row[st.session_state.posisjonskolonne]
            if pd.isna(posisjon):
                posisjon = "Midtbane"

            logger.debug(
                "DEBUG: Leste posisjon '%s' for %s fra kolonne '%s'",
                posisjon,
                navn,
                st.session_state.posisjonskolonne,
            )
            logger.debug("DEBUG: Validerer posisjon '%s' for %s", posisjon, navn)

            spiller_id = f"import_{index}"
            spillertropp[spiller_id] = {
                "navn": navn,
                "posisjon": posisjon,
                "er_aktiv": True,
            }
            logger.debug(
                "La til spiller: %s (ID: %s, Posisjon: %s)", navn, spiller_id, posisjon
            )

        logger.info("Importerte %d spillere fra Excel", len(spillertropp))
        logger.debug("\nDEBUG: Komplett spillertropp:")
        for spiller_id, spiller in spillertropp.items():
            logger.debug("  %s: %s", spiller_id, spiller)

        # Importer spillere til databasen
        spiller_handler = st.session_state.app_handler.spiller_handler

        # Hent eksisterende spillere for debugging
        with spiller_handler.db_handler.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, navn, aktiv, posisjon FROM spillere")
            eksisterende = cursor.fetchall()
            logger.debug("\nDEBUG: Eksisterende spillere i database før import:")
            for spiller in eksisterende:
                logger.debug(
                    "  ID=%s, navn='%s', aktiv=%s, posisjon='%s'",
                    spiller[0],
                    spiller[1],
                    spiller[2],
                    spiller[3],
                )

        logger.debug("\nDEBUG: Importerer spillere til database")
        spillere = [
            {"navn": spiller["navn"], "posisjon": spiller["posisjon"]}
            for spiller in spillertropp.values()
        ]
        resultater = spiller_handler.importer_spillere(spillere)
        logger.debug("DEBUG: Import resultater: %s", resultater)

        # Hent spillere etter import for debugging
        with spiller_handler.db_handler.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, navn, aktiv, posisjon FROM spillere")
            etter_import = cursor.fetchall()
            logger.debug("\nDEBUG: Eksisterende spillere i database etter import:")
            for spiller in etter_import:
                logger.debug(
                    "  ID=%s, navn='%s', aktiv=%s, posisjon='%s'",
                    spiller[0],
                    spiller[1],
                    spiller[2],
                    spiller[3],
                )

        return spillertropp

    except Exception as e:
        logger.error("Feil ved import av Excel-fil: %s", str(e), exc_info=True)
        st.error(f"Kunne ikke lese Excel-fil: {str(e)}")
        return None


def render_oppsett_page() -> None:
    """Rendrer oppsett-siden."""
    st.title("Oppsett")

    # Last opp Excel-fil
    uploaded_file = st.file_uploader("Last opp Excel-fil med spillere", type=["xlsx"])

    if uploaded_file is not None:
        try:
            logger.debug(f"Fil lastet opp: {uploaded_file.name}")

            # Les Excel-fil først for å få kolonner
            df = pd.read_excel(uploaded_file)

            # La bruker velge posisjonskolonne
            st.selectbox(
                "Velg kolonne for posisjon:",
                options=df.columns,
                index=2 if len(df.columns) > 2 else 0,
                key="posisjonskolonne",
            )

            if st.button("Bekreft kolonnevalg"):
                # Reset fil-posisjon før vi sender den videre
                uploaded_file.seek(0)
                importert_tropp = importer_spillertropp_fra_excel(uploaded_file)

                if importert_tropp:
                    st.success(f"Importerte {len(importert_tropp)} spillere fra Excel")

                    # Vis spillere i kolonner
                    st.subheader("Velg posisjoner for spillere")
                    cols = st.columns(3)
                    col_idx = 0

                    # Initialiser session state for valgte posisjoner hvis ikke allerede gjort
                    if "valgte_posisjoner" not in st.session_state:
                        st.session_state.valgte_posisjoner = {}

                    # Vis spillere i kolonner med posisjon-dropdown
                    for spiller_id, spiller_data in importert_tropp.items():
                        with cols[col_idx]:
                            # Bruk eksisterende posisjon som default hvis den er gyldig
                            default_pos = (
                                spiller_data["posisjon"]
                                if spiller_data["posisjon"] in POSISJONER
                                else None
                            )

                            # Vis dropdown for posisjon
                            valgt_posisjon = st.selectbox(
                                spiller_data["navn"],
                                options=POSISJONER,
                                index=POSISJONER.index(default_pos)
                                if default_pos
                                else 0,
                                key=f"pos_{spiller_id}",
                            )

                            # Lagre valgt posisjon
                            st.session_state.valgte_posisjoner[spiller_id] = (
                                valgt_posisjon
                            )

                        # Bytt kolonne for neste spiller
                        col_idx = (col_idx + 1) % 3

                    if st.button("Importer spillere"):
                        logger.debug("Starter import av spillere til database")
                        try:
                            # Konverter spillere til format for importer_spillere
                            spillere_for_import = []
                            for spiller_id, spiller_data in importert_tropp.items():
                                navn = spiller_data["navn"]
                                valgt_posisjon = st.session_state.valgte_posisjoner.get(
                                    spiller_id
                                )
                                if not valgt_posisjon:
                                    logger.warning(f"Ingen posisjon valgt for {navn}")
                                    continue

                                logger.debug(
                                    f"Bruker valgt posisjon for {navn}: {valgt_posisjon}"
                                )
                                spillere_for_import.append(
                                    {"navn": navn, "posisjon": valgt_posisjon}
                                )

                            # Bruk importer_spillere metoden
                            if not spillere_for_import:
                                st.error(
                                    "Ingen spillere å importere - velg posisjoner først"
                                )
                                return

                            resultater = st.session_state.app_handler.spiller_handler.importer_spillere(
                                spillere_for_import
                            )

                            antall_importert = sum(1 for r in resultater if r)
                            feilede_spillere = [
                                s["navn"]
                                for s, r in zip(spillere_for_import, resultater)
                                if not r
                            ]

                            # Vis resultater
                            if antall_importert > 0:
                                st.success(
                                    f"Importerte {antall_importert} spillere til spillertroppen"
                                )
                                logger.info(
                                    f"Vellykket import av {antall_importert} spillere"
                                )

                                # Vis link til kamptropp-siden
                                st.info(
                                    "For å legge til spillerne i en kamptropp, gå til Kamptropp-siden"
                                )
                                if st.button("Gå til Kamptropp"):
                                    st.session_state.current_page = "kamptropp"
                                    st.rerun()

                            if feilede_spillere:
                                feilmelding = f"Kunne ikke importere følgende spillere: {', '.join(feilede_spillere)}"
                                st.warning(feilmelding)
                                logger.warning(feilmelding)

                            if antall_importert == 0:
                                st.error("Ingen spillere ble importert")

                        except Exception as e:
                            logger.error(
                                f"Feil ved lagring av spillere: {str(e)}", exc_info=True
                            )
                            st.error(f"Kunne ikke lagre spillere: {str(e)}")

        except Exception as e:
            logger.error(f"Feil ved import av spillertropp: {str(e)}", exc_info=True)
            st.error(f"Feil ved import av spillertropp: {str(e)}")
