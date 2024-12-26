"""
Database handler.
"""

import logging
import threading
import traceback
from contextlib import contextmanager
from typing import Any, Optional, Tuple, List, Generator

import sqlite3

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handler for databaseoperasjoner."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self._connection_count = 0
        self._lock = threading.Lock()
        logging.info(f"DatabaseHandler initialisert med database: {database_path}")

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Oppretter en ny databasetilkobling for hver forespørsel."""
        thread_id = threading.get_ident()

        with self._lock:
            self._connection_count += 1
            conn_id = self._connection_count

        # Logg full kallstakk for debugging
        stack = traceback.extract_stack()
        stack_trace = "".join(traceback.format_list(stack[:-1]))

        log_msg = (
            f"\n--- Database Connection Debug ---\n"
            f"[CONN-{conn_id}][Thread-{thread_id}]\n"
            f"Oppretter tilkobling fra:\n{stack_trace}"
        )
        logging.debug(log_msg)

        try:
            # Opprett ny tilkobling for hver forespørsel
            conn = sqlite3.connect(
                self.database_path, timeout=30.0, isolation_level="IMMEDIATE"
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

            logging.debug(f"[CONN-{conn_id}][Thread-{thread_id}] Tilkobling etablert")

            try:
                yield conn
                conn.commit()
                logging.debug(f"[CONN-{conn_id}][Thread-{thread_id}] Endringer lagret")
            except Exception as e:
                conn.rollback()
                error_trace = (
                    f"\n--- Database Error Debug ---\n"
                    f"[CONN-{conn_id}][Thread-{thread_id}]\n"
                    f"Feil under databaseoperasjon: {str(e)}\n"
                    f"Kallstakk:\n{traceback.format_exc()}"
                )
                logging.error(error_trace)
                raise
            finally:
                conn.close()
                logging.debug(f"[CONN-{conn_id}][Thread-{thread_id}] Tilkobling lukket")

        except sqlite3.Error as e:
            error_trace = (
                f"\n--- Database Connection Error Debug ---\n"
                f"[CONN-{conn_id}][Thread-{thread_id}]\n"
                f"Database tilkoblingsfeil: {str(e)}\n"
                f"Kallstakk:\n{traceback.format_exc()}"
            )
            logging.error(error_trace)
            raise

    def execute_query(
        self, query: str, params: Optional[Tuple] = None, fetch_one: bool = False
    ) -> Any:
        """Utfører en SQL spørring og returnerer resultatene."""
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
            except sqlite3.Error as e:
                error_trace = (
                    f"\n--- Query Error Debug ---\n"
                    f"Query: {query}\n"
                    f"Parametere: {params}\n"
                    f"Feil: {str(e)}\n"
                    f"Kallstakk:\n{traceback.format_exc()}"
                )
                logging.error(error_trace)
                raise

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """Utfører en SQL oppdatering og returnerer antall påvirkede rader."""
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows_affected = cursor.rowcount
                return rows_affected
            except sqlite3.Error as e:
                error_trace = (
                    f"\n--- Update Error Debug ---\n"
                    f"Query: {query}\n"
                    f"Parametere: {params}\n"
                    f"Feil: {str(e)}\n"
                    f"Kallstakk:\n{traceback.format_exc()}"
                )
                logging.error(error_trace)
                raise

    def execute_transaction(self, queries: List[Tuple[str, Optional[Tuple]]]) -> None:
        """Utfører flere SQL-operasjoner i én transaksjon."""
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                for query, params in queries:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
            except sqlite3.Error as e:
                error_trace = (
                    f"\n--- Transaction Error Debug ---\n"
                    f"Feil: {str(e)}\n"
                    f"Kallstakk:\n{traceback.format_exc()}"
                )
                logging.error(error_trace)
                raise
