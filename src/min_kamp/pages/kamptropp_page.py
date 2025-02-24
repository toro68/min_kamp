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
) -> bool:
    """Sletter en spiller fra kamptroppen.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID til aktiv kamp
        spiller_id: ID til spilleren som skal slettes

    Returns:
        bool: True hvis sletting var vellykket, False ellers
    """
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            logger.debug(
                "Kaller slett_spiller_fra_kamptropp: "
                "kamp_id=%s, spiller_id=%s", 
                kamp_id, 
                spiller_id
            )
            
            # Sjekk om spilleren eksisterer i kamptroppen
            cursor.execute(
                "SELECT * FROM kamptropp "
                "WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id)
            )
            eksisterende_spiller = cursor.fetchone()
            
            if not eksisterende_spiller:
                logger.warning(
                    "Ingen spiller funnet: kamp_id=%s, spiller_id=%s", 
                    kamp_id, 
                    spiller_id
                )
                st.warning(f"Spilleren finnes ikke i kamptroppen")
                return False

            # Oppdaterer spillerens status til inaktiv (er_med = 0)
            cursor.execute(
                "UPDATE kamptropp SET er_med = 0 "
                "WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id),
            )
            rows = cursor.rowcount
            
            logger.debug("Antall oppdaterte rader: %s", rows)
            
            if rows == 0:
                logger.error(
                    "Ingen rader oppdatert: kamp_id=%s, spiller_id=%s", 
                    kamp_id, 
                    spiller_id
                )
                st.error("Kunne ikke oppdatere spillerens status")
                return False
            
            conn.commit()

        logger.info(
            "Satt spiller %s som inaktiv for kamp %s",
            spiller_id,
            kamp_id,
        )
        return True
    
    except Exception as e:
        logger.error(
            "Feil ved oppdatering av spiller %s til inaktiv for kamp %s: %s", 
            spiller_id, 
            kamp_id, 
            e,
            exc_info=True  # Legg til full stack trace
        )
        st.error(
            f"Kunne ikke sette spiller inaktiv med ID {spiller_id}. "
            f"Feil: {str(e)}"
        )
        return False


def slett_spiller_helt(
    app_handler: AppHandler,
    kamp_id: int,
    spiller_id: int,
) -> bool:
    """Sletter en spiller helt fra kamptroppen og spillerdatabasen.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID til aktiv kamp
        spiller_id: ID til spilleren som skal slettes

    Returns:
        bool: True hvis sletting var vellykket, False ellers
    """
    try:
        # Logg detaljert informasjon ved start av sletteprosess
        logger.info(
            "Starter sletting av spiller. "
            "Kamp ID: %s, Spiller ID: %s", 
            kamp_id, 
            spiller_id
        )

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            
            # Hent detaljer om spilleren før sletting
            cursor.execute(
                "SELECT * FROM spiller WHERE id = ?", 
                (spiller_id,)
            )
            eksisterende_spiller = cursor.fetchone()
            
            if not eksisterende_spiller:
                logger.warning(
                    "Ingen spiller funnet med ID: %s", 
                    spiller_id
                )
                st.warning(f"Spilleren med ID {spiller_id} eksisterer ikke")
                return False

            # Logg spillerdetaljer
            logger.info(
                "Spillerdetaljer før sletting: %s", 
                eksisterende_spiller
            )

            # Slett spilleren fra kamptroppen
            cursor.execute(
                "DELETE FROM kamptropp "
                "WHERE kamp_id = ? AND spiller_id = ?",
                (kamp_id, spiller_id)
            )
            kamptropp_rader = cursor.rowcount
            logger.info(
                "Slettet %s rader fra kamptropp", 
                kamptropp_rader
            )

            # Slett spilleren fra spillertabellen
            cursor.execute(
                "DELETE FROM spiller WHERE id = ?", 
                (spiller_id,)
            )
            spiller_rader = cursor.rowcount
            logger.info(
                "Slettet %s rader fra spillertabell", 
                spiller_rader
            )

            # Commit transaksjonen
            conn.commit()
            logger.info("Transaksjon committed")

            # Sjekk om slettingen var vellykket
            if spiller_rader == 0:
                logger.error(
                    "Kunne ikke slette spilleren med ID %s", 
                    spiller_id
                )
                st.error(f"Kunne ikke slette spilleren med ID {spiller_id}")
                return False

            # Bekreft sletting ved å sjekke at spilleren ikke lenger eksisterer
            cursor.execute(
                "SELECT * FROM spiller WHERE id = ?", 
                (spiller_id,)
            )
            bekreftet_slettet = cursor.fetchone() is None
            
            if bekreftet_slettet:
                st.success(f"Spilleren er fullstendig fjernet")
                logger.info(
                    "Spiller %s fullstendig fjernet fra kamp %s", 
                    spiller_id, 
                    kamp_id
                )
                return True
            else:
                logger.error(
                    "Spilleren %s kunne ikke slettes fullstendig", 
                    spiller_id
                )
                st.error(f"Kunne ikke slette spilleren fullstendig")
                return False
    
    except Exception as e:
        logger.error(
            "Kritisk feil ved sletting av spiller %s fra kamp %s: %s", 
            spiller_id, 
            kamp_id, 
            e,
            exc_info=True
        )
        st.error(
            f"En kritisk feil oppstod ved sletting av spilleren. "
            f"Vennligst kontakt support. Feilmelding: {str(e)}"
        )
        return False


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
        spillere = kamptropp["spillere"][posisjon]
        if not spillere:
            return

        st.write(f"### {posisjon}")

        # Legg til en "Velg alle" checkbox for hver posisjon
        velg_alle = st.checkbox(
            f"Velg alle {posisjon}", 
            key=f"velg_alle_{posisjon}"
        )

        # Vis hver spiller med en checkbox for aktiv status (avhukingsboks)
        for spiller in spillere:
            is_active = bool(int(spiller["er_med"]))
            col_name, col_checkbox, col_slett = st.columns([3, 1, 1])
            
            with col_name:
                st.write(spiller["navn"])
            
            with col_checkbox:
                # Bruk velg_alle til å sette checkbox-verdien
                nye_verdi = st.checkbox(
                    f"Aktiv {spiller['navn']}", 
                    value=velg_alle or is_active, 
                    key=f"checkbox_{spiller['id']}", 
                    label_visibility="hidden"
                )
                
                # Håndter endringer i spillerens status
                if nye_verdi != is_active:
                    if not nye_verdi:
                        # Fjern spiller fra kamptropp
                        if slett_spiller_fra_kamptropp(
                            app_handler, kamp_id, spiller["id"]
                        ):
                            st.success(
                                f"Spilleren {spiller['navn']} fjernet"
                            )
                        else:
                            st.error(
                                f"Kunne ikke fjerne spilleren {spiller['navn']}"
                            )
                    else:
                        # Legg til spiller i kamptropp (hvis ikke allerede med)
                        try:
                            with app_handler._database_handler.connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE kamptropp SET er_med = 1 "
                                    "WHERE kamp_id = ? AND spiller_id = ?",
                                    (kamp_id, spiller["id"]),
                                )
                                conn.commit()
                            st.success(
                                f"Spilleren {spiller['navn']} lagt til"
                            )
                        except Exception as e:
                            logger.error(f"Feil ved legge til spiller: {e}")
                            st.error(
                                f"Kunne ikke legge til spilleren {spiller['navn']}"
                            )
                    
                    # Oppdater siden
                    st.rerun()
            
            # Legg til slett-knapp
            with col_slett:
                if st.button(
                    "Slett", 
                    key=f"slett_{spiller['id']}", 
                    help=f"Fjern {spiller['navn']} helt fra troppen"
                ):
                    # Bekreftelsesdialog
                    if st.checkbox(
                        f"Bekreft sletting av {spiller['navn']}", 
                        key=f"bekreft_slett_{spiller['id']}"
                    ):
                        # Forsøk å slette spilleren helt
                        if slett_spiller_helt(
                            app_handler, kamp_id, spiller["id"]
                        ):
                            st.success(
                                f"{spiller['navn']} er slettet fra troppen"
                            )
                            st.rerun()
                        else:
                            st.error(
                                f"Kunne ikke slette {spiller['navn']}"
                            )

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
