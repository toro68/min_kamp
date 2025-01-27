# bytteplan_page.py
"""
Bytteplan-side for kampplanleggeren.
"""

import logging
from typing import Dict, List, Tuple, cast

import streamlit as st
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.db_handler import DatabaseHandler
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


def get_kamp_id() -> int:
    """Henter kamp ID fra query parameters."""
    kamp_id_str = st.query_params.get("kamp_id")
    if not kamp_id_str:
        error_msg = "Ingen kamp-ID funnet"
        logger.error(error_msg)
        raise ValueError(error_msg)
    try:
        return int(kamp_id_str)
    except (ValueError, TypeError):
        error_msg = "Ugyldig kamp-ID"
        logger.error(error_msg)
        raise ValueError(error_msg)


def _hent_kampinnstillinger(
    app_handler: AppHandler, bruker_id: int, kamp_id: int
) -> Tuple[int, int, int]:
    """Henter kampinnstillinger fra databasen."""
    try:
        db_handler = cast(DatabaseHandler, app_handler._database_handler)
        query = """
        SELECT nokkel, verdi, kamp_id
        FROM app_innstillinger
        WHERE (bruker_id = ? OR kamp_id = ?)
        AND nokkel IN (
            'kamplengde',
            'antall_perioder',
            'antall_paa_banen'
        )
        ORDER BY
            CASE
                WHEN kamp_id = ? THEN 1
                WHEN bruker_id = ? THEN 2
                ELSE 3
            END,
            sist_oppdatert DESC
        """
        innstillinger = db_handler.execute_query(
            query, (bruker_id, kamp_id, kamp_id, bruker_id)
        )

        # Detaljert logging av alle innhentede innstillinger
        logger.debug(
            "Hentet innstillinger for kamp %d, bruker %d: %s",
            kamp_id,
            bruker_id,
            innstillinger,
        )

        # Definer standard verdier
        kamplengde = 70  # Standard 70 minutter
        antall_perioder = 7  # Standard 7 perioder (10 min hver)
        antall_paa_banen = 7  # Standard 7 spillere på banen

        # Lag en dictionary for å holde styr på innstillinger
        innstillinger_dict = {}

        # Behandle innstillinger med prioritet
        for row in innstillinger:
            nokkel = row["nokkel"]
            verdi = row["verdi"]

            # Kun oppdater hvis nøkkelen ikke allerede er satt
            if nokkel not in innstillinger_dict:
                innstillinger_dict[nokkel] = verdi
                logger.debug("Valgt innstilling: nokkel=%s, verdi=%s", nokkel, verdi)

        # Oppdater verdier fra databasen
        if "kamplengde" in innstillinger_dict:
            kamplengde = int(innstillinger_dict["kamplengde"])
        if "antall_perioder" in innstillinger_dict:
            antall_perioder = int(innstillinger_dict["antall_perioder"])
        if "antall_paa_banen" in innstillinger_dict:
            antall_paa_banen = int(innstillinger_dict["antall_paa_banen"])

        logger.debug(
            "Endelige innstillinger: kamplengde=%d, perioder=%d, spillere=%d",
            kamplengde,
            antall_perioder,
            antall_paa_banen,
        )

        logger.info(
            "Kampinnstillinger for kamp %d: lengde=%d, perioder=%d, spillere=%d",
            kamp_id,
            kamplengde,
            antall_perioder,
            antall_paa_banen,
        )
        return kamplengde, antall_perioder, antall_paa_banen
    except Exception as e:
        logger.error("Feil ved henting av kampinnstillinger: %s", str(e))
        st.error(f"Kunne ikke hente kampinnstillinger: {str(e)}")
        return 70, 7, 7


def _lagre_kampinnstillinger(
    app_handler: AppHandler,
    bruker_id: int,
    kamp_id: int,
    kamplengde: int,
    antall_perioder: int,
    antall_paa_banen: int,
) -> None:
    """Lagrer kampinnstillinger i databasen."""
    try:
        db_handler = cast(DatabaseHandler, app_handler._database_handler)

        # Detaljert logging med stack trace
        import traceback

        logger.debug(
            "Starter lagring av kampinnstillinger: "
            "kamp_id=%d, bruker_id=%d, kamplengde=%d, "
            "antall_perioder=%d, antall_paa_banen=%d\n%s",
            kamp_id,
            bruker_id,
            kamplengde,
            antall_perioder,
            antall_paa_banen,
            traceback.format_stack(),
        )

        # Slett eventuelle eksisterende innstillinger for denne kampen
        delete_query = """
        DELETE FROM app_innstillinger
        WHERE kamp_id = ? AND nokkel IN (
            'kamplengde', 'antall_perioder', 'antall_paa_banen'
        )
        """
        db_handler.execute_update(delete_query, (kamp_id,))

        # Sett inn nye innstillinger
        query = """
        INSERT INTO app_innstillinger
        (kamp_id, bruker_id, nokkel, verdi)
        VALUES
            (?, ?, 'kamplengde', ?),
            (?, ?, 'antall_perioder', ?),
            (?, ?, 'antall_paa_banen', ?)
        """
        db_handler.execute_update(
            query,
            (
                kamp_id,
                bruker_id,
                str(kamplengde),
                kamp_id,
                bruker_id,
                str(antall_perioder),
                kamp_id,
                bruker_id,
                str(antall_paa_banen),
            ),
        )
        logger.info(
            "Lagret kampinnstillinger for kamp %d: lengde=%d, perioder=%d, spillere=%d",
            kamp_id,
            kamplengde,
            antall_perioder,
            antall_paa_banen,
        )
    except Exception as e:
        logger.error("Feil ved lagring av kampinnstillinger: %s", str(e))
        st.error(f"Kunne ikke lagre kampinnstillinger: {str(e)}")


def _hent_bytteplan(app_handler: AppHandler, kamp_id: int) -> List[Dict]:
    """Henter bytteplan fra databasen."""
    try:
        db_handler = cast(DatabaseHandler, app_handler._database_handler)
        query = """
        SELECT
            s.navn,
            s.id as spiller_id,
            s.posisjon,
            b.periode,
            b.er_paa
        FROM spillere s
        JOIN kamptropp kt ON kt.spiller_id = s.id
        LEFT JOIN bytteplan b ON b.spiller_id = s.id AND b.kamp_id = ?
        WHERE kt.kamp_id = ? AND kt.er_med = 1
        ORDER BY
            CASE s.posisjon
                WHEN 'Keeper' THEN 1
                WHEN 'Forsvar' THEN 2
                WHEN 'Midtbane' THEN 3
                WHEN 'Angrep' THEN 4
                ELSE 5
            END,
            s.navn
        """
        bytteplan_data = db_handler.execute_query(query, (kamp_id, kamp_id))
        logger.debug("Bytteplan data for kamp %d: %s", kamp_id, bytteplan_data)
        return bytteplan_data
    except Exception as e:
        logger.error("Feil ved henting av bytteplan: %s", str(e))
        st.error(f"Kunne ikke hente bytteplan: {str(e)}")
        return []


def _oppdater_bytteplan(
    app_handler: AppHandler, kamp_id: int, spiller_id: int, periode: int, er_paa: bool
) -> None:
    """Oppdaterer bytteplan i databasen."""
    try:
        db_handler = cast(DatabaseHandler, app_handler._database_handler)

        # Først slett eventuelle eksisterende rader for denne kombinasjonen
        delete_query = """
        DELETE FROM bytteplan
        WHERE kamp_id = ? AND spiller_id = ? AND periode = ?
        """
        db_handler.execute_update(delete_query, (kamp_id, spiller_id, periode))

        # Så sett inn ny rad
        insert_query = """
        INSERT INTO bytteplan
        (kamp_id, spiller_id, periode, er_paa)
        VALUES (?, ?, ?, ?)
        """
        db_handler.execute_update(insert_query, (kamp_id, spiller_id, periode, er_paa))

        logger.debug(
            "Oppdatert bytteplan: spiller=%d, periode=%d, er_på=%d",
            spiller_id,
            periode,
            er_paa,
        )

    except Exception as e:
        logger.error("Feil ved oppdatering av bytteplan: %s", str(e))
        st.error(f"Kunne ikke oppdatere bytteplan: {str(e)}")


def _vis_bytteplan_oppsummering(
    spillere: Dict, perioder: List[int], periode_lengde: float
) -> None:
    """Viser en oppsummering av bytteplanen."""
    st.subheader("Bytteplan")

    # Lag en oversikt over hver periode
    data = []
    for p_idx, periode in enumerate(perioder):
        # Finn hvem som er på banen og på benken i denne perioden
        paa_banen = {pos: [] for pos in ["Keeper", "Forsvar", "Midtbane", "Angrep"]}
        paa_benken = []

        for navn, spiller in spillere.items():
            if spiller["perioder"].get(p_idx, False):
                paa_banen[spiller["posisjon"]].append(navn)
            else:
                paa_benken.append(navn)

        # Finn bytter hvis ikke første periode
        bytter_inn = []
        bytter_ut = []
        if p_idx > 0:
            for navn, spiller in spillere.items():
                forrige = spiller["perioder"].get(p_idx - 1, False)
                denne = spiller["perioder"].get(p_idx, False)
                if not forrige and denne:
                    bytter_inn.append(navn)
                elif forrige and not denne:
                    bytter_ut.append(navn)

        # Formater spillere på banen
        paa_banen_tekst = []
        for pos in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
            if paa_banen[pos]:
                paa_banen_tekst.append(f"{pos}:")
                for spiller in sorted(paa_banen[pos]):
                    paa_banen_tekst.append(spiller)

        # Formater bytter
        bytter_tekst = "-"
        if bytter_inn or bytter_ut:
            bytter_linjer = []
            if bytter_inn:
                bytter_linjer.append("INN:")
                bytter_linjer.extend(sorted(bytter_inn))
            if bytter_ut:
                if bytter_inn:
                    bytter_linjer.append("")
                bytter_linjer.append("UT:")
                bytter_linjer.extend(sorted(bytter_ut))
            bytter_tekst = "\n".join(bytter_linjer)

        # Formater benken
        benk_tekst = "\n".join(sorted(paa_benken))

        # Formater data for denne perioden
        rad = {
            "Periode": f"Periode {p_idx+1}\n({periode} min)",
            "På banen": "\n".join(paa_banen_tekst),
            "Bytter": bytter_tekst,
            "På benken": benk_tekst,
        }
        data.append(rad)

    # Vis dataframe med tilpasset høyde
    st.dataframe(
        data,
        column_config={
            "Periode": st.column_config.TextColumn("Periode", width="small"),
            "På banen": st.column_config.TextColumn("På banen", width="large"),
            "Bytter": st.column_config.TextColumn("Bytter", width="medium"),
            "På benken": st.column_config.TextColumn("På benken", width="medium"),
        },
        hide_index=True,
        height=800,
    )


def _vis_bytteplan_statistikk(
    spillere: Dict, perioder: List[int], periode_lengde: float
) -> None:
    """Viser statistikk for bytteplanen."""
    st.subheader("Spilletid og byttemønster")

    # Beregn statistikk per spiller
    statistikk = {}
    for navn, data in spillere.items():
        # Bare tell perioder opp til antall_perioder og ta siste status per periode
        gyldige_perioder = {
            p: status for p, status in data["perioder"].items() if p < len(perioder)
        }
        logger.debug(
            "Gyldige perioder for %s: %s (av totalt %d perioder)",
            navn,
            gyldige_perioder,
            len(perioder),
        )

        perioder_paa = sum(1 for p in gyldige_perioder.values() if p)
        logger.debug(
            "Perioder på banen for %s: %d av %d mulige",
            navn,
            perioder_paa,
            len(perioder),
        )

        spilletid = int(perioder_paa * periode_lengde)
        logger.debug(
            "Beregnet spilletid for %s: %d perioder * %.2f min = %d min",
            navn,
            perioder_paa,
            periode_lengde,
            spilletid,
        )

        bytter = 0
        forrige_status = None
        for p_idx in range(len(perioder)):
            status = gyldige_perioder.get(p_idx, False)
            if forrige_status is not None and status != forrige_status:
                bytter += 1
            forrige_status = status

        statistikk[navn] = {
            "posisjon": data["posisjon"],
            "spilletid": spilletid,
            "perioder_paa": perioder_paa,
            "bytter": bytter,
        }

    # Vis statistikk gruppert etter posisjon
    for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
        spillere_i_posisjon = {
            navn: data
            for navn, data in statistikk.items()
            if data["posisjon"] == posisjon
        }
        if spillere_i_posisjon:
            st.markdown(f"**{posisjon}**")

            # Lag en tabell med statistikk
            data = []
            for navn, stats in spillere_i_posisjon.items():
                data.append(
                    {
                        "Navn": navn,
                        "Spilletid": f"{stats['spilletid']} min",
                        "Perioder": stats["perioder_paa"],
                        "Bytter": stats["bytter"],
                    }
                )

            if data:
                st.dataframe(
                    data,
                    column_config={
                        "Navn": st.column_config.TextColumn("Spiller", width="medium"),
                        "Spilletid": st.column_config.TextColumn(
                            "Spilletid", width="small"
                        ),
                        "Perioder": st.column_config.NumberColumn(
                            "Perioder på banen", width="small"
                        ),
                        "Bytter": st.column_config.NumberColumn(
                            "Antall bytter", width="small"
                        ),
                    },
                    hide_index=True,
                )


def _vis_bytteplan_html(
    spillere: Dict, perioder: List[int], periode_lengde: float
) -> None:
    """Viser bytteplan i kompakt tabellformat."""

    # Lag data for kompakt visning
    data = []

    # For hver periode
    for p_idx, periode in enumerate(perioder):
        # Finn hvem som er på banen og på benken
        paa_banen = {pos: [] for pos in ["Keeper", "Forsvar", "Midtbane", "Angrep"]}
        paa_benken = []

        for navn, spiller in spillere.items():
            if spiller["perioder"].get(p_idx, False):
                paa_banen[spiller["posisjon"]].append(navn)
            else:
                paa_benken.append(navn)

        # Finn bytter hvis ikke første periode
        bytter_inn = []
        bytter_ut = []
        if p_idx > 0:
            for navn, spiller in spillere.items():
                forrige = spiller["perioder"].get(p_idx - 1, False)
                denne = spiller["perioder"].get(p_idx, False)
                if not forrige and denne:
                    bytter_inn.append(navn)
                elif forrige and not denne:
                    bytter_ut.append(navn)

        # Formater spillere på banen kompakt
        paa_banen_tekst = []
        for pos in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
            if paa_banen[pos]:
                spillere_tekst = ", ".join(sorted(paa_banen[pos]))
                paa_banen_tekst.append(f"{pos}: {spillere_tekst}")

        # Formater bytter kompakt
        bytter_tekst = "-"
        if bytter_inn or bytter_ut:
            bytter_deler = []
            if bytter_inn:
                bytter_deler.append(f"INN: {', '.join(sorted(bytter_inn))}")
            if bytter_ut:
                bytter_deler.append(f"UT: {', '.join(sorted(bytter_ut))}")
            bytter_tekst = " | ".join(bytter_deler)

        # Formater benken kompakt
        benk_tekst = ", ".join(sorted(paa_benken))

        # Legg til rad i tabell
        data.append(
            {
                "Periode": f"P{p_idx+1} ({periode} min)",
                "På banen": " | ".join(paa_banen_tekst),
                "Bytter": bytter_tekst,
                "På benken": benk_tekst,
            }
        )

    # Vis tabell med kompakt formatering
    st.table(data)


def vis_bytteplan_side(app_handler: AppHandler) -> None:
    """Viser bytteplan-siden.

    Args:
        app_handler: AppHandler instans
    """
    try:
        auth_handler = app_handler.auth_handler
        if not check_auth(auth_handler):
            return

        st.title("Bytteplan")

        # Hent bruker ID og kamp ID
        try:
            bruker_id = get_bruker_id()
            kamp_id = get_kamp_id()
        except ValueError as e:
            st.error(str(e))
            if st.button("Gå til oppsett for å velge kamp"):
                st.query_params["page"] = "oppsett"
                st.rerun()
            return

        # Hent kampinnstillinger
        kamplengde, antall_perioder, antall_paa_banen = _hent_kampinnstillinger(
            app_handler, bruker_id, kamp_id
        )

        # DEBUGGING: Legg til detaljert logging
        logger.warning(
            "DEBUG: Opprinnelige innstillinger - "
            "kamplengde=%d, antall_perioder=%d, antall_paa_banen=%d",
            kamplengde,
            antall_perioder,
            antall_paa_banen,
        )

        # Kampinnstillinger
        st.subheader("Kampinnstillinger")

        col1, col2, col3 = st.columns(3)
        with col1:
            ny_kamplengde = st.number_input(
                "Kamplengde (minutter)", min_value=1, value=kamplengde
            )
        with col2:
            nytt_antall_perioder = st.number_input(
                "Antall perioder", min_value=1, value=antall_perioder
            )
        with col3:
            nytt_antall_paa_banen = st.number_input(
                "Antall spillere på banen", min_value=1, value=antall_paa_banen
            )

        # DEBUGGING: Legg til detaljert logging
        logger.warning(
            "DEBUG: Nye innstillinger før lagring - "
            "ny_kamplengde=%d, nytt_antall_perioder=%d, nytt_antall_paa_banen=%d",
            ny_kamplengde,
            nytt_antall_perioder,
            nytt_antall_paa_banen,
        )

        if st.button("Lagre innstillinger"):
            # DEBUGGING: Legg til detaljert logging
            logger.warning(
                "DEBUG: Lagrer innstillinger - "
                "kamp_id=%d, bruker_id=%d, ny_kamplengde=%d, "
                "nytt_antall_perioder=%d, nytt_antall_paa_banen=%d",
                kamp_id,
                bruker_id,
                ny_kamplengde,
                nytt_antall_perioder,
                nytt_antall_paa_banen,
            )

            _lagre_kampinnstillinger(
                app_handler,
                bruker_id,
                kamp_id,
                ny_kamplengde,
                nytt_antall_perioder,
                nytt_antall_paa_banen,
            )
            st.success("Innstillinger lagret")
            st.rerun()

        # Beregn periodetidspunkter
        periode_lengde = ny_kamplengde / nytt_antall_perioder
        logger.debug(
            "Beregner periodelengde: kamplengde=%d, antall_perioder=%d, periode_lengde=%f",
            ny_kamplengde,
            nytt_antall_perioder,
            periode_lengde,
        )
        perioder = [int(i * periode_lengde) for i in range(nytt_antall_perioder)]

        # Hent bytteplan
        bytteplan_data = _hent_bytteplan(app_handler, kamp_id)

        # Organiser data for visning
        spillere = {}
        posisjoner = {"Keeper": [], "Forsvar": [], "Midtbane": [], "Angrep": []}

        for rad in bytteplan_data:
            if rad["navn"] not in spillere:
                spillere[rad["navn"]] = {
                    "id": rad["spiller_id"],
                    "posisjon": rad["posisjon"],
                    "perioder": {p: False for p in range(nytt_antall_perioder)},
                }
                posisjoner[rad["posisjon"]].append(rad["navn"])
            if rad["periode"] is not None:
                spillere[rad["navn"]]["perioder"][rad["periode"]] = rad["er_paa"]

        logger.debug("Organiserte spillerdata: %s", spillere)

        if not spillere:
            st.warning(
                "Ingen spillere er lagt til i kamptroppen. "
                "Gå til Kamptropp-siden for å legge til spillere."
            )
            return

        # Beregn gjennomsnittlig spilletid
        omgang_lengde = int(ny_kamplengde / 2)
        antall_i_tropp = len(spillere)
        total_spilletid = ny_kamplengde * nytt_antall_paa_banen
        snitt_spilletid = int(total_spilletid / antall_i_tropp)

        st.info(
            "⚽ Alle spillere i kamptroppen bør minimum "
            f"spille én omgang ({omgang_lengde} min) "
            "for å sikre god spillerutvikling.\n\n"
            f"💡 {antall_i_tropp} spillere i tropp, "
            f"{nytt_antall_paa_banen} på banen = "
            f"snitt {snitt_spilletid} min spilletid.\n\n"
            "🌟 Fokus på utvikling og mestring - "
            "slik bygger vi et sterkt lag."
        )

        # Vis checkbox-basert bytteplan først
        st.subheader("Rediger bytteplan")

        # Vis kolonneoverskrifter
        cols = st.columns([2] + [1] * nytt_antall_perioder)
        cols[0].write("Navn")
        for p_idx, periode in enumerate(perioder):
            cols[p_idx + 1].write(str(periode))

        # Vis tabellen med checkboxer, gruppert etter posisjon
        for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
            if posisjoner[posisjon]:
                st.markdown(f"**{posisjon}**")
                for navn in sorted(posisjoner[posisjon]):
                    # Beregn spilletid
                    perioder_paa = spillere[navn]["perioder"].values()
                    antall_perioder_paa = sum(1 for p in perioder_paa if p)
                    spilletid = int(antall_perioder_paa * periode_lengde)

                    cols = st.columns([2] + [1] * nytt_antall_perioder)
                    spiller_info = f"{navn} ({spilletid} min)"
                    cols[0].write(spiller_info)
                    for p_idx, periode in enumerate(perioder):
                        ny_verdi = cols[p_idx + 1].checkbox(
                            (f"Spiller {navn} på banen " f"i periode {periode}"),
                            value=spillere[navn]["perioder"].get(p_idx, False),
                            key=f"{navn}_{periode}",
                            label_visibility="collapsed",
                        )
                        if ny_verdi != spillere[navn]["perioder"].get(p_idx, False):
                            _oppdater_bytteplan(
                                app_handler,
                                kamp_id,
                                spillere[navn]["id"],
                                p_idx,
                                ny_verdi,
                            )

        # Vis antall spillere på banen for hver periode
        st.markdown("---")
        cols = st.columns([2] + [1] * nytt_antall_perioder)
        cols[0].write("**Antall på banen**")

        # Beregn antall spillere på banen for hver periode
        for p_idx, periode in enumerate(perioder):
            antall_paa = sum(
                1
                for spiller in spillere.values()
                if spiller["perioder"].get(p_idx, False)
            )

            if antall_paa != nytt_antall_paa_banen:
                cols[p_idx + 1].markdown(f"**:red[{antall_paa}]**")
            else:
                cols[p_idx + 1].markdown(f"**:green[{antall_paa}]**")

        st.markdown("---")

        # Vis kompakt bytteplan
        st.subheader("Bytteplan")
        _vis_bytteplan_html(spillere, perioder, periode_lengde)

        # Vis statistikk
        st.markdown("---")
        _vis_bytteplan_statistikk(spillere, perioder, periode_lengde)

        # Vis nedlastbar versjon til slutt
        st.markdown("---")
        st.subheader("Last ned bytteplan")
        st.info(
            "💾 For å laste ned bytteplanen som en CSV-fil:\n"
            "1. Høyreklikk på tabellen under\n"
            "2. Velg 'Last ned som CSV'\n"
            "3. Filen kan åpnes i Excel eller Numbers"
        )
        _vis_bytteplan_oppsummering(spillere, perioder, periode_lengde)
    except Exception as e:
        logger.error("Feil ved visning av bytteplan: %s", str(e))
        st.error(f"Kunne ikke vis bytteplan: {str(e)}")
