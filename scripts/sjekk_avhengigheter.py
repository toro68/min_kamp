#!/usr/bin/env python3
"""
Analyseverktøy for å sjekke prosjektavhengigheter.

Dette scriptet analyserer:
1. Importerte moduler og deres bruk
2. Sykliske avhengigheter
3. Utdaterte pakker
4. Ubrukte importerte moduler
5. Versjonskonflikter
6. Manglende eksporterte funksjoner
"""

import ast
import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set
import pkg_resources
import requests
from packaging import version

# Logging oppsett
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AvhengighetType(Enum):
    """Definerer ulike typer avhengigetsproblemer."""

    UBRUKT_IMPORT = auto()
    SYKLISK_AVHENGIGHET = auto()
    UTDATERT_PAKKE = auto()
    VERSJON_KONFLIKT = auto()
    MANGLENDE_VERSJON = auto()
    MANGLENDE_FUNKSJON = auto()


@dataclass
class Avhengighet:
    """Representerer en avhengighet i prosjektet."""

    navn: str
    versjon: Optional[str] = None
    sist_versjon: Optional[str] = None
    brukt_i: Optional[List[str]] = None


@dataclass
class AvhengighetProblem:
    """Representerer et problem med en avhengighet."""

    type: AvhengighetType
    pakke: str
    melding: str
    detaljer: Optional[str] = None
    alvorlighet: str = "MEDIUM"


class ImportAnalyzer(ast.NodeVisitor):
    """Analyserer Python AST for imports."""

    def __init__(self) -> None:
        # modul -> filer som importerer den
        self.imports: Dict[str, Set[str]] = {}
        self.used_names: Set[str] = set()  # brukte importerte navn
        self.current_file = ""
        # definerte funksjoner i filen
        self.defined_functions: Set[str] = set()
        # fil -> eksporterte navn
        self.exported_names: Dict[str, Set[str]] = {}
        self.imported_names: Dict[str, Set[str]] = {}  # fil -> importerte navn

    def visit_Import(self, node: ast.Import) -> None:
        """Besøker import-statements."""
        for alias in node.names:
            if alias.name not in self.imports:
                self.imports[alias.name] = set()
            self.imports[alias.name].add(self.current_file)

            # Logg importert navn
            if self.current_file not in self.imported_names:
                self.imported_names[self.current_file] = set()
            self.imported_names[self.current_file].add(alias.asname or alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Besøker from-import statements."""
        if node.module:
            module_path = node.module
            if module_path not in self.imports:
                self.imports[module_path] = set()
            self.imports[module_path].add(self.current_file)

            # Logg importerte navn
            if self.current_file not in self.imported_names:
                self.imported_names[self.current_file] = set()

            for alias in node.names:
                full_name = f"{module_path}.{alias.name}"
                if full_name not in self.imports:
                    self.imports[full_name] = set()
                self.imports[full_name].add(self.current_file)
                self.imported_names[self.current_file].add(alias.asname or alias.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Besøker funksjonsdefinisjoner."""
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Besøker navn/variabler."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Besøker tilordninger, inkludert __all__."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    self.exported_names[self.current_file] = {
                        s.value for s in node.value.elts if isinstance(s, ast.Str)
                    }
                    # Sjekk at alle eksporterte navn er enten definert eller
                    # importert
                    for navn in self.exported_names[self.current_file]:
                        if (
                            navn not in self.defined_functions
                            and self.current_file in self.imported_names
                            and navn not in self.imported_names[self.current_file]
                        ):
                            logger.warning(
                                f"Fil {self.current_file} eksporterer '{navn}' "
                                f"som hverken er definert eller importert"
                            )
        self.generic_visit(node)


def finn_sykliske_avhengigheter(imports: Dict[str, Set[str]]) -> List[List[str]]:
    """Finner sykliske avhengigheter i importhierarkiet.

    Args:
        imports: Dictionary med imports og deres brukssteder

    Returns:
        Liste med sykliske avhengighetskjeder
    """

    def finn_sykler(node: str, visited: Set[str], path: List[str]) -> List[List[str]]:
        if node in visited:
            start = path.index(node)
            return [path[start:]]
        visited.add(node)
        path.append(node)
        sykler = []
        for imp in imports.get(node, set()):
            if os.path.isfile(imp):  # Sjekk bare filer, ikke eksterne pakker
                sykler.extend(finn_sykler(imp, visited.copy(), path.copy()))
        return sykler

    sykler = []
    for node in imports:
        if os.path.isfile(node):  # Start bare fra faktiske filer
            sykler.extend(finn_sykler(node, set(), []))
    return sykler


def sjekk_eksporterte_funksjoner(
    analyzer: ImportAnalyzer,
) -> List[AvhengighetProblem]:
    """Sjekker at alle eksporterte funksjoner faktisk er definert eller importert.

    Args:
        analyzer: ImportAnalyzer-instansen med analysert kode

    Returns:
        Liste med problemer relatert til manglende funksjoner
    """
    problemer = []

    for fil, eksporterte in analyzer.exported_names.items():
        for funksjon in eksporterte:
            if (
                funksjon not in analyzer.defined_functions
                and funksjon not in analyzer.used_names
            ):
                problemer.append(
                    AvhengighetProblem(
                        type=AvhengighetType.MANGLENDE_FUNKSJON,
                        pakke=funksjon,
                        melding=f"Eksportert funksjon '{funksjon}' er ikke definert eller importert i {fil}",
                        alvorlighet="HIGH",
                    )
                )

    return problemer


def sjekk_pakkeversjoner(requirements_fil: str) -> List[AvhengighetProblem]:
    """Sjekker pakkeversjonene mot PyPI.

    Args:
        requirements_fil: Sti til requirements.txt

    Returns:
        Liste med versjonsproblemer
    """
    problemer = []

    try:
        with open(requirements_fil, "r") as f:
            krav_liste = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        logger.warning(f"Fant ikke {requirements_fil}")
        return problemer

    for krav_linje in krav_liste:
        try:
            pakke = pkg_resources.Requirement.parse(krav_linje)
            pakkenavn = pakke.project_name

            # Sjekk siste versjon fra PyPI
            try:
                respons = requests.get(f"https://pypi.org/pypi/{pakkenavn}/json")
                if respons.status_code == 200:
                    data = respons.json()
                    sist_versjon = data["info"]["version"]

                    # Sammenlign versjoner
                    if version.parse(sist_versjon) > version.parse(
                        list(pakke.specs)[0][1]
                    ):
                        problemer.append(
                            AvhengighetProblem(
                                type=AvhengighetType.UTDATERT_PAKKE,
                                pakke=pakkenavn,
                                melding=f"Utdatert versjon: {list(pakke.specs)[0][1]} (siste: {sist_versjon})",
                                alvorlighet="LOW",
                            )
                        )
            except Exception as e:
                logger.warning(f"Kunne ikke sjekke versjon for {pakkenavn}: {e}")

        except Exception as e:
            logger.warning(f"Kunne ikke parse krav '{krav_linje}': {e}")

    return problemer


def analyser_python_fil(
    filsti: str, analyzer: ImportAnalyzer
) -> List[AvhengighetProblem]:
    """Analyserer en Python-fil for avhengighetsproblemer.

    Args:
        filsti: Sti til filen som skal analyseres
        analyzer: ImportAnalyzer-instansen som brukes

    Returns:
        Liste med avhengighetsproblemer
    """
    problemer = []
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            tre = ast.parse(f.read(), filename=filsti)

        analyzer.current_file = filsti
        analyzer.visit(tre)

    except Exception as e:
        logger.error(f"Feil ved analyse av {filsti}: {e}")

    return problemer


def lag_oppryddingsplan(problemer: List[AvhengighetProblem]) -> None:
    """Lager en plan for opprydding av avhengighetsproblemer.

    Args:
        problemer: Liste med avhengighetsproblemer
    """
    # Grupper problemer etter filsti
    problemer_per_fil: Dict[str, List[AvhengighetProblem]] = {}
    for problem in problemer:
        if problem.type == AvhengighetType.UBRUKT_IMPORT:
            for filsti in problem.melding.split(", "):
                if filsti not in problemer_per_fil:
                    problemer_per_fil[filsti] = []
                problemer_per_fil[filsti].append(problem)

    print("\nOppryddingsplan:")
    print("=" * 80)
    print("\n1. Utdaterte pakker som bør oppdateres:")
    print("-" * 40)

    for problem in problemer:
        if problem.type == AvhengighetType.UTDATERT_PAKKE:
            print(f"- {problem.pakke}: {problem.melding}")

    print("\n2. Filer som trenger opprydding i imports:")
    print("-" * 40)

    for filsti, fil_problemer in sorted(problemer_per_fil.items()):
        print(f"\n{filsti}:")
        for problem in fil_problemer:
            if "." in problem.pakke:  # Intern modul
                print(f"  - Fjern import av intern modul: {problem.pakke}")
            else:  # Ekstern pakke
                print(f"  - Fjern ubrukt import: {problem.pakke}")

    print("\n3. Foreslåtte kommandoer:")
    print("-" * 40)
    print("# Oppdater pakker:")
    print("pip install --upgrade streamlit pandas openpyxl python-dotenv")
    print("\n# Frys nye versjoner:")
    print("pip freeze > requirements.txt")
    print("\n# Kjør autoflake for å fjerne ubrukte imports:")
    print("pip install autoflake")
    print(
        "find src -name '*.py' -exec autoflake --in-place --remove-all-unused-imports {} +"
    )


def main() -> None:
    """Hovedfunksjon som kjører analysene."""
    analyzer = ImportAnalyzer()
    problemer: List[AvhengighetProblem] = []

    # Analyser Python-filer
    for root, _, files in os.walk("src"):
        for fil in files:
            if fil.endswith(".py"):
                filsti = os.path.join(root, fil)
                problemer.extend(analyser_python_fil(filsti, analyzer))

    # Finn ubrukte imports
    for imp, filer in analyzer.imports.items():
        if not any(name in analyzer.used_names for name in imp.split(".")):
            problemer.append(
                AvhengighetProblem(
                    type=AvhengighetType.UBRUKT_IMPORT,
                    pakke=imp,
                    melding=", ".join(filer),
                    alvorlighet="LOW",
                )
            )

    # Finn sykliske avhengigheter
    sykler = finn_sykliske_avhengigheter(analyzer.imports)
    for sykel in sykler:
        problemer.append(
            AvhengighetProblem(
                type=AvhengighetType.SYKLISK_AVHENGIGHET,
                pakke=" -> ".join(sykel),
                melding="Syklisk avhengighet funnet",
                alvorlighet="HIGH",
            )
        )

    # Sjekk pakkeversjoner
    if os.path.exists("requirements.txt"):
        problemer.extend(sjekk_pakkeversjoner("requirements.txt"))

    # Sjekk eksporterte funksjoner
    problemer.extend(sjekk_eksporterte_funksjoner(analyzer))

    # Skriv ut problemer gruppert etter alvorlighet
    alvorligheter = ["HIGH", "MEDIUM", "LOW"]

    print("\nFunnet følgende problemer:")
    print("=" * 80)

    for alvorlighet in alvorligheter:
        relevante_problemer = [p for p in problemer if p.alvorlighet == alvorlighet]
        if relevante_problemer:
            print(f"\n{alvorlighet} Priority ({len(relevante_problemer)} problemer):")
            print("-" * 40)

            for problem in relevante_problemer:
                print(f"\nType: {problem.type.name}")
                print(f"Pakke: {problem.pakke}")
                print(f"Problem: {problem.melding}")
                if problem.detaljer:
                    print(f"Detaljer: {problem.detaljer}")
                print("-" * 40)

    # Lag oppryddingsplan
    lag_oppryddingsplan(problemer)


if __name__ == "__main__":
    main()
