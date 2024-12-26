"""
Database connection pool
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator, Optional, Dict, TypeVar, Callable

from min_kamp.db.db_config import get_db_path

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConnectionPool:
    """A simple SQLite connection pool."""

    def __init__(self, database: Optional[str] = None):
        """Initialize the connection pool.

        Args:
            database: Path to the database file. If None, uses default from config.
        """
        self.database = database or get_db_path()
        self._connections: Dict[int, sqlite3.Connection] = {}
        logger.debug("Initialiserer connection pool for %s", self.database)

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection.

        Returns:
            sqlite3.Connection: A database connection
        """
        thread_id = threading.get_ident()
        if thread_id not in self._connections:
            logger.debug("Oppretter ny databasetilkobling for tråd %s", thread_id)
            connection = sqlite3.connect(
                self.database,
                detect_types=(sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES),
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._connections[thread_id] = connection
        return self._connections[thread_id]

    def close(self) -> None:
        """Close all connections in the pool."""
        for thread_id, connection in self._connections.items():
            logger.debug("Lukker databasetilkobling for tråd %s", thread_id)
            connection.close()
        self._connections.clear()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transactions.

        Yields:
            sqlite3.Connection: A database connection
        """
        conn = self.get_connection()
        try:
            yield conn
            try:
                conn.commit()
            except sqlite3.OperationalError as e:
                if "cannot commit" in str(e):
                    logger.warning(
                        "Kunne ikke committe transaksjon - "
                        "antar at den allerede er committet"
                    )
                else:
                    raise
        except Exception as e:
            logger.error("Feil i databasetransaksjon: %s", e)
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                logger.warning(
                    "Kunne ikke rulle tilbake transaksjon - "
                    "antar at den allerede er rullet tilbake"
                )
            raise

    def execute_with_connection(self, func: Callable[[sqlite3.Connection], T]) -> T:
        """Execute a function with a database connection.

        Args:
            func: Function to execute with the connection

        Returns:
            The result of the function
        """
        with self.transaction() as conn:
            return func(conn)


# Opprett en global connection pool
pool = ConnectionPool()
