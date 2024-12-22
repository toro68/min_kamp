"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Hovedapplikasjon for kampplanleggeren.
Se spesielt:
- avhengigheter.md -> Frontend
- system.md -> Systemarkitektur -> Frontend
"""

import logging
from collections import defaultdict
from sqlite3 import Error as SQLiteError
from typing import Any, Dict, List, Optional, TypedDict

import pandas as pd
import streamlit as st

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.bytteplan_handler import BytteplanHandler

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
            DataFrame med kolonner [navn, posisjon, er_paa_banen]
        """
        if not spillere:
            return pd.DataFrame(columns=["navn", "posisjon", "er_paa_banen"])

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
        if "er_paa_banen" not in df.columns:
            df["er_paa_banen"] = False

        # Håndter ukjente posisjoner
        df["posisjon"] = df["posisjon"].fillna("")

        # Sorter etter posisjon og navn
        df["posisjon_orden"] = df["posisjon"].map(posisjon_orden)
        df = df.sort_values(["posisjon_orden", "navn"])

        return df[["navn", "posisjon", "er_paa_banen"]]

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
        for periode, periode_bytter in pd.DataFrame(bytter).groupby("periode_nummer"):
            antall_paa_banen = len(periode_bytter[periode_bytter["er_paa_banen"]])

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
            periode = bytte["periode_nummer"]
            er_paa_banen = bytte["er_paa_banen"]

            if spiller_id not in spilletid:
                spilletid[spiller_id] = {
                    "perioder_spilt": 0,
                    "prosent_spilletid": 0.0,
                    "perioder": [False] * antall_perioder,
                }

            spilletid[spiller_id]["perioder"][periode] = er_paa_banen
            if er_paa_banen:
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
            er_paa_banen = spilletider[st.session_state.get("current_periode", 0)]

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
                    "er_paa_banen": er_paa_banen,
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
                    "er_paa_banen",
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
        required_fields = {"spiller_id", "periode_nummer", "er_paa_banen"}
        return all(field in bytte for field in required_fields)

    def lagre_bytteplan(self, kamp_id: str, bytter: List[Dict[str, Any]]) -> bool:
        """
        Lagrer bytteplan via BytteplanHandler.

        Args:
            kamp_id: ID for kampen
            bytter: Liste med bytter som skal lagres

        Returns:
            True hvis lagring var vellykket
        """
        try:
            return self.handler.lagre_bytteplan(kamp_id, bytter)
        except (SQLiteError, DatabaseError) as e:
            logger.error("Feil ved lagring av bytteplan: %s", e)
            return False

    def eksporter_bytteplan(self, kamp_id: str, filnavn: Optional[str] = None) -> str:
        """
        Eksporterer bytteplan via BytteplanHandler.

        Args:
            kamp_id: ID for kampen
            filnavn: Valgfritt filnavn for eksporten

        Returns:
            Sti til eksportert fil
        """
        try:
            return self.handler.eksporter_bytteplan(kamp_id, filnavn)
        except (SQLiteError, DatabaseError, IOError) as e:
            logger.error("Feil ved eksportering av bytteplan: %s", e)
            return ""
