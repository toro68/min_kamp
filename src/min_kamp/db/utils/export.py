"""
Sentral eksport-funksjonalitet for bytteplan
"""

import logging
from typing import Optional

from ..handlers.bytteplan_handler import BytteplanHandler
from ..handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


def eksporter_bytteplan(
    kamp_id: str, db_handler: BaseHandler, filnavn: Optional[str] = None
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
    handler = BytteplanHandler(db_handler=db_handler)
    return handler.eksporter_bytteplan(kamp_id, filnavn)
