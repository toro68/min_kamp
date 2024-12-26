#!/usr/bin/env python3
"""
Script for å sjekke SQL-spørringer i kodebasen.

Dette scriptet:
1. Finner alle Python-filer i src/min_kamp
2. Sjekker etter SQL-spørringer
3. Validerer spørringene
4. Sjekker etter caching-dekoratører
5. Sjekker etter bruk av BaseHandler og @auto_transaction
"""

import os
import re
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Konstanter
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "min_kamp"
CACHE_PATTERNS = [
    r"@st\.cache_data",
    r"@st\.cache",
    r"@st\.cache_resource",
    r"@st\.experimental_memo",
    r"@st\.experimental_singleton",
]
SQL_PATTERN = (
    r'cursor\.execute\s*\(\s*(?:f?[\'"]|f?"""|\'\'\')'
    + r"(.*?(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER).*?)"
    + r'(?:[\'"]|"""|\'\'\')'
)
BASE_HANDLER_PATTERN = r"from\s+min_kamp\.db\.handlers\.base_handler\s+import"
AUTO_TRANSACTION_PATTERN = r"@auto_transaction"


def finn_python_filer(start_dir: Path) -> List[Path]:
    """Finner alle Python-filer i katalogen og underkatalogene.

    Args:
        start_dir: Katalogen å starte søket fra

    Returns:
        Liste med Path-objekter til Python-filer
    """
    python_filer = []
    for root, _, files in os.walk(start_dir):
        for fil in files:
            if fil.endswith(".py"):
                python_filer.append(Path(root) / fil)
    return python_filer


def finn_cache_dekoratører(filinnhold: str) -> List[Tuple[int, str]]:
    """Finner cache-dekoratører i filinnholdet.

    Args:
        filinnhold: Innholdet i filen

    Returns:
        Liste med tupler (linjenummer, dekoratør)
    """
    cache_dekoratører = []
    linjer = filinnhold.split("\n")
    for i, linje in enumerate(linjer, 1):
        for pattern in CACHE_PATTERNS:
            if re.search(pattern, linje):
                cache_dekoratører.append((i, linje.strip()))
    return cache_dekoratører


def finn_base_handler_bruk(filinnhold: str) -> List[Tuple[int, str]]:
    """Finner bruk av BaseHandler i filinnholdet.

    Args:
        filinnhold: Innholdet i filen

    Returns:
        Liste med tupler (linjenummer, linje)
    """
    base_handler_bruk = []
    linjer = filinnhold.split("\n")
    for i, linje in enumerate(linjer, 1):
        if re.search(BASE_HANDLER_PATTERN, linje):
            base_handler_bruk.append((i, linje.strip()))
        elif "class" in linje and "BaseHandler" in linje:
            base_handler_bruk.append((i, linje.strip()))
    return base_handler_bruk


def finn_auto_transaction_bruk(filinnhold: str) -> List[Tuple[int, str]]:
    """Finner bruk av @auto_transaction i filinnholdet.

    Args:
        filinnhold: Innholdet i filen

    Returns:
        Liste med tupler (linjenummer, linje)
    """
    auto_transaction_bruk = []
    linjer = filinnhold.split("\n")
    for i, linje in enumerate(linjer, 1):
        if re.search(AUTO_TRANSACTION_PATTERN, linje):
            auto_transaction_bruk.append((i, linje.strip()))
    return auto_transaction_bruk


def finn_sql_spørringer(filinnhold: str) -> List[Tuple[int, str]]:
    """Finner SQL-spørringer i filinnholdet.

    Args:
        filinnhold: Innholdet i filen

    Returns:
        Liste med tupler (linjenummer, spørring)
    """
    sql_spørringer = []
    linjer = filinnhold.split("\n")
    samlet_innhold = "\n".join(linjer)

    for match in re.finditer(
        SQL_PATTERN, samlet_innhold, re.IGNORECASE | re.MULTILINE | re.DOTALL
    ):
        # Finn linjenummer for spørringen
        linjenummer = samlet_innhold.count("\n", 0, match.start()) + 1
        sql_spørringer.append((linjenummer, match.group(1).strip()))

    return sql_spørringer


def valider_sql_spørring(spørring: str) -> List[str]:
    """Validerer en SQL-spørring.

    Args:
        spørring: SQL-spørringen som skal valideres

    Returns:
        Liste med feilmeldinger (tom hvis ingen feil)
    """
    feil = []

    # Sjekk etter vanlige feil
    if not spørring.strip():
        feil.append("Tom spørring")

    if "SELECT *" in spørring.upper():
        feil.append("Bruker SELECT * (spesifiser kolonner)")

    sql_nøkkelord = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "DROP",
        "ALTER",
        "PRAGMA",
    ]
    if not any(keyword in spørring.upper() for keyword in sql_nøkkelord):
        feil.append("Mangler SQL-nøkkelord")

    # Ignorer PRAGMA og DDL-kommandoer som ikke trenger parameterbinding
    ddl_nøkkelord = ["PRAGMA", "CREATE", "DROP", "ALTER"]
    if any(keyword in spørring.upper() for keyword in ddl_nøkkelord):
        return feil

    # For DML-kommandoer, sjekk parameterbinding
    if "%s" in spørring:
        feil.append("Bruker %s i stedet for ? for parameterbinding")
    elif "?" not in spørring and not spørring.startswith("PRAGMA"):
        feil.append("Mangler parameterbinding")

    return feil


def sjekk_fil(fil: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Sjekker en fil for SQL-spørringer og cache-dekoratører.

    Args:
        fil: Path til filen som skal sjekkes

    Returns:
        Dict med resultater
    """
    try:
        with open(fil, "r", encoding="utf-8") as f:
            innhold = f.read()

        cache_dekoratører = finn_cache_dekoratører(innhold)
        sql_spørringer = finn_sql_spørringer(innhold)
        base_handler_bruk = finn_base_handler_bruk(innhold)
        auto_transaction_bruk = finn_auto_transaction_bruk(innhold)

        # Valider SQL-spørringer
        sql_feil = []
        for linjenr, spørring in sql_spørringer:
            feil = valider_sql_spørring(spørring)
            if feil:
                sql_feil.append((linjenr, f"{spørring}: {', '.join(feil)}"))

        return {
            "cache_dekoratører": cache_dekoratører,
            "sql_spørringer": sql_spørringer,
            "sql_feil": sql_feil,
            "base_handler_bruk": base_handler_bruk,
            "auto_transaction_bruk": auto_transaction_bruk,
        }

    except Exception as e:
        logger.error("Feil ved sjekking av %s: %s", fil, e)
        return {
            "cache_dekoratører": [],
            "sql_spørringer": [],
            "sql_feil": [(0, f"Feil ved lesing av fil: {e}")],
            "base_handler_bruk": [],
            "auto_transaction_bruk": [],
        }


def main():
    """Hovedfunksjon."""
    logger.info("Starter sjekk av SQL-spørringer")

    # Finn alle Python-filer
    python_filer = finn_python_filer(SRC_DIR)
    logger.info("Fant %d Python-filer", len(python_filer))

    # Sjekk hver fil
    total_cache = 0
    total_sql = 0
    total_feil = 0
    total_base_handler = 0
    total_auto_transaction = 0

    for fil in python_filer:
        relativ_sti = fil.relative_to(PROJECT_ROOT)
        logger.info("Sjekker %s", relativ_sti)

        resultater = sjekk_fil(fil)

        if resultater["cache_dekoratører"]:
            logger.warning(
                "Fant %d cache-dekoratører i %s:",
                len(resultater["cache_dekoratører"]),
                relativ_sti,
            )
            for linjenr, dekoratør in resultater["cache_dekoratører"]:
                logger.warning("  Linje %d: %s", linjenr, dekoratør)
            total_cache += len(resultater["cache_dekoratører"])

        if resultater["sql_spørringer"]:
            logger.info(
                "Fant %d SQL-spørringer i %s",
                len(resultater["sql_spørringer"]),
                relativ_sti,
            )
            total_sql += len(resultater["sql_spørringer"])

        if resultater["sql_feil"]:
            logger.error(
                "Fant %d SQL-feil i %s:", len(resultater["sql_feil"]), relativ_sti
            )
            for linjenr, feil in resultater["sql_feil"]:
                logger.error("  Linje %d: %s", linjenr, feil)
            total_feil += len(resultater["sql_feil"])

        if resultater["base_handler_bruk"]:
            logger.error(
                "Fant %d bruk av BaseHandler i %s:",
                len(resultater["base_handler_bruk"]),
                relativ_sti,
            )
            for linjenr, linje in resultater["base_handler_bruk"]:
                logger.error("  Linje %d: %s", linjenr, linje)
            total_base_handler += len(resultater["base_handler_bruk"])

        if resultater["auto_transaction_bruk"]:
            logger.error(
                "Fant %d bruk av @auto_transaction i %s:",
                len(resultater["auto_transaction_bruk"]),
                relativ_sti,
            )
            for linjenr, linje in resultater["auto_transaction_bruk"]:
                logger.error("  Linje %d: %s", linjenr, linje)
            total_auto_transaction += len(resultater["auto_transaction_bruk"])

    # Oppsummering
    logger.info("\nOppsummering:")
    logger.info("Totalt antall cache-dekoratører: %d", total_cache)
    logger.info("Totalt antall SQL-spørringer: %d", total_sql)
    logger.error("Totalt antall SQL-feil: %d", total_feil)
    logger.error("Totalt antall bruk av BaseHandler: %d", total_base_handler)
    logger.error("Totalt antall bruk av @auto_transaction: %d", total_auto_transaction)

    # Avslutt med feilkode hvis det er feil
    if total_feil > 0 or total_base_handler > 0 or total_auto_transaction > 0:
        exit(1)


if __name__ == "__main__":
    main()
