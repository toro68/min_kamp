"""
Bytteplan handler.
"""

import logging
from typing import Any, Dict, Optional, List

from min_kamp.db.errors import DatabaseError
from min_kamp.models.bytteplan_model import Bytteplan, BytteplanDict, Spilletid

logger = logging.getLogger(__name__)


class BytteplanHandler:
    """Handler for bytteplan-relaterte databaseoperasjoner."""

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        self._database_handler = db_handler

    def lagre_bytteplan_innstillinger(
        self, kamp_id: int, bruker_id: int, min_spillere: int, max_spillere: int
    ) -> None:
        """Lagrer bytteplan-innstillinger for en kamp.

        Args:
            kamp_id: ID for kampen
            bruker_id: ID for brukeren
            min_spillere: Minimum antall spillere på banen
            max_spillere: Maksimum antall spillere på banen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                # Slett eksisterende innstillinger
                cursor.execute(
                    """
                    DELETE FROM app_innstillinger
                    WHERE bruker_id = ?
                    AND nokkel IN ('min_spillere', 'max_spillere')
                    """,
                    (bruker_id,),
                )

                # Lagre nye innstillinger
                cursor.execute(
                    """
                    INSERT INTO app_innstillinger
                    (bruker_id, nokkel, verdi)
                    VALUES (?, 'min_spillere', ?),
                           (?, 'max_spillere', ?)
                    """,
                    (bruker_id, min_spillere, bruker_id, max_spillere),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved lagring av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke lagre bytteplan: {e}")

    def hent_bytteplan_innstillinger(
        self, kamp_id: int, bruker_id: int
    ) -> Optional[Dict[str, Any]]:
        """Henter bytteplan-innstillinger for en kamp.

        Args:
            kamp_id: ID for kampen
            bruker_id: ID for brukeren

        Returns:
            Dict med innstillinger eller None hvis ikke funnet
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT nokkel, verdi
                    FROM app_innstillinger
                    WHERE bruker_id = ?
                    AND nokkel IN ('min_spillere', 'max_spillere')
                    """,
                    (bruker_id,),
                )
                results = cursor.fetchall()
                if not results:
                    return None

                innstillinger = {}
                for row in results:
                    innstillinger[row[0]] = int(row[1])
                return innstillinger

        except Exception as e:
            logger.error("Feil ved henting av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke hente bytteplan: {e}")

    def lagre_bytteplan(self, bytteplan: BytteplanDict) -> int:
        """Lagrer en ny bytteplan.

        Args:
            bytteplan: Bytteplan data

        Returns:
            ID for den nye bytteplanen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO bytteplan (
                        kamp_id, spiller_id, periode, er_paa
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        bytteplan["kamp_id"],
                        bytteplan["spiller_id"],
                        bytteplan["periode"],
                        bytteplan["er_paa"],
                    ),
                )
                conn.commit()
                return cursor.lastrowid or 0

        except Exception as e:
            logger.error("Feil ved lagring av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke lagre bytteplan: {e}")

    def hent_bytteplan(self, kamp_id: int) -> List[Bytteplan]:
        """Henter bytteplan for en kamp.

        Args:
            kamp_id: ID for kampen

        Returns:
            Liste med bytteplan-data
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        id, kamp_id, spiller_id, periode, er_paa,
                        opprettet_dato, sist_oppdatert
                    FROM bytteplan
                    WHERE kamp_id = ?
                    ORDER BY periode, spiller_id
                    """,
                    (kamp_id,),
                )

                bytteplaner = []
                for row in cursor.fetchall():
                    bytteplaner.append(
                        Bytteplan(
                            bytteplan_id=row[0],
                            kamp_id=row[1],
                            spiller_id=row[2],
                            periode=row[3],
                            er_paa=bool(row[4]),
                            opprettet=row[5],
                            oppdatert=row[6],
                        )
                    )
                return bytteplaner

        except Exception as e:
            logger.error("Feil ved henting av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke hente bytteplan: {e}")

    def oppdater_bytteplan(self, bytteplan_id: int, er_paa: bool) -> None:
        """Oppdaterer en bytteplan.

        Args:
            bytteplan_id: ID for bytteplanen
            er_paa: Om spilleren er på banen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE bytteplan
                    SET er_paa = ?,
                        sist_oppdatert = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (er_paa, bytteplan_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved oppdatering av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere bytteplan: {e}")

    def slett_bytteplan(self, kamp_id: int) -> None:
        """Sletter bytteplan for en kamp.

        Args:
            kamp_id: ID for kampen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM bytteplan
                    WHERE kamp_id = ?
                    """,
                    (kamp_id,),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved sletting av bytteplan: %s", e)
            raise DatabaseError(f"Kunne ikke slette bytteplan: {e}")

    def lagre_spilletid(self, spilletid: Spilletid) -> None:
        """Lagrer spilletid for en spiller i en kamp.

        Args:
            spilletid: Spilletid data
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO spilletid (
                        kamp_id, spiller_id, minutter
                    ) VALUES (?, ?, ?)
                    ON CONFLICT(kamp_id, spiller_id) DO UPDATE SET
                        minutter = excluded.minutter,
                        sist_oppdatert = CURRENT_TIMESTAMP
                    """,
                    (spilletid.kamp_id, spilletid.spiller_id, spilletid.minutter),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved lagring av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke lagre spilletid: {e}")

    def hent_spilletid(
        self, kamp_id: int, spiller_id: Optional[int] = None
    ) -> List[Spilletid]:
        """Henter spilletid for en kamp.

        Args:
            kamp_id: ID for kampen
            spiller_id: Valgfri ID for spesifikk spiller

        Returns:
            Liste med spilletid-data
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                if spiller_id is not None:
                    cursor.execute(
                        """
                        SELECT kamp_id, spiller_id, minutter
                        FROM spilletid
                        WHERE kamp_id = ? AND spiller_id = ?
                        """,
                        (kamp_id, spiller_id),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT kamp_id, spiller_id, minutter
                        FROM spilletid
                        WHERE kamp_id = ?
                        ORDER BY spiller_id
                        """,
                        (kamp_id,),
                    )

                return [
                    Spilletid(kamp_id=row[0], spiller_id=row[1], minutter=row[2])
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            logger.error("Feil ved henting av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke hente spilletid: {e}")

    def oppdater_spilletid(self, kamp_id: int, spiller_id: int, minutter: int) -> None:
        """Oppdaterer spilletid for en spiller i en kamp.

        Args:
            kamp_id: ID for kampen
            spiller_id: ID for spilleren
            minutter: Antall minutter spilt
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE spilletid
                    SET minutter = ?,
                        sist_oppdatert = CURRENT_TIMESTAMP
                    WHERE kamp_id = ? AND spiller_id = ?
                    """,
                    (minutter, kamp_id, spiller_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved oppdatering av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere spilletid: {e}")

    def slett_spilletid(self, kamp_id: int, spiller_id: Optional[int] = None) -> None:
        """Sletter spilletid for en kamp eller spiller.

        Args:
            kamp_id: ID for kampen
            spiller_id: Valgfri ID for spesifikk spiller
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                if spiller_id is not None:
                    cursor.execute(
                        """
                        DELETE FROM spilletid
                        WHERE kamp_id = ? AND spiller_id = ?
                        """,
                        (kamp_id, spiller_id),
                    )
                else:
                    cursor.execute(
                        """
                        DELETE FROM spilletid
                        WHERE kamp_id = ?
                        """,
                        (kamp_id,),
                    )

                conn.commit()

        except Exception as e:
            logger.error("Feil ved sletting av spilletid: %s", e)
            raise DatabaseError(f"Kunne ikke slette spilletid: {e}")
