#!/usr/bin/env python3
"""
Script for å analysere bruken av session state i kodebasen.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import ast
from dataclasses import dataclass
import logging
import importlib.util

# Legg til prosjektroten i Python-stien
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def import_session_state_module(project_root: Path) -> Optional[Dict]:
    """Importerer session_state modulen for å få tilgang til
    VALID_SESSION_KEYS"""
    try:
        module_path = project_root / "src" / "min_kamp" / "utils" / "session_state.py"
        if not module_path.exists():
            logger.warning(f"Finner ikke session_state.py på {module_path}")
            return None

        spec = importlib.util.spec_from_file_location("session_state", module_path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "VALID_SESSION_KEYS", {})
    except Exception as e:
        logger.warning(f"Kunne ikke importere VALID_SESSION_KEYS: {e}")
        return None


@dataclass
class SessionStateUsage:
    filename: str
    reads: Set[str]
    writes: Set[str]
    line_numbers: Dict[str, List[int]]
    potential_issues: List[Tuple[int, str]]
    invalid_keys: Set[str]


class SessionStateVisitor(ast.NodeVisitor):
    def __init__(self, valid_keys: Optional[Dict] = None):
        self.reads = set()
        self.writes = set()
        self.line_numbers = {}
        self.potential_issues = []
        self.valid_keys = valid_keys or {}
        self.invalid_keys = set()
        self.current_function = None

    def visit_FunctionDef(self, node):
        """Holder styr på hvilken funksjon vi er i"""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Attribute(self, node):
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "st"
            and node.attr == "session_state"
            and not (self.current_function and self.current_function.startswith("_"))
        ):
            msg = "Direkte aksess til session_state uten sjekk"
            self.potential_issues.append((node.lineno, msg))
        self.generic_visit(node)

    def visit_Call(self, node):
        """Sjekker etter kall til get_session_state og set_session_state"""
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in ["get_session_state", "set_session_state"]
            and node.args
        ):
            # Prøv å hente ut nøkkelen hvis den er en streng-konstant
            if isinstance(node.args[0], ast.Constant) and isinstance(
                node.args[0].value, str
            ):
                key = node.args[0].value
                if key not in self.valid_keys:
                    self.invalid_keys.add(key)
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if (
            isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "st"
            and node.value.attr == "session_state"
            and not (self.current_function and self.current_function.startswith("_"))
        ):
            key = None
            if isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif isinstance(node.slice, ast.Str):
                key = node.slice.s

            if key:
                if isinstance(node.ctx, ast.Load):
                    self.reads.add(key)
                elif isinstance(node.ctx, ast.Store):
                    self.writes.add(key)

                if key not in self.line_numbers:
                    self.line_numbers[key] = []
                self.line_numbers[key].append(node.lineno)

                # Sjekk om nøkkelen er gyldig
                if key not in self.valid_keys:
                    self.invalid_keys.add(key)

        self.generic_visit(node)


def analyze_file(
    file_path: Path, valid_keys: Optional[Dict] = None
) -> Optional[SessionStateUsage]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        visitor = SessionStateVisitor(valid_keys)
        visitor.visit(tree)

        return SessionStateUsage(
            filename=str(file_path),
            reads=visitor.reads,
            writes=visitor.writes,
            line_numbers=visitor.line_numbers,
            potential_issues=visitor.potential_issues,
            invalid_keys=visitor.invalid_keys,
        )
    except Exception as e:
        logger.error(f"Feil ved analysering av {file_path}: {e}")
        return None


def find_python_files(start_path: Path) -> List[Path]:
    python_files = []
    for root, _, files in os.walk(start_path):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files


def analyze_codebase(project_root: Path) -> List[SessionStateUsage]:
    valid_keys = import_session_state_module(project_root)
    if valid_keys:
        logger.info(f"Fant {len(valid_keys)} gyldige session state nøkler")
    else:
        logger.warning("Kunne ikke laste gyldige session state nøkler")

    results = []
    for file_path in find_python_files(project_root):
        if result := analyze_file(file_path, valid_keys):
            results.append(result)
    return results


def print_analysis_results(results: List[SessionStateUsage]):
    print("\n=== Session State Analyse ===\n")

    all_keys = set()
    invalid_keys = set()
    for result in results:
        all_keys.update(result.reads)
        all_keys.update(result.writes)
        invalid_keys.update(result.invalid_keys)

    if invalid_keys:
        print("Ugyldige session state nøkler funnet:")
        for key in sorted(invalid_keys):
            print(f"\n{key}:")
            for result in results:
                if key in result.invalid_keys:
                    print(f"  {result.filename}")
        print("\n")

    if all_keys:
        print("Nøkler i session state:")
        for key in sorted(all_keys):
            print(f"\n{key}:")
            for result in results:
                if key in result.reads or key in result.writes:
                    operations = []
                    if key in result.reads:
                        operations.append("lest")
                    if key in result.writes:
                        operations.append("skrevet")
                    line_numbers = result.line_numbers.get(key, [])
                    line_nums = ", ".join(map(str, line_numbers))
                    print(
                        f"  {result.filename}: {', '.join(operations)} "
                        f"(linje {line_nums})"
                    )

    has_issues = False
    for result in results:
        if result.potential_issues:
            if not has_issues:
                print("\nPotensielle problemer:")
                has_issues = True
            print(f"\n{result.filename}:")
            for line_no, issue in result.potential_issues:
                print(f"  Linje {line_no}: {issue}")


def main():
    try:
        project_root = Path(__file__).parent.parent
        logger.info(f"Analyserer kodebase: {project_root}")
        results = analyze_codebase(project_root)
        print_analysis_results(results)

    except Exception as e:
        logger.error(f"Feil: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
