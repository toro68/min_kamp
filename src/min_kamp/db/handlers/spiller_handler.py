"""
Håndterer spillerdata i databasen.
"""

import logging
from typing import List, Any, Optional

from min_kamp.db.errors import DatabaseError
from min_kamp.models.spiller_model import Spiller

logger = logging.getLogger(__name__)


class SpillerHandler:
    """Håndterer spillerdata i databasen."""

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        self._database_handler = db_handler

    def hent_spillere(self, bruker_id: int) -> List[Spiller]:
        """Henter alle spillere for en bruker.

        Args:
            bruker_id: ID til brukeren

        Returns:
            Liste med spillere
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        id,
                        navn,
                        posisjon,
                        bruker_id,
                        opprettet_dato,
                        sist_oppdatert
                    FROM spillere
                    WHERE bruker_id = ?
                    ORDER BY navn
                    """,
                    (bruker_id,),
                )

                return [
                    Spiller(
                        navn=row[1],
                        posisjon=row[2],
                        bruker_id=row[3],
                        id=row[0],
                        opprettet_dato=row[4],
                        sist_oppdatert=row[5],
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error("Feil ved henting av spillere: %s", e)
            raise DatabaseError(f"Kunne ikke hente spillere: {e}")

    def hent_spiller(self, spiller_id: int, bruker_id: int) -> Optional[Spiller]:
        """Henter en spiller.

        Args:
            spiller_id: ID til spilleren
            bruker_id: ID til brukeren

        Returns:
            Spiller eller None hvis ikke funnet
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        id,
                        navn,
                        posisjon,
                        bruker_id,
                        opprettet_dato,
                        sist_oppdatert
                    FROM spillere
                    WHERE id = ? AND bruker_id = ?
                    """,
                    (spiller_id, bruker_id),
                )

                row = cursor.fetchone()
                if row:
                    return Spiller(
                        navn=row[1],
                        posisjon=row[2],
                        bruker_id=row[3],
                        id=row[0],
                        opprettet_dato=row[4],
                        sist_oppdatert=row[5],
                    )
                return None
        except Exception as e:
            logger.error("Feil ved henting av spiller: %s", e)
            raise DatabaseError(f"Kunne ikke hente spiller: {e}")

    def opprett_spiller(self, navn: str, posisjon: str, bruker_id: int) -> int:
        """Oppretter en ny spiller.

        Args:
            navn: Navn på spilleren
            posisjon: Posisjon på banen
            bruker_id: ID til brukeren

        Returns:
            ID til den nye spilleren
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO spillere (
                        navn,
                        posisjon,
                        bruker_id
                    ) VALUES (?, ?, ?)
                    """,
                    (navn, posisjon, bruker_id),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error("Feil ved opprettelse av spiller: %s", e)
            raise DatabaseError(f"Kunne ikke opprette spiller: {e}")

    def oppdater_spiller(
        self,
        spiller_id: int,
        bruker_id: int,
        navn: Optional[str] = None,
        posisjon: Optional[str] = None,
    ) -> None:
        """Oppdaterer en spiller.

        Args:
            spiller_id: ID til spilleren
            bruker_id: ID til brukeren
            navn: Nytt navn (valgfritt)
            posisjon: Ny posisjon (valgfritt)
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Bygg oppdateringsspørring
                updates = []
                params = []
                if navn is not None:
                    updates.append("navn = ?")
                    params.append(navn)
                if posisjon is not None:
                    updates.append("posisjon = ?")
                    params.append(posisjon)

                if not updates:
                    return

                params.extend([spiller_id, bruker_id])
                cursor.execute(
                    """
                    UPDATE spillere
                    SET {}
                    WHERE id = ? AND bruker_id = ?
                    """.format(", ".join(updates)),
                    tuple(params),
                )
                conn.commit()
        except Exception as e:
            logger.error("Feil ved oppdatering av spiller: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere spiller: {e}")

    def slett_spiller(self, spiller_id: int, bruker_id: int) -> None:
        """Sletter en spiller.

        Args:
            spiller_id: ID til spilleren
            bruker_id: ID til brukeren
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM spillere
                    WHERE id = ? AND bruker_id = ?
                    """,
                    (spiller_id, bruker_id),
                )
                conn.commit()
        except Exception as e:
            logger.error("Feil ved sletting av spiller: %s", e)
            raise DatabaseError(f"Kunne ikke slette spiller: {e}")
