"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, TypedDict

import pandas as pd

from min_kamp.db.handlers.bytteplan_handler import BytteplanHandler
from min_kamp.utils.streamlit_utils import get_session_state

logger = logging.getLogger("kampplanlegger")


class SpillerStats(TypedDict):
    """Type for spillerstatistikk"""

    perioder_spilt: int
    prosent_spilletid: float
    perioder: List[bool]


class BytteplanUtils:
    """Verktøy for håndtering av bytteplan"""

    def __init__(self, bytteplan_handler: BytteplanHandler):
        """
        Initialiserer BytteplanUtils.

        Args:
            bytteplan_handler: Handler for bytteplan-operasjoner
        """
        self.handler = bytteplan_handler

    @staticmethod
    def generer_posisjonssortert_df(
        spillere: List[Dict[str, Any]], kun_kamptropp: bool = True
    ) -> pd.DataFrame:
        """
        Genererer en DataFrame med spillere sortert etter posisjon

        Args:
            spillere: Liste med spillerdata
            kun_kamptropp: Hvis True, vis bare spillere i kamptroppen

        Returns:
            DataFrame med kolonner [navn, posisjon, er_paa]
        """
        if not spillere:
            return pd.DataFrame(columns=["navn", "posisjon", "er_paa"])

        posisjon_orden = {
            "Keeper": 1,
            "Forsvar": 2,
            "Midtbane": 3,
            "Angrep": 4,
            "": 5,  # For ukjente posisjoner
        }

        # Konverter til DataFrame og håndter manglende verdier
        df = pd.DataFrame(spillere)

        # Filtrer på kamptropp hvis spesifisert
        if kun_kamptropp and "i_kamptropp" in df.columns:
            df = df[df["i_kamptropp"]]

        # Sett standardverdier for manglende kolonner
        if "posisjon" not in df.columns:
            df["posisjon"] = ""
        if "navn" not in df.columns:
            df["navn"] = "Ukjent"
        if "er_paa" not in df.columns:
            df["er_paa"] = False

        # Håndter ukjente posisjoner
        df["posisjon"] = df["posisjon"].fillna("")

        # Sorter etter posisjon og navn
        df["posisjon_orden"] = df["posisjon"].map(posisjon_orden)
        df = df.sort_values(["posisjon_orden", "navn"])

        return df[["navn", "posisjon", "er_paa"]]

    @staticmethod
    def valider_bytteplan(
        bytter: List[Dict[str, Any]], min_spillere: int, max_spillere: int
    ) -> Dict[str, Any]:
        """
        Validerer at bytteplan følger reglene

        Args:
            bytter: Liste med bytter som skal valideres
            min_spillere: Minimum antall spillere på banen
            max_spillere: Maksimum antall spillere på banen

        Returns:
            Dict med valideringsresultat og eventuelle feilmeldinger
        """
        resultat: Dict[str, Any] = {
            "gyldig": True,
            "feilmeldinger": [],  # Initialiserer som tom liste
        }

        # Grupper bytter per periode
        for periode, periode_bytter in pd.DataFrame(bytter).groupby("periode"):
            antall_paa_banen = len(periode_bytter[periode_bytter["er_paa"]])

            if antall_paa_banen < min_spillere:
                resultat["gyldig"] = False
                resultat["feilmeldinger"].append(
                    f"For få spillere på banen i periode {periode} "
                    f"({antall_paa_banen})"
                )

            if antall_paa_banen > max_spillere:
                resultat["gyldig"] = False
                resultat["feilmeldinger"].append(
                    f"For mange spillere på banen i periode {periode} "
                    f"({antall_paa_banen})"
                )

        return resultat

    @staticmethod
    def beregn_spilletid(
        bytteplan: List[Dict[str, Any]], antall_perioder: int
    ) -> Dict[str, SpillerStats]:
        """
        Beregner spilletid for hver spiller basert på bytteplan.

        Args:
            bytteplan: Liste med bytter per periode
            antall_perioder: Totalt antall perioder i kampen

        Returns:
            Dict med spillerstatistikk per spiller-ID
        """
        spilletid: Dict[str, SpillerStats] = defaultdict(
            lambda: {
                "perioder_spilt": 0,
                "prosent_spilletid": 0.0,
                "perioder": [False] * antall_perioder,
            }
        )

        # Grupper bytter per periode og spiller
        for bytte in bytteplan:
            spiller_id = bytte["spiller_id"]
            periode = bytte["periode"]
            er_paa = bytte["er_paa"]

            if spiller_id not in spilletid:
                spilletid[spiller_id] = {
                    "perioder_spilt": 0,
                    "prosent_spilletid": 0.0,
                    "perioder": [False] * antall_perioder,
                }

            spilletid[spiller_id]["perioder"][periode] = er_paa
            if er_paa:
                spilletid[spiller_id]["perioder_spilt"] += 1

        # Beregn prosent spilletid
        for spiller_stats in spilletid.values():
            spiller_stats["prosent_spilletid"] = (
                float(spiller_stats["perioder_spilt"]) / float(antall_perioder) * 100.0
            )

        return dict(spilletid)

    @staticmethod
    def generer_spilleroversikt(
        kamptropp: Dict[str, Dict[str, Any]],
        alle_spilletider: Dict[str, List[bool]],
        antall_perioder: int,
        periode_lengde: int,
    ) -> pd.DataFrame:
        """
        Genererer en DataFrame med spilleroversikt for bytteplan

        Args:
            kamptropp: Dict med spillerinfo per spiller-ID
            alle_spilletider: Dict med spilletider per spiller-ID
            antall_perioder: Totalt antall perioder
            periode_lengde: Lengde på hver periode i minutter

        Returns:
            DataFrame med spilleroversikt
        """
        data = []
        for spiller_id, info in kamptropp.items():
            spilletider = alle_spilletider.get(spiller_id, [False] * antall_perioder)
            total_tid = sum(1 for x in spilletider if x) * periode_lengde
            current_periode_result = get_session_state("current_periode", default=0)
            current_periode = (
                current_periode_result.value if current_periode_result.success else 0
            )
            er_paa = bool(
                spilletider[int(current_periode)]
                if isinstance(current_periode, (int, float))
                else False
            )

            # Sikre at posisjon alltid er tilgjengelig
            posisjon = info.get(
                "posisjon", "Benk"
            )  # Standardverdi hvis posisjon mangler

            data.append(
                {
                    "spiller_id": spiller_id,
                    "navn": info.get(
                        "navn", "Ukjent"
                    ),  # Standardverdi hvis navn mangler
                    "posisjon": posisjon,
                    "total_spilletid": total_tid,
                    "er_paa": er_paa,
                }
            )

        if not data:
            # Returner tom DataFrame med riktige kolonner
            return pd.DataFrame(
                columns=[
                    "spiller_id",
                    "navn",
                    "posisjon",
                    "total_spilletid",
                    "er_paa",
                ]
            )

        return pd.DataFrame(data)

    @staticmethod
    def _valider_byttedata(bytte: Dict[str, Any]) -> bool:
        """
        Validerer at byttedata inneholder alle nødvendige felter

        Args:
            bytte: Dict med byttedata som skal valideres

        Returns:
            True hvis alle nødvendige felter er til stede
        """
        required_fields = {"spiller_id", "periode", "er_paa"}
        return all(field in bytte for field in required_fields)
