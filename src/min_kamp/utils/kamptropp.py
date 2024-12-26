"""
Kamptropp utilities.
"""

import logging
from typing import Dict, Any, Optional

from min_kamp.utils.session_state import safe_get_session_state
from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


def hent_kamptropp(kamp_id: int, bruker_id: int) -> Optional[Dict[str, Any]]:
    """Henter kamptropp fra databasen.

    Args:
        kamp_id: ID for kampen
        bruker_id: ID for brukeren

    Returns:
        Dict med kamptropp data eller None ved feil
    """
    try:
        # Hent app_handler fra session state
        app_handler_state = safe_get_session_state("app_handler")
        if not app_handler_state or not app_handler_state.success:
            logger.error("Kunne ikke hente app_handler fra session state")
            return None

        app_handler = app_handler_state.value

        # Hent kamptropp direkte fra databasen
        kamptropp = app_handler.kamp_handler.hent_kamptropp(
            kamp_id=kamp_id, bruker_id=bruker_id
        )

        if not kamptropp:
            logger.warning("Ingen kamptropp funnet for kamp %d", kamp_id)
            return None

        return kamptropp

    except DatabaseError as e:
        logger.error("Databasefeil ved henting av kamptropp: %s", e)
        return None
    except Exception as e:
        logger.error("Uventet feil ved henting av kamptropp: %s", e)
        return None
