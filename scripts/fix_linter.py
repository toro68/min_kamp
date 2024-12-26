#!/usr/bin/env python3

"""
Script for å analysere og fikse kritiske feil i Python-filer.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def analyze_class_usage(content: str, filename: str) -> List[Dict]:
    """Analyser hvordan klassen brukes i koden."""
    findings = []

    # Se etter DatabaseHandler klassen
    handler_match = re.search(
        r"class\s+DatabaseHandler.*?:.*?def\s+__init__.*?\)", content, re.DOTALL
    )
    if handler_match:
        findings.append(
            {
                "type": "handler_class",
                "file": filename,
                "line": content.count("\n", 0, handler_match.start()) + 1,
                "content": handler_match.group(0),
            }
        )

    # Se etter direkte instansiering av DatabaseContext
    matches = re.finditer(r"(\w+)\s*=\s*(?:get_)?db_context\((.*?)\)", content)
    for match in matches:
        findings.append(
            {
                "type": "instansiering",
                "var_name": match.group(1),
                "args": match.group(2),
                "file": filename,
                "line": content.count("\n", 0, match.start()) + 1,
                "context": content[max(0, match.start() - 100) : match.end() + 100],
            }
        )

    # Se etter bruk av db_context
    matches = re.finditer(r"db_context\.(\w+)\((.*?)\)", content)
    for match in matches:
        findings.append(
            {
                "type": "bruk",
                "method": match.group(1),
                "args": match.group(2),
                "file": filename,
                "line": content.count("\n", 0, match.start()) + 1,
                "context": content[max(0, match.start() - 100) : match.end() + 100],
            }
        )

    # Se etter arv fra DatabaseContext
    matches = re.finditer(r"class\s+(\w+)\s*\(.*?DatabaseContext.*?\):", content)
    for match in matches:
        findings.append(
            {
                "type": "arv",
                "class_name": match.group(1),
                "file": filename,
                "line": content.count("\n", 0, match.start()) + 1,
                "context": content[max(0, match.start() - 100) : match.end() + 100],
            }
        )

    return findings


def analyze_project(base_path: Path) -> None:
    """Analyser hele prosjektet for DatabaseContext bruk."""
    logger.info("Starter prosjektanalyse...")

    all_findings = []

    # Finn alle Python-filer
    for file_path in base_path.rglob("*.py"):
        if file_path.is_file():
            logger.debug(f"Analyserer fil: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if any(
                    term in content
                    for term in ["DatabaseContext", "db_context", "DatabaseHandler"]
                ):
                    findings = analyze_class_usage(content, str(file_path))
                    if findings:
                        logger.debug(f"Fant {len(findings)} treff i {file_path}")
                        all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Feil ved analyse av {file_path}: {e}")

    # Rapporter funn
    if all_findings:
        logger.info("\nFunn i prosjektet:")
        for finding in all_findings:
            if finding["type"] == "handler_class":
                logger.info(
                    f"\n[{finding['file']}:{finding['line']}] "
                    f"DatabaseHandler klasse funnet:"
                )
                logger.debug(f"Innhold:\n{finding['content']}")

            elif finding["type"] == "instansiering":
                logger.info(
                    f"\n[{finding['file']}:{finding['line']}] "
                    f"Instansiering: {finding['var_name']} = "
                    f"db_context({finding['args']})"
                )
                logger.debug(f"Kontekst:\n{finding['context']}")

            elif finding["type"] == "bruk":
                logger.info(
                    f"\n[{finding['file']}:{finding['line']}] "
                    f"Metodekall: db_context.{finding['method']}({finding['args']})"
                )
                logger.debug(f"Kontekst:\n{finding['context']}")

            elif finding["type"] == "arv":
                logger.info(
                    f"\n[{finding['file']}:{finding['line']}] "
                    f"Klasse {finding['class_name']} arver fra DatabaseContext"
                )
                logger.debug(f"Kontekst:\n{finding['context']}")


def main():
    """Hovedfunksjon som kjører analyseverktøyet."""
    base_path = Path("..").resolve()
    logger.info(f"Analyserer prosjekt i: {base_path}")
    analyze_project(base_path)


if __name__ == "__main__":
    main()
