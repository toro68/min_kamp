"""
Bytteplan-side for kampplanleggeren
"""

import logging
from typing import Any, Dict, List
import pandas as pd
import io

import streamlit as st
from dotenv import load_dotenv


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
                    "er_paa_banen": True,
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
        bytteplan[spiller_id] = [False] * 12  # Maks 12 perioder
    bytteplan[spiller_id][periode] = verdi
    return bytteplan


def importer_spillertropp_fra_excel(excel_fil: io.BytesIO) -> Dict[str, Dict[str, Any]]:
    """
    Importerer spillertropp fra Excel-fil.

    Forventet format:
    - Første kolonne: Navn (påkrevd)
    - Andre kolonne: Nummer (valgfritt)
    - Tredje kolonne: Posisjon (valgfritt)
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


def vis_bytteplan_side() -> None:
    """Viser bytteplan-siden."""
    try:
        # Initialiser session state
        if "bytteplan" not in st.session_state:
            st.session_state.bytteplan = initialiser_bytteplan(12)
        if "bytteplan_endret" not in st.session_state:
            st.session_state.bytteplan_endret = False
        if "forrige_antall_perioder" not in st.session_state:
            st.session_state.forrige_antall_perioder = 4
        if "app_handler" not in st.session_state:
            st.session_state.app_handler = None
        if "user_id" not in st.session_state:
            st.session_state.user_id = 1

        st.title("Bytteplan")

        # Legg til Excel-import før innstillinger
        with st.expander("Importer spillertropp fra Excel", expanded=True):
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
                        st.success(
                            f"Leste inn {len(importert_tropp)} spillere fra Excel"
                        )

                        # Oppdater spillerlisten med importerte spillere
                        spillere = {}
                        for spiller_id, data in importert_tropp.items():
                            posisjon = data.get("posisjon", "").strip()
                            if not posisjon or posisjon not in [
                                "Keeper",
                                "Forsvar",
                                "Midtbane",
                                "Angrep",
                            ]:
                                posisjon = "Midtbane"  # Standard posisjon

                            spillere[spiller_id] = {
                                "navn": data["navn"],
                                "posisjon": posisjon,
                                "er_med": True,
                            }

                except Exception as e:
                    st.error(f"Feil ved import av spillertropp: {str(e)}")

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

        # Demo-spillere
        st.subheader("Spillere")
        spillere = {
            "1": {"navn": "Spiller 1", "posisjon": "Keeper", "er_med": True},
            "2": {"navn": "Spiller 2", "posisjon": "Forsvar", "er_med": True},
            "3": {"navn": "Spiller 3", "posisjon": "Forsvar", "er_med": True},
            "4": {"navn": "Spiller 4", "posisjon": "Midtbane", "er_med": True},
            "5": {"navn": "Spiller 5", "posisjon": "Midtbane", "er_med": True},
            "6": {"navn": "Spiller 6", "posisjon": "Angrep", "er_med": True},
            "7": {"navn": "Spiller 7", "posisjon": "Angrep", "er_med": True},
        }

        # Sorter spillere etter posisjon
        spillere_per_posisjon = {}
        for spiller_id, data in spillere.items():
            posisjon = data.get("posisjon", "Ukjent")
            if posisjon not in spillere_per_posisjon:
                spillere_per_posisjon[posisjon] = []
            spillere_per_posisjon[posisjon].append((spiller_id, data))

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
                spillere_i_posisjon = sorted(
                    spillere_per_posisjon[posisjon], key=lambda x: x[1]["navn"]
                )

                for spiller_id, data in spillere_i_posisjon:
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
                if spiller_id in spillere:
                    spiller = spillere[spiller_id]
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

        # Vis utskriftsvennlig bytteplan
        if st.session_state.bytteplan:
            st.subheader("Utskriftsvennlig bytteplan")

            # Generer utskriftsvennlig versjon
            perioder = []
            for periode in range(antall_perioder):
                spillere_paa_banen = []
                spillere_paa_benk = []
                start_tid = periode * periode_lengde

                for spiller_id, perioder_aktiv in st.session_state.bytteplan.items():
                    if spiller_id in spillere:
                        navn = spillere[spiller_id]["navn"]
                        if perioder_aktiv[periode]:
                            spillere_paa_banen.append(navn)
                        else:
                            spillere_paa_benk.append(navn)

                perioder.append(
                    {
                        "Periode": f"{start_tid}'-{start_tid + periode_lengde}'",
                        "På banen": ", ".join(sorted(spillere_paa_banen)),
                        "På benken": ", ".join(sorted(spillere_paa_benk)),
                    }
                )

            # Vis som DataFrame
            df = pd.DataFrame(perioder)
            st.dataframe(df, use_container_width=True)

            # Last ned som CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Last ned bytteplan som CSV",
                data=csv,
                file_name="bytteplan.csv",
                mime="text/csv",
            )

    except Exception as e:
        logger.error("Feil ved visning av bytteplan-side: %s", str(e), exc_info=True)
        st.error(f"En feil oppstod: {str(e)}")
