"""
Utility functions for logging.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def setup_logging(log_dir: str = "logs") -> None:
    """
    Set up logging configuration.
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)


class LoggerHandler:
    """
    Handler for logging operations.
    """

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        self._database_handler = db_handler

    def loggfør(
        self,
        hendelse: str,
        bruker: Optional[str] = None,
        detaljer: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an event.
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO logger (
                        hendelse,
                        bruker,
                        detaljer,
                        tidspunkt
                    )
                    VALUES (?, ?, ?, ?)
                """
                cursor.execute(query, (hendelse, bruker, str(detaljer), datetime.now()))
                conn.commit()
        except Exception as e:
            logger.error("Feil ved logging av hendelse: %s", e)
            raise

    def hent_logger(
        self,
        bruker: Optional[str] = None,
        fra_dato: Optional[datetime] = None,
        til_dato: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get logs.
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM logger WHERE 1=1"
                params = []

                if bruker:
                    query += " AND bruker = ?"
                    params.append(bruker)

                if fra_dato:
                    query += " AND tidspunkt >= ?"
                    params.append(fra_dato)

                if til_dato:
                    query += " AND tidspunkt <= ?"
                    params.append(til_dato)

                query += " ORDER BY tidspunkt DESC"

                cursor.execute(query, tuple(params))
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Feil ved henting av logger: %s", e)
            raise

    def slett_logger(
        self,
        bruker: Optional[str] = None,
        fra_dato: Optional[datetime] = None,
        til_dato: Optional[datetime] = None,
    ) -> None:
        """
        Delete logs.
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                query = "DELETE FROM logger WHERE 1=1"
                params = []

                if bruker:
                    query += " AND bruker = ?"
                    params.append(bruker)

                if fra_dato:
                    query += " AND tidspunkt >= ?"
                    params.append(fra_dato)

                if til_dato:
                    query += " AND tidspunkt <= ?"
                    params.append(til_dato)

                cursor.execute(query, tuple(params))
                conn.commit()
        except Exception as e:
            logger.error("Feil ved sletting av logger: %s", e)
            raise
