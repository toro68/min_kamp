#!/usr/bin/env python3
"""
Analyseverktøy for å sjekke og utbedre bytteplansystemet.

Dette scriptet analyserer:
1. Bytteplanlogikk og -validering
2. Spilletidsfordeling
3. Periodeoverganger
4. Posisjonshåndtering
5. Feilhåndtering og logging
"""

import ast
import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Logging oppsett
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rich console oppsett
console = Console()


class BytteplanProblemType(Enum):
    """Definerer ulike typer problemer i bytteplansystemet."""

    UBALANSERT_SPILLETID = auto()
    UGYLDIG_BYTTE = auto()
    MANGLENDE_VALIDERING = auto()
    INEFFEKTIV_PERIODEOVERGANG = auto()
    POSISJONSUBALANSE = auto()
    MANGLENDE_FEILHÅNDTERING = auto()
    DÅRLIG_LOGGING = auto()


@dataclass
class BytteplanProblem:
    """Representerer et problem funnet i bytteplansystemet."""

    fil: str
    type: BytteplanProblemType
    melding: str
    kode: Optional[str] = None
    linje: Optional[int] = None
    alvorlighet: str = "MEDIUM"


class BytteplanAnalyzer(ast.NodeVisitor):
    """Analyserer Python AST for bytteplan-relaterte problemer."""

    def __init__(self) -> None:
        self.problemer: List[BytteplanProblem] = []
        self.current_file = ""
        self.validering_funnet = False
        self.spilletid_sjekk_funnet = False
        self.posisjon_sjekk_funnet = False
        self.feilhåndtering_funnet = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyserer funksjonsdefinisjoner."""
        # Sjekk for valideringsfunksjoner
        if any(val in node.name.lower() for val in ["valider", "sjekk", "verify"]):
            self.validering_funnet = True
            self._analyser_validering(node)

        # Sjekk for spilletidshåndtering
        if any(tid in node.name.lower() for tid in ["spilletid", "byttetid", "time"]):
            self.spilletid_sjekk_funnet = True
            self._analyser_spilletid(node)

        # Sjekk for posisjonshåndtering
        if any(
            pos in node.name.lower() for pos in ["posisjon", "stilling", "position"]
        ):
            self.posisjon_sjekk_funnet = True
            self._analyser_posisjoner(node)

        self.generic_visit(node)

    def _analyser_validering(self, node: ast.FunctionDef) -> None:
        """Analyserer valideringsfunksjoner."""
        har_feilhåndtering = False
        har_logging = False

        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                har_feilhåndtering = True
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if "log" in child.func.attr:
                        har_logging = True

        if not har_feilhåndtering:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.MANGLENDE_FEILHÅNDTERING,
                    melding=f"Manglende feilhåndtering i valideringsfunksjon {node.name}",
                    linje=node.lineno,
                )
            )

        if not har_logging:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.DÅRLIG_LOGGING,
                    melding=f"Manglende logging i valideringsfunksjon {node.name}",
                    linje=node.lineno,
                )
            )

    def _analyser_spilletid(self, node: ast.FunctionDef) -> None:
        """Analyserer spilletidshåndtering."""
        har_balansering = False
        har_grenseverdier = False

        for child in ast.walk(node):
            if isinstance(child, ast.Compare):
                har_grenseverdier = True
            elif isinstance(child, ast.BinOp):
                har_balansering = True

        if not har_balansering:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.UBALANSERT_SPILLETID,
                    melding=f"Manglende spilletidsbalansering i {node.name}",
                    linje=node.lineno,
                )
            )

        if not har_grenseverdier:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.MANGLENDE_VALIDERING,
                    melding=f"Manglende grenseverdier for spilletid i {node.name}",
                    linje=node.lineno,
                )
            )

    def _analyser_posisjoner(self, node: ast.FunctionDef) -> None:
        """Analyserer posisjonshåndtering."""
        har_posisjonsjekk = False
        har_balansesjekk = False

        for child in ast.walk(node):
            if isinstance(child, ast.Dict):
                har_posisjonsjekk = True
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if "balanse" in child.func.id.lower():
                        har_balansesjekk = True

        if not har_posisjonsjekk:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.POSISJONSUBALANSE,
                    melding=f"Manglende posisjonshåndtering i {node.name}",
                    linje=node.lineno,
                )
            )

        if not har_balansesjekk:
            self.problemer.append(
                BytteplanProblem(
                    fil=self.current_file,
                    type=BytteplanProblemType.POSISJONSUBALANSE,
                    melding=f"Manglende posisjonsbalansering i {node.name}",
                    linje=node.lineno,
                )
            )


def analyser_python_fil(filsti: str) -> List[BytteplanProblem]:
    """Analyserer en Python-fil for bytteplan-relaterte problemer."""
    problemer = []
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            tre = ast.parse(f.read(), filename=filsti)

        analyzer = BytteplanAnalyzer()
        analyzer.current_file = filsti
        analyzer.visit(tre)
        problemer.extend(analyzer.problemer)

        if not analyzer.validering_funnet:
            problemer.append(
                BytteplanProblem(
                    fil=filsti,
                    type=BytteplanProblemType.MANGLENDE_VALIDERING,
                    melding="Mangler dedikert valideringsfunksjonalitet",
                    alvorlighet="HIGH",
                )
            )

        if not analyzer.spilletid_sjekk_funnet:
            problemer.append(
                BytteplanProblem(
                    fil=filsti,
                    type=BytteplanProblemType.UBALANSERT_SPILLETID,
                    melding="Mangler dedikert spilletidshåndtering",
                    alvorlighet="HIGH",
                )
            )

    except Exception as e:
        logger.error(f"Feil ved analyse av {filsti}: {e}")

    return problemer


def vis_problemer_tabell(problemer: List[BytteplanProblem]) -> None:
    """Viser problemer i en pen tabell."""
    for alvorlighet in ["HIGH", "MEDIUM", "LOW"]:
        relevante_problemer = [p for p in problemer if p.alvorlighet == alvorlighet]
        if not relevante_problemer:
            continue

        table = Table(
            title=f"🚨 {alvorlighet} Prioritet ({len(relevante_problemer)} problemer)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Fil", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Problem", style="white")
        table.add_column("Linje", justify="right", style="green")

        for problem in relevante_problemer:
            table.add_row(
                os.path.basename(problem.fil),
                problem.type.name,
                problem.melding,
                str(problem.linje) if problem.linje else "-",
            )

        console.print(table)
        console.print()


def vis_forbedringsforslag(problemer: List[BytteplanProblem]) -> None:
    """Viser forbedringsforslag i pene paneler."""
    console.print("\n[bold cyan]Forbedringsforslag for bytteplansystemet:[/]\n")

    problemer_per_type: Dict[BytteplanProblemType, List[BytteplanProblem]] = {}
    for problem in problemer:
        if problem.type not in problemer_per_type:
            problemer_per_type[problem.type] = []
        problemer_per_type[problem.type].append(problem)

    if BytteplanProblemType.UBALANSERT_SPILLETID in problemer_per_type:
        panel = Panel.fit(
            "• Implementer algoritme for rettferdig fordeling av spilletid\n"
            "• Legg til minimum/maksimum spilletid per spiller\n"
            "• Implementer varsling ved ubalansert spilletid",
            title="[yellow]1. Spilletidsbalansering[/]",
            border_style="yellow",
        )
        console.print(panel)

    if BytteplanProblemType.MANGLENDE_VALIDERING in problemer_per_type:
        panel = Panel.fit(
            "• Legg til omfattende byttevalidering\n"
            "• Implementer sjekk av posisjonskrav\n"
            "• Valider spilletidsregler",
            title="[green]2. Valideringsforbedringer[/]",
            border_style="green",
        )
        console.print(panel)

    if BytteplanProblemType.POSISJONSUBALANSE in problemer_per_type:
        panel = Panel.fit(
            "• Implementer posisjonssporing\n"
            "• Legg til validering av posisjonsdekning\n"
            "• Varsle ved ubalanserte formasjoner",
            title="[blue]3. Posisjonshåndtering[/]",
            border_style="blue",
        )
        console.print(panel)

    if BytteplanProblemType.MANGLENDE_FEILHÅNDTERING in problemer_per_type:
        panel = Panel.fit(
            "• Legg til omfattende feilhåndtering\n"
            "• Implementer bedre feilmeldinger\n"
            "• Logg alle kritiske operasjoner",
            title="[red]4. Feilhåndtering[/]",
            border_style="red",
        )
        console.print(panel)


def vis_kodeeksempler() -> None:
    """Viser kodeeksempler i pene paneler."""
    console.print("\n[bold cyan]Foreslåtte kodeendringer:[/]\n")

    validator_kode = """
class BytteplanValidator:
    def valider_bytte(self, spiller_id: int, inn_tid: int, ut_tid: Optional[int]) -> bool:
        # Implementer validering
        pass

    def valider_spilletid(self, spilletider: Dict[int, int]) -> bool:
        # Implementer spilletidsvalidering
        pass

    def valider_posisjoner(self, bytteplan: Dict[str, Any]) -> bool:
        # Implementer posisjonsvalidering
        pass
"""

    balanserer_kode = """
class SpilletidBalanserer:
    def balanser_spilletid(self, bytteplan: Dict[str, Any]) -> Dict[str, Any]:
        # Implementer balansering
        pass

    def beregn_optimal_fordeling(self, antall_spillere: int, total_tid: int) -> Dict[int, int]:
        # Implementer optimal fordeling
        pass
"""

    feilhaandtering_kode = """
try:
    with self.transaction():
        # Eksisterende kode
        if not self.validator.valider_bytte(spiller_id, inn_tid, ut_tid):
            raise ValueError("Ugyldig bytte")
        # Mer kode
except Exception as e:
    logger.error("Feil ved bytteregistrering: %s", e)
    raise BytteplanError("Kunne ikke registrere bytte") from e
"""

    console.print(
        Panel(
            validator_kode,
            title="[yellow]1. Ny valideringsklasse[/]",
            border_style="yellow",
        )
    )
    console.print(
        Panel(
            balanserer_kode,
            title="[green]2. Spilletidsbalansering[/]",
            border_style="green",
        )
    )
    console.print(
        Panel(
            feilhaandtering_kode,
            title="[red]3. Forbedret feilhåndtering[/]",
            border_style="red",
        )
    )


def main() -> None:
    """Hovedfunksjon som kjører analysene."""
    console.print("[bold cyan]Analyserer bytteplansystemet...[/]\n")

    problemer: List[BytteplanProblem] = []
    for root, _, files in os.walk("src"):
        for fil in files:
            if fil.endswith(".py") and "bytteplan" in fil.lower():
                filsti = os.path.join(root, fil)
                problemer.extend(analyser_python_fil(filsti))

    if not problemer:
        console.print("[green]Ingen problemer funnet! 🎉[/]")
        return

    console.print("[bold red]Problemer funnet i bytteplansystemet:[/]\n")
    vis_problemer_tabell(problemer)
    vis_forbedringsforslag(problemer)
    vis_kodeeksempler()


if __name__ == "__main__":
    main()
