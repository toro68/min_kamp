# kamptropp_page.py
"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict
from datetime import date
import time

import streamlit as st
from min_kamp.database.auth.auth_views import check_auth

logger = logging.getLogger(__name__)


@st.cache_data(ttl=60)
def hent_kamper(_app_handler, user_id: int) -> List[Dict[str, Any]]:
    """Henter kamper med caching."""
    return _app_handler.kamp_handler.hent_kamper(user_id)


@st.cache_data(ttl=60)
def hent_kamptropp(
    _app_handler, kamp_id: int, user_id: int
) -> Dict[int, Dict[str, Any]]:
    """Henter kamptropp med caching."""
    return _app_handler.kamp_handler.hent_kamptropp(kamp_id, user_id)


def initialiser_session_state():
    """Initialiserer session state variabler."""
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "current_kamp_id": None,
            "valgte_spillere": set(),
            "viser_bekreftelse": False,
            "lagring_aktiv": False,
            "sist_oppdatert": None,
            "melding": None,
            "melding_type": None,
            "endret": False,
            "kamp_options": {},
            "sist_valgte_kamp": None,
            "opprinnelige_valgte_spillere": set(),
        }


def vis_melding():
    """Viser meldinger til bruker."""
    if st.session_state.app_state["melding"]:
        if st.session_state.app_state["melding_type"] == "success":
            st.success(st.session_state.app_state["melding"])
        elif st.session_state.app_state["melding_type"] == "error":
            st.error(st.session_state.app_state["melding"])
        elif st.session_state.app_state["melding_type"] == "warning":
            st.warning(st.session_state.app_state["melding"])
        st.session_state.app_state["melding"] = None
        st.session_state.app_state["melding_type"] = None


def toggle_spiller(spiller_id: int):
    """Callback for å håndtere spiller-toggle."""
    key = f"spiller_{spiller_id}"
    if key in st.session_state:
        if st.session_state[key]:
            st.session_state.app_state["valgte_spillere"].add(spiller_id)
        else:
            st.session_state.app_state["valgte_spillere"].discard(spiller_id)

        st.session_state.app_state["endret"] = (
            st.session_state.app_state["valgte_spillere"]
            != st.session_state.app_state["opprinnelige_valgte_spillere"]
        )


def bytt_kamp():
    """Callback for å håndtere kampbytte."""
    if "kamp_velger" in st.session_state:
        selected_kamp = st.session_state.kamp_velger
        kamp_id = st.session_state.app_state["kamp_options"][selected_kamp]
        st.session_state.app_state["current_kamp_id"] = kamp_id
        st.session_state.app_state["valgte_spillere"] = set()
        st.session_state.app_state["opprinnelige_valgte_spillere"] = set()
        st.session_state.app_state["endret"] = False


def lagre_kamptropp(app_handler, kamp_id: int, user_id: int):
    """Lagrer kamptropp."""
    try:
        if app_handler.kamp_handler.lagre_kamptropp(
            kamp_id, list(st.session_state.app_state["valgte_spillere"]), user_id
        ):
            st.session_state.app_state["melding"] = "Kamptropp lagret!"
            st.session_state.app_state["melding_type"] = "success"
            st.session_state.app_state["opprinnelige_valgte_spillere"] = set(
                st.session_state.app_state["valgte_spillere"]
            )
            st.session_state.app_state["endret"] = False
            hent_kamptropp.clear()
        else:
            st.session_state.app_state["melding"] = "Kunne ikke lagre kamptropp"
            st.session_state.app_state["melding_type"] = "error"
    except Exception as e:
        logger.error("Feil ved lagring av kamptropp: %s", str(e))
        st.session_state.app_state["melding"] = (
            "En feil oppstod ved lagring av kamptroppen"
        )
        st.session_state.app_state["melding_type"] = "error"


def vis_spillere(kamptropp: Dict[int, Dict[str, Any]], posisjon: str) -> None:
    """Viser spillere for en gitt posisjon."""
    spillere = [
        (spiller_id, data)
        for spiller_id, data in kamptropp.items()
        if data["posisjon"] == posisjon
    ]
    logger.debug(f"Viser spillere for posisjon {posisjon}")
    logger.debug(f"Antall spillere funnet: {len(spillere)}")
    logger.debug(
        f"Spillere i denne posisjonen: {[(data['navn'], data['posisjon']) for _, data in spillere]}"
    )

    if spillere:
        st.write(f"**{posisjon}:**")
        for spiller_id, data in spillere:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                key = f"spiller_{spiller_id}"
                er_valgt = spiller_id in st.session_state.app_state["valgte_spillere"]

                if st.checkbox(data["navn"], value=er_valgt, key=key):
                    logger.debug(
                        f"Legger til spiller {data['navn']} (ID: {spiller_id})"
                    )
                    st.session_state.app_state["valgte_spillere"].add(spiller_id)
                else:
                    logger.debug(f"Fjerner spiller {data['navn']} (ID: {spiller_id})")
                    st.session_state.app_state["valgte_spillere"].discard(spiller_id)

            with col2:
                ny_posisjon = st.selectbox(
                    "Posisjon",
                    ["Keeper", "Forsvar", "Midtbane", "Angrep"],
                    index=["Keeper", "Forsvar", "Midtbane", "Angrep"].index(
                        data["posisjon"]
                    ),
                    key=f"posisjon_{spiller_id}",
                    label_visibility="collapsed",
                )

                if ny_posisjon != data["posisjon"]:
                    logger.debug(
                        f"Endrer posisjon for {data['navn']} fra {data['posisjon']} til {ny_posisjon}"
                    )
                    try:
                        st.session_state.app_handler.spiller_handler.endre_spiller_posisjon(
                            spiller_id, ny_posisjon
                        )
                        hent_kamptropp.clear()
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Feil ved endring av posisjon: {str(e)}")
                        st.error(f"Kunne ikke endre posisjon: {str(e)}")

            with col3:
                if st.button(
                    "🗑️",
                    key=f"slett_{spiller_id}",
                    help=f"Slett {data['navn']}",
                    type="secondary",
                ):
                    logger.debug(f"Sletter spiller {data['navn']} (ID: {spiller_id})")
                    try:
                        if st.session_state.app_handler.spiller_handler.slett_spiller(
                            spiller_id
                        ):
                            st.session_state.app_state["valgte_spillere"].discard(
                                spiller_id
                            )
                            # Tøm cache for å tvinge oppdatering av kamptropp
                            hent_kamptropp.clear()
                            time.sleep(
                                0.1
                            )  # Kort pause for å la databasen oppdatere seg
                            st.rerun()
                        else:
                            st.error(f"Kunne ikke slette {data['navn']}")
                    except Exception as e:
                        logger.error(f"Feil ved sletting av spiller: {str(e)}")
                        st.error(f"Kunne ikke slette spiller: {str(e)}")

        logger.debug(
            f"Oppdatert valgte_spillere: {st.session_state.app_state['valgte_spillere']}"
        )
        logger.debug(
            f"Opprinnelige valgte_spillere: {st.session_state.app_state['opprinnelige_valgte_spillere']}"
        )

        st.session_state.app_state["endret"] = (
            st.session_state.app_state["valgte_spillere"]
            != st.session_state.app_state["opprinnelige_valgte_spillere"]
        )
        logger.debug(f"Endret: {st.session_state.app_state['endret']}")


def vis_valgt_tropp(kamptropp: Dict[int, Dict[str, Any]], valgte_spillere: set) -> None:
    """Viser oversikt over valgt tropp."""
    st.write("**Valgt tropp:**")

    valgte_by_posisjon = defaultdict(list)
    for spiller_id in valgte_spillere:
        if spiller_id in kamptropp:
            data = kamptropp[spiller_id]
            valgte_by_posisjon[data["posisjon"]].append(data["navn"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"Keepere: {len(valgte_by_posisjon['Keeper'])}")
    with col2:
        st.write(f"Forsvar: {len(valgte_by_posisjon['Forsvar'])}")
    with col3:
        st.write(f"Midtbane: {len(valgte_by_posisjon['Midtbane'])}")
    with col4:
        st.write(f"Angrep: {len(valgte_by_posisjon['Angrep'])}")

    for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
        if valgte_by_posisjon[posisjon]:
            st.write(f"**{posisjon}:** {', '.join(valgte_by_posisjon[posisjon])}")


def vis_kamptropp_side() -> None:
    """Viser kamptropp-siden"""
    try:
        # Hent handlers fra session state
        auth_handler = st.session_state.auth_handler
        app_handler = st.session_state.app_handler

        # Sjekk autentisering
        if not check_auth(auth_handler):
            return

        st.title("Velg kamptropp")

        # Initialiser session state
        initialiser_session_state()

        # Vis eventuelle meldinger
        vis_melding()

        # Vis eksisterende kamper
        kamper = hent_kamper(app_handler, st.session_state.user_id)
        logger.debug(f"Hentet {len(kamper)} kamper")

        if kamper:
            # Lag en mapping mellom visningsnavn og kamp-ID
            kamp_options = {
                f"{k['motstander']} ({k['dato']})": k["kamp_id"] for k in kamper
            }
            st.session_state.app_state["kamp_options"] = kamp_options
            logger.debug(f"Kamp options: {kamp_options}")

            # Finn gjeldende kamp
            current_kamp_id = st.session_state.app_state["current_kamp_id"]
            if not current_kamp_id:
                current_kamp_id = next(iter(kamp_options.values()))
                st.session_state.app_state["current_kamp_id"] = current_kamp_id
            logger.debug(f"Gjeldende kamp ID: {current_kamp_id}")

            current_kamp_name = next(
                (name for name, kid in kamp_options.items() if kid == current_kamp_id),
                None,
            )
            logger.debug(f"Gjeldende kamp navn: {current_kamp_name}")

            # Vis nedtrekksmeny for å velge kamp
            selected_kamp = st.selectbox(
                "Velg kamp:",
                options=list(kamp_options.keys()),
                index=list(kamp_options.keys()).index(current_kamp_name)
                if current_kamp_name
                else 0,
                key="kamp_velger",
                on_change=bytt_kamp,
            )

            if selected_kamp:
                kamp_id = kamp_options[selected_kamp]
                logger.debug(f"Valgt kamp ID: {kamp_id}")
                kamptropp = hent_kamptropp(
                    app_handler, kamp_id, st.session_state.user_id
                )
                logger.debug(f"Hentet kamptropp med {len(kamptropp)} spillere")
                logger.debug("Full kamptropp:")
                for spiller_id, data in kamptropp.items():
                    logger.debug(f"  Spiller {spiller_id}: {data}")

                # Initialiser valgte spillere fra databasen hvis ikke allerede gjort
                if not st.session_state.app_state["valgte_spillere"]:
                    valgte_spillere = {
                        spiller_id
                        for spiller_id, data in kamptropp.items()
                        if data["er_med"]
                    }
                    st.session_state.app_state["valgte_spillere"] = valgte_spillere
                    st.session_state.app_state["opprinnelige_valgte_spillere"] = set(
                        valgte_spillere
                    )
                    logger.debug(f"Initialiserte valgte spillere: {valgte_spillere}")

                st.write("Velg spillere til kamptroppen:")

                # Vis spillere gruppert etter posisjon
                for posisjon in ["Keeper", "Forsvar", "Midtbane", "Angrep"]:
                    vis_spillere(kamptropp, posisjon)

                antall_valgt = len(st.session_state.app_state["valgte_spillere"])
                logger.debug(f"Antall valgte spillere: {antall_valgt}")
                st.write(f"Antall valgte spillere: {antall_valgt}")

                # Vis oversikt over valgt tropp
                if st.session_state.app_state["valgte_spillere"]:
                    st.divider()
                    vis_valgt_tropp(
                        kamptropp, st.session_state.app_state["valgte_spillere"]
                    )

                # Lagre-form
                with st.form("lagre_form"):
                    logger.debug("Viser lagre-form")
                    if antall_valgt >= 7:
                        logger.debug("Nok spillere valgt, viser submit-knapp")
                        if st.form_submit_button(
                            "Lagre kamptropp",
                            disabled=not st.session_state.app_state["endret"],
                        ):
                            logger.debug("Lagre-knapp trykket")
                            lagre_kamptropp(
                                app_handler, kamp_id, st.session_state.user_id
                            )
                    else:
                        logger.debug("For få spillere valgt, viser advarsel")
                        st.warning(
                            "Du må velge minst 7 spillere for å lagre kamptroppen"
                        )

        else:
            logger.debug("Ingen kamper funnet, viser skjema for å opprette ny kamp")
            # Legg til ny kamp
            st.info("Du må opprette en kamp før du kan velge spillere til kamptroppen.")
            with st.form("ny_kamp_form"):
                st.write("### Opprett ny kamp")
                motstander = st.text_input("Motstander")
                valgt_dato = st.date_input("Dato")
                hjemmebane = st.checkbox("Hjemmekamp", value=True)

                if st.form_submit_button("Opprett kamp"):
                    logger.debug(
                        f"Forsøker å opprette kamp: {motstander} ({valgt_dato})"
                    )
                    if motstander:
                        try:
                            if not isinstance(valgt_dato, (date, tuple)):
                                st.error("Ugyldig dato")
                                return

                            # Håndter at st.date_input kan returnere en tuple
                            if isinstance(valgt_dato, tuple) and not valgt_dato:
                                st.error("Ugyldig dato")
                                return

                            dato_str = (
                                valgt_dato.strftime("%Y-%m-%d")
                                if isinstance(valgt_dato, date)
                                else valgt_dato[0].strftime("%Y-%m-%d")
                            )

                            kamp_id = app_handler.kamp_handler.registrer_kamp(
                                dato=dato_str,
                                motstander=motstander,
                                hjemmebane=hjemmebane,
                                user_id=st.session_state.user_id,
                            )
                            if kamp_id:
                                logger.debug(f"Opprettet kamp med ID: {kamp_id}")
                                st.session_state.app_state["current_kamp_id"] = kamp_id
                                st.session_state.app_state["valgte_spillere"] = set()
                                st.session_state.app_state[
                                    "opprinnelige_valgte_spillere"
                                ] = set()
                                st.session_state.app_state["melding"] = (
                                    f"Kamp mot {motstander} opprettet!"
                                )
                                st.session_state.app_state["melding_type"] = "success"
                                st.session_state.app_state["endret"] = False
                                hent_kamper.clear()
                                st.rerun()
                            else:
                                logger.error("Kunne ikke opprette kamp")
                                st.error("Kunne ikke opprette kamp")
                        except Exception as e:
                            logger.error(f"Feil ved opprettelse av kamp: {str(e)}")
                            st.error(f"Kunne ikke opprette kamp: {str(e)}")
                    else:
                        logger.warning("Forsøkte å opprette kamp uten motstander")
                        st.error("Fyll inn motstander")

    except Exception as e:
        logger.error(f"Feil ved visning av kamptropp-side: {str(e)}", exc_info=True)
        st.error("En feil oppstod ved visning av kamptropp-siden")
