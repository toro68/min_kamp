"""
Handler for spilletid operations.
"""

import logging
from datetime import datetime
from threading import Lock
from typing import List, Dict, Any

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


class SpilletidHandler:
    """Handler for spilletidhåndtering"""

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Implementer singleton pattern på en thread-safe måte."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, db_handler: Any):
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instance
        """
        if not hasattr(self, "_initialized"):
            self._database_handler = db_handler
            self._initialized = True
            self._opprett_indekser()

    def _opprett_indekser(self) -> None:
        """Oppretter nødvendige indekser for spilletidtabellen."""
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                # Indeks for kamp_id og spiller_id i spilletid
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_spilletid_kamp_spiller
                    ON spilletid(kamp_id, spiller_id)
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error("Kunne ikke opprette indekser: %s", e)
            raise DatabaseError("Kunne ikke opprette indekser") from e

    def hent_spilletid_rad(self, spilletid_id: int) -> Dict[str, Any]:
        """Henter informasjon om en spilletid-rad.

        Args:
            spilletid_id: ID til spilletid-raden

        Returns:
            Spilletid-informasjon

        Raises:
            NotFoundError: Hvis spilletid-raden ikke finnes
            DatabaseError: Ved databasefeil
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, kamp_id, spiller_id, minutter,
                           opprettet_dato, sist_oppdatert
                    FROM spilletid
                    WHERE id = ?
                    """,
                    (spilletid_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise DatabaseError(f"Spilletid ikke funnet: {spilletid_id}")
                return dict(
                    zip(
                        [
                            "id",
                            "kamp_id",
                            "spiller_id",
                            "minutter",
                            "opprettet_dato",
                            "sist_oppdatert",
                        ],
                        row,
                    )
                )
        except Exception as e:
            logger.error("Feil ved henting av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke hente spilletid: {e}")

    def hent_spilletid(self, kamp_id: int) -> List[Dict[str, Any]]:
        """Henter spilletid for alle spillere i en kamp.

        Args:
            kamp_id: ID til kampen

        Returns:
            Liste med spilletid for hver spiller

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.id as spiller_id, s.navn, s.posisjon, st.minutter,
                           st.opprettet_dato, st.sist_oppdatert
                    FROM spillere s
                    LEFT JOIN spilletid st
                        ON st.spiller_id = s.id
                        AND st.kamp_id = ?
                    ORDER BY s.navn
                    """,
                    (kamp_id,),
                )
                return [
                    dict(
                        zip(
                            [
                                "spiller_id",
                                "navn",
                                "posisjon",
                                "minutter",
                                "opprettet_dato",
                                "sist_oppdatert",
                            ],
                            row,
                        )
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error("Feil ved henting av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke hente spilletid: {e}")

    def oppdater_spilletid(self, kamp_id: int, spiller_id: int, minutter: int) -> None:
        """Oppdaterer spilletid for en spiller i en kamp.

        Args:
            kamp_id: ID til kampen
            spiller_id: ID til spilleren
            minutter: Antall minutter spilt

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                now = datetime.now()
                cursor.execute(
                    """
                    INSERT INTO spilletid (
                        kamp_id, spiller_id, minutter,
                        opprettet_dato, sist_oppdatert
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(kamp_id, spiller_id) DO UPDATE SET
                        minutter = excluded.minutter,
                        sist_oppdatert = excluded.sist_oppdatert
                    """,
                    (kamp_id, spiller_id, minutter, now, now),
                )
                conn.commit()
        except Exception as e:
            logger.error("Feil ved oppdatering av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere spilletid: {e}")
