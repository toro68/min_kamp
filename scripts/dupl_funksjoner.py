#!/usr/bin/env python3
"""
Analyseverktøy for å finne dupliserte funksjoner i Python-kodebase.

Dette scriptet analyserer Python-filer for å finne funksjoner som er implementert
flere steder, og hjelper med å identifisere hvor funksjonene bør konsolideres.
"""

import ast
import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# Logging oppsett
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class FunksjonType(Enum):
    """Definerer ulike typer funksjonsimplementasjoner."""

    NORMAL = auto()  # Vanlig implementasjon
    IMPLEMENTASJON = auto()  # Hovedimplementasjon
    DELEGERING = auto()  # Delegerer til en annen implementasjon
    IMPORTERT = auto()  # Importert fra en annen modul
    WRAPPER = auto()  # Wrapper rundt en annen implementasjon


class Prioritet(Enum):
    """Definerer prioritetsnivåer for refaktorering."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Problem:
    """Representerer et problem funnet i kodebasen."""

    fil: str
    type: str
    melding: str
    linje: Optional[int] = None
    alvorlighet: Optional[str] = None


@dataclass
class FunksjonInfo:
    """Holder informasjon om en funksjon."""

    filsti: str
    navn: str
    type: FunksjonType
    linjenummer: int
    detaljer: Optional[str] = None


@dataclass
class Refaktoreringsinfo:
    """Holder informasjon om anbefalt refaktorering."""

    anbefalt_plassering: str
    begrunnelse: str
    prioritet: Prioritet
    kompleksitet: str  # Enkel/Medium/Kompleks


def er_problem_dict(p: Any) -> bool:
    """Sjekker om et objekt er et gyldig Problem-dict.
    Args:
        p: Objektet som skal sjekkes
    Returns:
        bool: True hvis objektet er et gyldig Problem-dict, False ellers
    """
    er_gyldig_linje = (
        "linje" not in p or p["linje"] is None or isinstance(p["linje"], int)
    )
    er_gyldig_alvorlighet = (
        "alvorlighet" not in p
        or p["alvorlighet"] is None
        or isinstance(p["alvorlighet"], str)
    )
    return (
        isinstance(p, dict)
        and "fil" in p
        and isinstance(p["fil"], str)
        and "type" in p
        and isinstance(p["type"], str)
        and "melding" in p
        and isinstance(p["melding"], str)
        and er_gyldig_linje
        and er_gyldig_alvorlighet
    )


def problem_fra_dict(p: Dict[str, Any]) -> Problem:
    """
    Konverterer et dictionary til et Problem-objekt.

    Args:
        p: Dictionary med problem-data

    Returns:
        Problem: Et Problem-objekt
    """
    return Problem(
        fil=p["fil"],
        type=p["type"],
        melding=p["melding"],
        linje=p.get("linje"),
        alvorlighet=p.get("alvorlighet"),
    )


def les_python_fil(filsti: str) -> Optional[ast.Module]:
    """
    Leser og parser en Python-fil.

    Args:
        filsti: Sti til filen som skal leses

    Returns:
        Optional[ast.Module]: AST for filen hvis parsing var vellykket, None ellers
    """
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            innhold = f.read()
        return ast.parse(innhold, filename=filsti)
    except (IOError, SyntaxError) as e:
        logger.error("Kunne ikke lese/parse %s: %s", filsti, e)
        return None


def er_delegering(node: ast.FunctionDef) -> Tuple[bool, Optional[str]]:
    """Sjekker om en funksjon delegerer til en annen implementasjon.
    Args:
        node: Funksjonsdefinisjonen som skal sjekkes
    Returns:
        Tuple[bool, Optional[str]]: (True, detaljer) hvis delegerer,
                                   (False, None) ellers
    """

    def sjekk_delegering(call: ast.Call) -> Tuple[bool, Optional[str]]:
        if isinstance(call.func, ast.Attribute):
            try:
                if isinstance(call.func.value, ast.Attribute):
                    if isinstance(call.func.value.value, ast.Name):
                        base = f"{call.func.value.value.id}.{call.func.value.attr}"
                        return True, f"Delegerer via {base}.{call.func.attr}"
                if isinstance(call.func.value, ast.Name):
                    base = call.func.value.id
                    return True, f"Delegerer via {base}.{call.func.attr}"
            except AttributeError:
                pass
        elif isinstance(call.func, ast.Name):
            return True, f"Delegerer til {call.func.id}"
        return False, None

    if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return False, None

    return_value = node.body[0].value
    if not isinstance(return_value, ast.Call):
        return False, None

    return sjekk_delegering(return_value)


def analyser_fil(filsti: str) -> List[FunksjonInfo]:
    """Analyserer en fil for å finne funksjoner.
    Args:
        filsti: Sti til filen som skal analyseres
    Returns:
        List[FunksjonInfo]: Liste med informasjon om funksjonene i filen
    """
    tre = les_python_fil(filsti)
    if not tre:
        return []
    funksjoner = []
    for node in ast.walk(tre):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                continue
            er_deleg, deleg_info = er_delegering(node)
            if any(
                pattern in node.name.lower()
                for pattern in [
                    "hent_",
                    "get_",
                    "update_",
                    "oppdater_",
                    "lagre_",
                    "save_",
                    "delete_",
                    "slett_",
                ]
            ):
                logger.warning(
                    "Potensiell duplisert funksjon: %s i %s", node.name, filsti
                )
            funk_type = FunksjonType.DELEGERING if er_deleg else FunksjonType.NORMAL
            funksjoner.append(
                FunksjonInfo(
                    filsti=filsti,
                    navn=node.name,
                    type=funk_type,
                    linjenummer=node.lineno,
                    detaljer=deleg_info if er_deleg else None,
                )
            )
    return funksjoner


def finn_dupliserte_funksjoner(src_mappe: str) -> None:
    """Finner dupliserte funksjoner i kildekoden.
    Args:
        src_mappe: Sti til kildekode-mappen som skal analyseres
    """

    def finn_python_filer() -> List[str]:
        filer = []
        for root, _, files in os.walk(src_mappe):
            for fil in files:
                if fil.endswith(".py") and not fil.startswith("_"):
                    filer.append(os.path.join(root, fil))
        return filer

    def grupper_funksjoner(filer: List[str]) -> Dict[str, List[FunksjonInfo]]:
        funksjoner: Dict[str, List[FunksjonInfo]] = {}
        for filsti in filer:
            for funksjon in analyser_fil(filsti):
                if funksjon.navn not in funksjoner:
                    funksjoner[funksjon.navn] = []
                funksjoner[funksjon.navn].append(funksjon)
        return funksjoner

    def finn_duplikater(
        funksjoner: Dict[str, List[FunksjonInfo]],
    ) -> Dict[str, List[FunksjonInfo]]:
        return {
            navn: forekomster
            for navn, forekomster in funksjoner.items()
            if len([f for f in forekomster if f.type != FunksjonType.DELEGERING]) > 1
        }

    def skriv_rapport(duplikater: Dict[str, List[FunksjonInfo]]) -> None:
        if not duplikater:
            logger.info("Ingen dupliserte funksjoner funnet")
            return
        print("\nFunnet følgende dupliserte funksjoner:")
        print("=" * 50)
        for navn, forekomster in duplikater.items():
            print(f"\n{navn}:")
            implementasjoner = [
                f for f in forekomster if f.type != FunksjonType.DELEGERING
            ]
            delegeringer = [f for f in forekomster if f.type == FunksjonType.DELEGERING]
            print("  Implementasjoner:")
            for impl in implementasjoner:
                print(f"  - {impl.filsti}:{impl.linjenummer}")
            if delegeringer:
                print("  Delegeringer:")
                for deleg in delegeringer:
                    print(f"  - {deleg.filsti}:{deleg.linjenummer} ({deleg.detaljer})")
            print("-" * 50)

    logger.info("Søker etter dupliserte funksjoner i %s", src_mappe)
    python_filer = finn_python_filer()
    logger.info("Fant %d Python-filer", len(python_filer))
    funksjoner = grupper_funksjoner(python_filer)
    duplikater = finn_duplikater(funksjoner)
    skriv_rapport(duplikater)


def sjekk_ide_problemer(filsti: str) -> List[Dict[str, Any]]:
    """Sjekker IDE-relaterte problemer.
    Args:
        filsti: Sti til mappen som skal sjekkes
    Returns:
        List[Dict[str, Any]]: Liste med problemer funnet
    """

    def finn_imports(tre: ast.Module) -> set:
        imports = set()
        for node in ast.walk(tre):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name)
            elif isinstance(node, ast.ImportFrom):
                for n in node.names:
                    imports.add(n.name)
        return imports

    def er_import_brukt(tre: ast.Module, imp: str) -> bool:
        for node in ast.walk(tre):
            if isinstance(node, ast.Name) and node.id == imp:
                return True
        return False

    logger.info("Sjekker IDE-problemer i %s", filsti)
    ide_problemer = []
    for root, _, files in os.walk(filsti):
        for fil in files:
            if not fil.endswith(".py"):
                continue
            full_sti = os.path.join(root, fil)
            tre = les_python_fil(full_sti)
            if not tre:
                continue
            imports = finn_imports(tre)
            for imp in imports:
                if not er_import_brukt(tre, imp):
                    ide_problemer.append(
                        {
                            "fil": full_sti,
                            "type": "UBRUKT_IMPORT",
                            "melding": f"Ubrukt import: {imp}",
                            "linje": None,
                            "alvorlighet": "INFO",
                        }
                    )
    return ide_problemer


def sjekk_filplassering(filsti: str) -> List[Dict[str, Any]]:
    """Sjekker filplassering.
    Args:
        filsti: Sti til mappen som skal sjekkes
    Returns:
        List[Dict[str, Any]]: Liste med problemer funnet
    """

    def les_filinnhold(full_sti: str) -> Optional[str]:
        try:
            with open(full_sti, "r", encoding="utf-8") as f:
                return f.read()
        except IOError:
            return None

    def sjekk_kategori_plassering(
        innhold: str, rel_sti: str, kategori: str, mapper: List[str]
    ) -> Optional[Dict[str, Any]]:
        if any(term in innhold.lower() for term in [kategori, f"{kategori}_"]):
            if not any(rel_sti.startswith(mappe) for mappe in mapper):
                return {
                    "fil": rel_sti,
                    "type": "FEIL_PLASSERING",
                    "melding": (
                        f"{kategori}-relatert fil bør ligge i "
                        f"{' eller '.join(mapper)}"
                    ),
                    "linje": None,
                    "alvorlighet": "ADVARSEL",
                }
        return None

    logger.info("Sjekker filplassering i %s", filsti)
    feil_liste = []
    forventede_mapper = {
        "database": ["database/", "models/", "repositories/"],
        "view": ["pages/", "views/", "templates/"],
        "utils": ["utils/", "helpers/"],
        "auth": ["auth/", "security/"],
    }

    for root, _, files in os.walk(filsti):
        for fil in files:
            if not fil.endswith(".py"):
                continue
            full_sti = os.path.join(root, fil)
            rel_sti = os.path.relpath(full_sti, filsti)
            innhold = les_filinnhold(full_sti)
            if not innhold:
                continue

            for kategori, mapper in forventede_mapper.items():
                feil = sjekk_kategori_plassering(innhold, rel_sti, kategori, mapper)
                if feil:
                    feil_liste.append(feil)

    return feil_liste


def skriv_problemer(problemer: List[Problem]) -> None:
    """
    Skriver ut problemer i en ryddig format.

    Args:
        problemer: Liste med problemer som skal skrives ut
    """
    if not problemer:
        print("Ingen problemer funnet")
        return

    # Grupper problemer etter fil
    problemer_per_fil: Dict[str, List[Problem]] = {}
    for p in problemer:
        fil = p.fil  # Bruk attributt-tilgang siden Problem er en dataclass
        if fil not in problemer_per_fil:
            problemer_per_fil[fil] = []
        problemer_per_fil[fil].append(p)

    # Skriv ut problemer gruppert etter fil
    for fil, fil_problemer in sorted(problemer_per_fil.items()):
        print(f"\n{fil}:")
        # Sorter problemer etter linjenummer, håndter None-verdier
        sorterte_problemer = sorted(
            fil_problemer,
            key=lambda x: x.linje or float("inf"),  # Bruk attributt-tilgang
        )
        for p in sorterte_problemer:
            linje_info = f" (linje {p.linje})" if p.linje is not None else ""
            alvorlighet = f"[{p.alvorlighet}]" if p.alvorlighet else ""
            print(f"  {alvorlighet} {p.type}{linje_info} - {p.melding}")


if __name__ == "__main__":
    finn_dupliserte_funksjoner("src/")

    print("\nProblemer funnet i kodebasen:")
    print("=" * 50)

    # Samle problemer og konverter til Problem-objekter
    problemer: List[Dict[str, Any]] = []
    problemer.extend(sjekk_ide_problemer("src/"))
    problemer.extend(sjekk_filplassering("src/"))

    # Konverter til Problem-objekter
    alle_problemer: List[Problem] = [
        problem_fra_dict(p) if er_problem_dict(p) else Problem(**p) for p in problemer
    ]
    skriv_problemer(alle_problemer)
