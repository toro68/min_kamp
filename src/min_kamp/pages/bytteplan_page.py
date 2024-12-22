# bytteplan_page.py
"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
import time
from typing import Any, Dict, List
import pandas as pd
import io

import streamlit as st
from dotenv import load_dotenv

from min_kamp.database.db_handler import DatabaseHandler
from min_kamp.database.handlers.bytteplan_handler import BytteplanHandler
from min_kamp.database.utils.bytteplan_utils import BytteplanUtils, SpillerStats
from min_kamp.pages.components.bytteplan_view import BytteplanView
from min_kamp.database.auth.auth_views import check_auth

logger = logging.getLogger(__name__)

# Last miljøvariabler
load_dotenv()

# Cache nøkler
CACHE_TTL = 300  # 5 minutter cache-tid


@st.cache_data(ttl=CACHE_TTL)
def hent_cached_kamper(user_id: str) -> List[Dict[str, Any]]:
    """Henter og cacher kamper for en bruker."""
    return st.session_state.app_handler.kamp_handler.hent_kamper(user_id)


@st.cache_data(ttl=CACHE_TTL)
def hent_cached_kamptropp(kamp_id: str, user_id: str) -> Dict[str, Any]:
    """Henter og cacher kamptropp."""
    return st.session_state.app_handler.kamp_handler.hent_kamptropp(kamp_id, user_id)


@st.cache_data(ttl=CACHE_TTL)
def beregn_spilletid(
    bytteplan: Dict[str, List[bool]], antall_perioder: int, periode_lengde: int
) -> Dict[str, Any]:
    """Beregner og cacher spilletid for hver spiller."""
    total_spilletid = antall_perioder * periode_lengde
    statistikk = {}

    for spiller_id, perioder in bytteplan.items():
        antall_perioder_spilt = sum(perioder[:antall_perioder])
        spilletid = antall_perioder_spilt * periode_lengde
        prosent = (spilletid / total_spilletid) * 100
        statistikk[spiller_id] = {"spilletid": spilletid, "prosent": prosent}

    return statistikk


@st.cache_data(ttl=CACHE_TTL)
def valider_bytteplan(
    bytteplan: Dict[str, List[bool]], antall_perioder: int, spillere_paa_banen: int
) -> Dict[str, Any]:
    """Validerer og cacher bytteplan."""
    feil = []
    for periode in range(antall_perioder):
        spillere_i_periode = sum(
            1 for perioder in bytteplan.values() if perioder[periode]
        )
        if spillere_i_periode != spillere_paa_banen:
            feil.append(
                f"Periode {periode + 1}: {spillere_i_periode} spillere på banen. Skal være {spillere_paa_banen} spillere."
            )

    return {"er_gyldig": len(feil) == 0, "feilmeldinger": feil}


def konverter_bytteplan_til_bytter(
    bytteplan: Dict[str, List[bool]], periode_lengde: int
) -> List[Dict[str, Any]]:
    """Konverterer bytteplan fra UI-format til database-format."""
    bytter = []
    for spiller_id, perioder in bytteplan.items():
        for periode_idx, er_aktiv in enumerate(perioder):
            if er_aktiv:
                bytte = {
                    "spiller_id": spiller_id,
                    "periode_nummer": periode_idx + 1,  # Periode nummer starter på 1
                    "start_tid": periode_idx * periode_lengde,
                    "slutt_tid": (periode_idx + 1) * periode_lengde,
                    "er_aktiv": True,
                    "er_paa_banen": True,  # Legger til manglende felt
                }
                bytter.append(bytte)
    return bytter


@st.cache_data(ttl=CACHE_TTL)
def initialiser_bytteplan(antall_perioder: int) -> Dict[str, List[bool]]:
    """Initialiserer en tom bytteplan."""
    return {}


@st.cache_data(ttl=CACHE_TTL)
def oppdater_bytteplan(
    bytteplan: Dict[str, List[bool]], spiller_id: str, periode: int, verdi: bool
) -> Dict[str, List[bool]]:
    """Oppdaterer bytteplan med ny verdi."""
    if spiller_id not in bytteplan:
        bytteplan[spiller_id] = [False] * 10  # Maks 10 perioder
    bytteplan[spiller_id][periode] = verdi
    return bytteplan


@st.cache_data(ttl=CACHE_TTL)
def generer_utskriftsvennlig_bytteplan(
    bytteplan: Dict[str, List[bool]],
    aktive_spillere: Dict[str, Dict[str, Any]],
    antall_perioder: int,
    periode_lengde: int,
) -> pd.DataFrame:
    """Genererer en utskriftsvennlig bytteplan med pandas DataFrame."""
    perioder = []
    posisjon_rekkefolge = ["Keeper", "Forsvar", "Midtbane", "Angrep", "Ukjent"]

    for periode in range(antall_perioder):
        spillere_per_posisjon = {pos: [] for pos in posisjon_rekkefolge}
        spillere_paa_benk = []
        spillere_inn = []
        spillere_ut = []
        start_tid = periode * periode_lengde

        # Finn spillere som er på banen og på benken i denne perioden
        for spiller_id, perioder_aktiv in bytteplan.items():
            if spiller_id in aktive_spillere:
                navn = aktive_spillere[spiller_id]["navn"]
                posisjon = aktive_spillere[spiller_id].get("posisjon", "Ukjent")
                if perioder_aktiv[periode]:
                    if posisjon in spillere_per_posisjon:
                        spillere_per_posisjon[posisjon].append(navn)
                    else:
                        spillere_per_posisjon["Ukjent"].append(navn)
                    # Sjekk om spilleren kommer inn (var ikke på banen i forrige periode)
                    if periode > 0 and not perioder_aktiv[periode - 1]:
                        spillere_inn.append(navn)
                else:
                    spillere_paa_benk.append(navn)
                    # Sjekk om spilleren går ut (var på banen i forrige periode)
                    if periode > 0 and perioder_aktiv[periode - 1]:
                        spillere_ut.append(navn)

        # Formater spillerlister med posisjon og nummerering
        spillere_paa_banen_formatert = []
        total_paa_banen = 0
        for posisjon in posisjon_rekkefolge:
            spillere = sorted(spillere_per_posisjon[posisjon])
            if spillere:
                spillere_paa_banen_formatert.append(f"\n{posisjon}:")
                for i, navn in enumerate(spillere, 1):
                    spillere_paa_banen_formatert.append(f"{i}. {navn}")
                total_paa_banen += len(spillere)

        spillere_paa_benk_formatert = "\n".join(
            f"{i+1}. {navn}" for i, navn in enumerate(sorted(spillere_paa_benk))
        )
        spillere_inn_formatert = (
            "\n".join(f"↗️ {navn}" for navn in sorted(spillere_inn))
            if spillere_inn
            else "-"
        )
        spillere_ut_formatert = (
            "\n".join(f"↙️ {navn}" for navn in sorted(spillere_ut))
            if spillere_ut
            else "-"
        )

        perioder.append(
            {
                "Periode": f"Periode {periode + 1}\n({start_tid} min)",
                "Starter på banen": "\n".join(spillere_paa_banen_formatert),
                "Bytter": f"INN:\n{spillere_inn_formatert}\n\nUT:\n{spillere_ut_formatert}",
                "På benken": spillere_paa_benk_formatert,
                "Antall": f"På banen: {total_paa_banen}\nPå benk: {len(spillere_paa_benk)}",
            }
        )

    # Opprett DataFrame og sett kolonnebredder
    df = pd.DataFrame(perioder)

    return df


@st.cache_data(ttl=CACHE_TTL)
def importer_spillertropp_fra_excel(excel_fil: io.BytesIO) -> Dict[str, Dict[str, Any]]:
    """
    Importerer spillertropp fra Excel-fil.

    Forventet format:
    - Kolonne 1: Navn
    - Kolonne 2: Nummer (valgfritt)
    - Kolonne 3: Posisjon (valgfritt)
    """
    try:
        df = pd.read_excel(excel_fil)

        # Sjekk at vi har minst én kolonne med navn
        if len(df.columns) < 1:
            raise ValueError("Excel-filen må ha minst én kolonne med spillernavn")

        # Standardiser kolonnenavn
        df.columns = [str(col).lower().strip() for col in df.columns]

        # Finn navnekolonnen (første kolonne)
        navn_kolonne = df.columns[0]

        # Opprett spillertropp dictionary
        spillertropp = {}
        for idx, row in df.iterrows():
            spiller_id = f"import_{idx}"  # Generer unik ID

            # Hent data fra rad
            navn = str(row[navn_kolonne]).strip()
            nummer = str(row.get("nummer", "")) if "nummer" in df.columns else ""
            posisjon = str(row.get("posisjon", "")) if "posisjon" in df.columns else ""

            if navn and navn.lower() != "nan":  # Sjekk at navn ikke er tomt eller NaN
                spillertropp[spiller_id] = {
                    "navn": navn,
                    "nummer": nummer,
                    "posisjon": posisjon,
                    "er_med": True,  # Standard: alle importerte spillere er med
                }

        return spillertropp

    except Exception as e:
        raise ValueError(f"Kunne ikke lese Excel-fil: {str(e)}")


class BytteplanPage:
    """Klasse for å håndtere bytteplan-siden."""

    def __init__(self):
        """Initialiserer BytteplanPage med nødvendige handlers."""
        self.db_handler = DatabaseHandler()
        self.bytteplan_handler = BytteplanHandler(self.db_handler)
        self.bytteplan_utils = BytteplanUtils(self.bytteplan_handler)
        self.bytteplan_view = BytteplanView()
        self.antall_perioder = 0  # Initialiserer antall_perioder

    def vis_bytteplan(self) -> None:
        """Viser bytteplan."""
        self.bytteplan_view.vis_bytteplan_view()

    def oppdater_bytteplan(
        self, bytteplan: List[Dict[str, Any]]
    ) -> Dict[str, SpillerStats]:
        """
        Oppdaterer bytteplan.

        Args:
            bytteplan: Liste med bytteplan-data

        Returns:
            Oppdatert bytteplan med beregnet spilletid
        """
        return self.bytteplan_utils.beregn_spilletid(bytteplan, self.antall_perioder)

    def vis_monster_preview(self, monster: Any, kamptropp: Dict[str, Any]) -> None:
        """
        Viser en preview av byttemonsteret.

        Args:
            monster: Monster-objekt som skal vises
            kamptropp: Dictionary med kamptropp-data
        """
        try:
            st.write(f"### Preview: {monster.navn}")
            st.write(monster.beskrivelse)

            if not monster.spillere or len(monster.spillere) != len(monster.monster):
                st.error("Feil antall spillere valgt for monsteret")
                return

            # Lag header
            antall_perioder = len(monster.monster[0]) if monster.monster else 0
            cols = st.columns([3] + [1] * antall_perioder)
            cols[0].write("Spiller")
            for i in range(antall_perioder):
                cols[i + 1].write(f"{i*monster.periode_lengde}'")

            # Vis monster for hver spiller
            for idx, (spiller_navn, rad) in enumerate(
                zip(monster.spillere, monster.monster)
            ):
                if idx < len(monster.spillere):
                    cols = st.columns([3] + [1] * len(rad))
                    cols[0].write(spiller_navn)
                    for periode_idx, er_aktiv in enumerate(rad):
                        cols[periode_idx + 1].write("✓" if er_aktiv else "·")

        except Exception as e:
            logger.error("Feil ved visning av bytteplan: %s", e)
            st.error(f"Kunne ikke vise bytteplan: {str(e)}")
            raise

    def vis_bytteplan_side(self) -> None:
        """Viser bytteplan-siden."""
        self.bytteplan_view.vis_bytteplan_view()


def vis_bytteplan_side() -> None:
    """Viser bytteplan-siden."""
    try:
        # Hent handlers fra session state
        auth_handler = st.session_state.auth_handler
        app_handler = st.session_state.app_handler

        # Sjekk autentisering
        if not check_auth(auth_handler):
            return

        st.title("Bytteplan")

        # Initialiser session state
        if "bytteplan" not in st.session_state:
            st.session_state.bytteplan = initialiser_bytteplan(10)
        if "bytteplan_endret" not in st.session_state:
            st.session_state.bytteplan_endret = False
        if "forrige_antall_perioder" not in st.session_state:
            st.session_state.forrige_antall_perioder = 4

        # Hent aktiv kamp
        kamper = hent_cached_kamper(st.session_state.user_id)
        if not kamper:
            st.info("Ingen aktive kamper funnet. Opprett en kamp først.")
            return

        # Velg kamp
        kamp_options = {
            f"{k['motstander']} ({k['dato']})": k["kamp_id"] for k in kamper
        }

        selected_kamp = st.selectbox(
            "Velg kamp:", options=list(kamp_options.keys()), key="selected_kamp"
        )

        if selected_kamp:
            kamp_id = kamp_options[selected_kamp]

            # Hent kamptropp
            kamptropp = hent_cached_kamptropp(kamp_id, st.session_state.user_id)
            if not kamptropp:
                st.warning(
                    "Ingen spillere valgt for denne kampen. Velg kamptropp først."
                )
                return

            # Vis innstillinger for bytteplan
            with st.expander("Innstillinger", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    kamp_lengde = st.number_input(
                        "Kamplengde (minutter)",
                        min_value=20,
                        max_value=120,
                        value=60,
                        step=5,
                        key="kamp_lengde",
                    )
                with col2:
                    antall_perioder = st.number_input(
                        "Antall perioder",
                        min_value=1,
                        max_value=12,
                        value=4,
                        key="antall_perioder",
                    )
                with col3:
                    spillere_paa_banen = st.number_input(
                        "Spillere på banen",
                        min_value=3,
                        max_value=11,
                        value=7,
                        key="spillere_paa_banen",
                    )
                with col4:
                    # Beregn periode_lengde basert på kamplengde og antall perioder
                    periode_lengde = kamp_lengde // antall_perioder
                    st.write(f"**Minutter per periode:** {periode_lengde}")

            # Vis aktive spillere
            st.subheader("Aktive spillere")
            aktive_spillere = {
                spiller_id: data
                for spiller_id, data in kamptropp.items()
                if data["er_med"]
            }

            if not aktive_spillere:
                st.warning("Ingen aktive spillere funnet i kamptroppen.")
                return

            # Sorter spillere etter posisjon
            spillere_per_posisjon = {}
            for spiller_id, data in aktive_spillere.items():
                posisjon = data.get("posisjon", "Ukjent")
                if posisjon not in spillere_per_posisjon:
                    spillere_per_posisjon[posisjon] = []
                spillere_per_posisjon[posisjon].append((spiller_id, data))

            # Oppdater bytteplan hvis antall perioder er endret
            if antall_perioder != st.session_state.forrige_antall_perioder:
                for spiller_id in aktive_spillere:
                    if spiller_id in st.session_state.bytteplan:
                        gamle_valg = st.session_state.bytteplan[spiller_id][
                            :antall_perioder
                        ]
                        nye_valg = gamle_valg + [False] * max(
                            0, antall_perioder - len(gamle_valg)
                        )
                        st.session_state.bytteplan = oppdater_bytteplan(
                            st.session_state.bytteplan,
                            spiller_id,
                            0,  # Dummy verdi siden vi oppdaterer hele listen
                            False,  # Dummy verdi siden vi oppdaterer hele listen
                        )
                        st.session_state.bytteplan[spiller_id] = nye_valg
                st.session_state.forrige_antall_perioder = antall_perioder

            # Definerer rekkefølgen på posisjoner
            posisjon_rekkefolge = ["Keeper", "Forsvar", "Midtbane", "Angrep", "Ukjent"]

            # Vis bytteplan-tabell
            st.subheader("Bytteplan")

            # Lag kolonner for hver periode
            cols = st.columns([3] + [1] * antall_perioder)

            # Overskrifter
            cols[0].write("**Spiller**")
            for i in range(antall_perioder):
                start_minutt = i * periode_lengde
                cols[i + 1].write(f"**{start_minutt}'**")

            # Vis spillere gruppert etter posisjon
            for posisjon in posisjon_rekkefolge:
                if posisjon in spillere_per_posisjon:
                    st.markdown(f"**{posisjon}**")
                    # Sorter spillere innen hver posisjon etter navn
                    spillere = sorted(
                        spillere_per_posisjon[posisjon], key=lambda x: x[1]["navn"]
                    )

                    for spiller_id, data in spillere:
                        cols = st.columns([3] + [1] * antall_perioder)
                        cols[0].write(data["navn"])

                        # Initialiser spillerens bytteplan hvis den ikke finnes
                        if spiller_id not in st.session_state.bytteplan:
                            st.session_state.bytteplan = oppdater_bytteplan(
                                st.session_state.bytteplan,
                                spiller_id,
                                0,  # Dummy verdi siden vi initialiserer
                                False,
                            )
                            st.session_state.bytteplan[spiller_id] = [
                                False
                            ] * antall_perioder

                        # Checkbox for hver periode
                        for i in range(antall_perioder):
                            key = f"spiller_{spiller_id}_periode_{i}"
                            if key not in st.session_state:
                                st.session_state[key] = st.session_state.bytteplan[
                                    spiller_id
                                ][i]

                            checked = cols[i + 1].checkbox(
                                f"{data['navn']} - Periode {i+1}",
                                key=key,
                                value=st.session_state[key],
                                label_visibility="collapsed",
                            )

                            # Oppdater bytteplan hvis endret
                            if checked != st.session_state.bytteplan[spiller_id][i]:
                                st.session_state.bytteplan = oppdater_bytteplan(
                                    st.session_state.bytteplan, spiller_id, i, checked
                                )
                                st.session_state.bytteplan_endret = True

            # Vis statistikk
            if st.session_state.bytteplan:
                st.subheader("Statistikk")

                # Beregn statistikk
                statistikk = beregn_spilletid(
                    st.session_state.bytteplan, antall_perioder, periode_lengde
                )

                for spiller_id, data in statistikk.items():
                    if spiller_id in aktive_spillere:
                        spiller = aktive_spillere[spiller_id]
                        st.write(
                            f"{spiller['navn']}: {data['spilletid']} min "
                            f"({data['prosent']:.1f}%)"
                        )

                # Valider bytteplan
                validering = valider_bytteplan(
                    st.session_state.bytteplan, antall_perioder, spillere_paa_banen
                )

                if not validering["er_gyldig"]:
                    for feil in validering["feilmeldinger"]:
                        st.warning(feil)

            # Vis utskriftsvennlig bytteplan etter statistikk-seksjonen
            if st.session_state.bytteplan:
                st.subheader("Utskriftsvennlig bytteplan")
                df = generer_utskriftsvennlig_bytteplan(
                    st.session_state.bytteplan,
                    aktive_spillere,
                    antall_perioder,
                    periode_lengde,
                )

                # Vis DataFrame
                st.dataframe(df, use_container_width=True)

                # Last ned som CSV
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Last ned bytteplan som CSV",
                    data=csv,
                    file_name="bytteplan.csv",
                    mime="text/csv",
                )

            # Lagre-knapp
            if st.session_state.bytteplan_endret:
                validering = valider_bytteplan(
                    st.session_state.bytteplan, antall_perioder, spillere_paa_banen
                )

                if not validering["er_gyldig"]:
                    st.error(
                        "Kan ikke lagre bytteplan. Sjekk at alle perioder har riktig antall spillere."
                    )
                elif st.button("Lagre bytteplan", key="lagre_bytteplan"):
                    try:
                        # Konverter bytteplan til bytter
                        bytter = konverter_bytteplan_til_bytter(
                            st.session_state.bytteplan, periode_lengde
                        )

                        # Lagre bytteplan til databasen med separate parametre
                        app_handler.bytteplan_handler.lagre_bytteplan(
                            kamp_id=kamp_id, bytter=bytter
                        )

                        st.success("Bytteplan lagret!")
                        st.session_state.bytteplan_endret = False

                        # Tving oppdatering av cache
                        hent_cached_kamper.clear()
                        hent_cached_kamptropp.clear()

                        # Kort pause for å la UI oppdatere seg
                        time.sleep(0.1)

                    except Exception as e:
                        logger.error(
                            "Feil ved lagring av bytteplan: %s", e, exc_info=True
                        )
                        st.error(f"Kunne ikke lagre bytteplan: {str(e)}")

        # Legg til Excel-import før kamptropp-visning
        with st.expander("Importer spillertropp fra Excel"):
            st.write("""
            Last opp en Excel-fil (.xlsx) med følgende format:
            - Første kolonne: Navn (påkrevd)
            - Andre kolonne: Nummer (valgfritt)
            - Tredje kolonne: Posisjon (valgfritt)
            """)

            uploaded_file = st.file_uploader(
                "Velg Excel-fil", type=["xlsx"], key="excel_import"
            )

            if uploaded_file is not None:
                try:
                    importert_tropp = importer_spillertropp_fra_excel(uploaded_file)
                    if importert_tropp:
                        if st.button("Legg til spillere i kamptropp"):
                            # Oppdater kamptropp i databasen
                            for spiller_id, spiller_data in importert_tropp.items():
                                app_handler.kamp_handler.legg_til_spiller(
                                    kamp_id=kamp_options[selected_kamp],
                                    spiller_data=spiller_data,
                                )
                            st.success(
                                f"Importerte {len(importert_tropp)} spillere til kamptroppen"
                            )

                            # Tving oppdatering av cache
                            hent_cached_kamptropp.clear()
                            time.sleep(
                                0.1
                            )  # Kort pause for å la databasen oppdatere seg

                except Exception as e:
                    st.error(f"Feil ved import av spillertropp: {str(e)}")

    except Exception:
        logger.error("Feil ved visning av bytteplan-side: %s", exc_info=True)
        st.error("Kunne ikke vise bytteplan-siden")
