"""
Sentral eksport-funksjonalitet for bytteplan
"""

import datetime
import logging
from typing import Any, Optional

from ..handlers.bytteplan_handler import BytteplanHandler

logger = logging.getLogger(__name__)


def eksporter_bytteplan(
    kamp_id: str, db_handler: Any, filnavn: Optional[str] = None
) -> str:
    """
    Eksporterer bytteplan for en kamp til en fil.

    Args:
        kamp_id: ID til kampen som skal eksporteres
        db_handler: Database-handler for tilkobling
        filnavn: Valgfritt filnavn for eksport. Hvis ikke angitt genereres et.

    Returns:
        str: Filbanen til den eksporterte filen

    Raises:
        ValueError: Hvis kamp_id er ugyldig
        OSError: Hvis det oppstår feil ved filskriving
    """
    # Opprett bytteplan-handler
    BytteplanHandler(db_handler=db_handler)

    # Generer filnavn hvis ikke angitt
    if filnavn is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filnavn = f"bytteplan_kamp_{kamp_id}_{timestamp}.xlsx"

    # Implementer eksport-logikk her
    logger.info("Eksporterer bytteplan for kamp %s til %s", kamp_id, filnavn)

    # Returner filbanen
    return filnavn
