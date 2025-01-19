"""
Test script for å vise bytter fra databasen.
"""

import logging
import os

import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.db_handler import DatabaseHandler
from min_kamp.db.handlers.app_handler import AppHandler

logger = logging.getLogger(__name__)


def hent_kamp_id(app_handler: AppHandler, bruker_id: int) -> int:
    """Henter kamp ID for Sulf/Sandved kampen."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, motstander, hjemmebane, dato
                FROM kamper
                WHERE bruker_id = ?
                ORDER BY dato DESC
            """,
                (bruker_id,),
            )

            kamper = cursor.fetchall()
            st.write("Debug - Tilgjengelige kamper:")
            for kamp in kamper:
                lag_tekst = f"SULF vs {kamp[1]}" if kamp[2] else f"{kamp[1]} vs SULF"
                st.write(f"ID: {kamp[0]}, {lag_tekst} ({kamp[3]})")

            # For nå, returner første kamp
            return kamper[0][0] if kamper else 16

    except Exception as e:
        logger.error("Feil ved henting av kamp ID: %s", e)
        return 16  # Default hvis noe går galt


def hent_bytter_for_periode(app_handler: AppHandler, kamp_id: int, periode_id: int):
    """Henter bytter for en periode."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent alle spillere i kamptroppen med deres status i denne og forrige periode
            cursor.execute(
                """
                WITH SisteStatus AS (
                    SELECT
                        spiller_id,
                        er_paa,
                        periode,
                        sist_oppdatert,
                        ROW_NUMBER() OVER (
                            PARTITION BY spiller_id, periode
                            ORDER BY sist_oppdatert DESC
                        ) as rn
                    FROM bytteplan
                    WHERE kamp_id = ?
                    AND periode IN (?, ? - 1)
                )
                SELECT
                    s.id,
                    s.navn,
                    s.posisjon,
                    COALESCE(ss.er_paa, 0) as er_paa,
                    ss.periode,
                    ss.sist_oppdatert
                FROM spillere s
                JOIN kamptropp kt ON s.id = kt.spiller_id AND kt.kamp_id = ?
                LEFT JOIN SisteStatus ss ON s.id = ss.spiller_id AND ss.rn = 1
                WHERE kt.er_med = 1
                ORDER BY ss.periode, ss.sist_oppdatert
            """,
                (kamp_id, periode_id, periode_id, kamp_id),
            )

            return cursor.fetchall()

    except Exception as e:
        logger.error("Feil ved henting av bytter: %s", e)
        return []


def hent_perioder_med_bytter(app_handler: AppHandler, kamp_id: int) -> list:
    """Henter alle perioder som har bytter for en kamp."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT periode
                FROM bytteplan
                WHERE kamp_id = ?
                ORDER BY periode
            """,
                (kamp_id,),
            )
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error("Feil ved henting av perioder: %s", e)
        return []


def vis_bytter():
    """Hovedfunksjon for å vise bytter."""
    try:
        st.title("Test Byttevisning")

        # Initialiser database og app handler
        try:
            db_path = os.path.join("database", "kampdata.db")
            st.write(f"Debug - Database sti: {db_path}")

            if not os.path.exists(db_path):
                st.error(f"Finner ikke databasefilen: {db_path}")
                return

            db_handler = DatabaseHandler(database_path=db_path)
            st.write("Debug - DatabaseHandler opprettet")

            app_handler = AppHandler(db_handler)
            st.write("Debug - AppHandler opprettet")

        except Exception as e:
            st.error(f"Feil ved initialisering av handlers: {str(e)}")
            logger.error("Handler initialisering feilet: %s", e)
            return

        # Sjekk bruker_id i query params
        bruker_id_str = st.query_params.get("bruker_id", "1")  # Default til bruker 1
        st.write(f"Debug - Bruker ID fra query params: {bruker_id_str}")

        try:
            bruker_id = int(bruker_id_str)
            st.write(f"Debug - Konvertert bruker_id til int: {bruker_id}")

            # Sett bruker_id i query params som int
            st.query_params["bruker_id"] = str(bruker_id)

        except (ValueError, TypeError) as e:
            st.error(f"Ugyldig bruker ID format: {bruker_id_str}")
            logger.error("Konvertering av bruker_id feilet: %s", e)
            return

        try:
            if not check_auth(app_handler.auth_handler):
                st.error("Autentisering feilet")
                return
            st.write("Debug - Autentisering OK")
        except Exception as e:
            st.error(f"Feil ved autentisering: {str(e)}")
            logger.error("Autentisering feilet: %s", e)
            return

        # Hent kamp ID for Sulf/Sandved kampen
        kamp_id = hent_kamp_id(app_handler, bruker_id)
        st.write(f"Debug - Query params: {st.query_params}")

        # Hent perioder med bytter
        perioder = hent_perioder_med_bytter(app_handler, kamp_id)
        if perioder:
            st.write("Debug - Perioder med bytter:", perioder)

        # La brukeren velge periode
        periode = st.number_input("Velg periode", min_value=0, max_value=15, value=0)

        st.subheader(f"Bytter i periode {periode + 1}")

        # Debug info
        st.write(f"Debug - Kamp ID: {kamp_id}, Periode: {periode}")

        # Hent og vis bytter
        bytter = hent_bytter_for_periode(app_handler, kamp_id, periode)

        # Debug info
        st.write(f"Debug - Antall bytter funnet: {len(bytter)}")
        if bytter:
            st.write("Debug - Første bytte:", bytter[0])

        if not bytter:
            st.info("Ingen bytter funnet i denne perioden")
            return

        # Organiser data per spiller
        spillere = {}
        for bytte in bytter:
            spiller_id = bytte[0]
            navn = bytte[1]
            posisjon = bytte[2]
            er_paa = bytte[3]
            periode_nr = bytte[4]

            if navn not in spillere:
                spillere[navn] = {"posisjon": posisjon, "perioder": {}}
            spillere[navn]["perioder"][periode_nr] = er_paa

        # Finn bytter mellom periodene
        bytter_inn = []
        bytter_ut = []

        for navn, spiller in spillere.items():
            forrige = spiller["perioder"].get(periode - 1, False)
            denne = spiller["perioder"].get(periode, False)

            if not forrige and denne:
                bytter_inn.append(navn)
            elif forrige and not denne:
                bytter_ut.append(navn)

        # Vis bytter i en pen tabell
        data = []
        if bytter_inn or bytter_ut:
            bytter_tekst = []
            if bytter_inn:
                bytter_tekst.append("INN:")
                bytter_tekst.extend([f"↑ {navn}" for navn in sorted(bytter_inn)])
            if bytter_ut:
                if bytter_inn:
                    bytter_tekst.append("")
                bytter_tekst.append("UT:")
                bytter_tekst.extend([f"↓ {navn}" for navn in sorted(bytter_ut)])

            data.append({"Bytter": "\n".join(bytter_tekst)})

            st.dataframe(
                data,
                column_config={
                    "Bytter": st.column_config.TextColumn(
                        "Bytter i perioden", width="large"
                    )
                },
                hide_index=True,
            )
        else:
            st.info("Ingen bytter i denne perioden")

    except Exception as e:
        logger.error("Feil i byttevisning: %s", e)
        st.error(f"En feil oppstod ved visning av bytter: {str(e)}")


if __name__ == "__main__":
    vis_bytter()
