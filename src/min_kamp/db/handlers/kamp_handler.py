"""
Kamp handler.
"""

import logging
from typing import Any, Dict, Optional

from min_kamp.db.errors import DatabaseError

logger = logging.getLogger(__name__)


class KampHandler:
    """Handler for kamp-relaterte databaseoperasjoner."""

    def __init__(self, db_handler: Any) -> None:
        """Initialiser handler.

        Args:
            db_handler: DatabaseHandler instans
        """
        self._database_handler = db_handler

    def opprett_kamp(
        self, bruker_id: int, motstander: str, dato: str, hjemmebane: bool = True
    ) -> Optional[int]:
        """Oppretter en ny kamp.

        Args:
            bruker_id: ID for brukeren
            motstander: Navn på motstander
            dato: Dato for kampen
            hjemmebane: Om det er hjemmekamp

        Returns:
            ID for den nye kampen eller None ved feil
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO kamper (bruker_id, motstander, dato, hjemmebane)
                    VALUES (?, ?, ?, ?)
                    """,
                    (bruker_id, motstander, dato, hjemmebane),
                )
                kamp_id = cursor.lastrowid
                conn.commit()
                return kamp_id

        except Exception as e:
            logger.error("Feil ved opprettelse av kamp: %s", e)
            raise DatabaseError(f"Kunne ikke opprette kamp: {e}")

    def hent_kamp(self, kamp_id: int) -> Optional[Dict[str, Any]]:
        """Henter kampinfo.

        Args:
            kamp_id: ID for kampen

        Returns:
            Dict med kampinfo eller None hvis ikke funnet
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, bruker_id, motstander, dato, hjemmebane
                    FROM kamper
                    WHERE id = ?
                    """,
                    (kamp_id,),
                )
                result = cursor.fetchone()
                if not result:
                    return None

                return {
                    "id": result[0],
                    "bruker_id": result[1],
                    "motstander": result[2],
                    "dato": result[3],
                    "hjemmebane": bool(result[4]),
                }

        except Exception as e:
            logger.error("Feil ved henting av kamp: %s", e)
            raise DatabaseError(f"Kunne ikke hente kamp: {e}")

    def hent_kamper(self, bruker_id: int) -> list[Dict[str, Any]]:
        """Henter alle kamper for en bruker.

        Args:
            bruker_id: ID for brukeren

        Returns:
            Liste med kampinfo
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, motstander, dato, hjemmebane
                    FROM kamper
                    WHERE bruker_id = ?
                    ORDER BY dato DESC
                    """,
                    (bruker_id,),
                )
                return [
                    {
                        "id": row[0],
                        "motstander": row[1],
                        "dato": row[2],
                        "hjemmebane": bool(row[3]),
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            logger.error("Feil ved henting av kamper: %s", e)
            raise DatabaseError(f"Kunne ikke hente kamper: {e}")

    def slett_kamp(self, kamp_id: int) -> None:
        """Sletter en kamp.

        Args:
            kamp_id: ID for kampen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM kamper
                    WHERE id = ?
                    """,
                    (kamp_id,),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved sletting av kamp: %s", e)
            raise DatabaseError(f"Kunne ikke slette kamp: {e}")

    def oppdater_kamp(
        self,
        kamp_id: int,
        motstander: Optional[str] = None,
        dato: Optional[str] = None,
        hjemmebane: Optional[bool] = None,
    ) -> None:
        """Oppdaterer en kamp.

        Args:
            kamp_id: ID for kampen
            motstander: Nytt navn på motstander
            dato: Ny dato for kampen
            hjemmebane: Ny verdi for hjemmebane
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Bygg oppdateringsspørring
                updates = []
                params = []
                if motstander is not None:
                    updates.append("motstander = ?")
                    params.append(motstander)
                if dato is not None:
                    updates.append("dato = ?")
                    params.append(dato)
                if hjemmebane is not None:
                    updates.append("hjemmebane = ?")
                    params.append(hjemmebane)

                if not updates:
                    return

                params.append(kamp_id)
                cursor.execute(
                    """
                    UPDATE kamper
                    SET {}
                    WHERE id = ?
                    """.format(", ".join(updates)),
                    tuple(params),
                )
                conn.commit()

        except Exception as e:
            logger.error("Feil ved oppdatering av kamp: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere kamp: {e}")

    def hent_kamptropp(self, kamp_id: int, bruker_id: int) -> Dict[str, Any]:
        """Henter kamptropp for en kamp.

        Args:
            kamp_id: ID for kampen
            bruker_id: ID for brukeren

        Returns:
            Dict med kamptropp data
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Hent alle spillere for brukeren, gruppert etter posisjon
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.navn,
                        s.posisjon,
                        COALESCE(kt.er_med, 0) as er_med
                    FROM spillere s
                    LEFT JOIN kamptropp kt
                        ON kt.spiller_id = s.id
                        AND kt.kamp_id = ?
                    WHERE s.bruker_id = ?
                    ORDER BY s.posisjon, s.navn
                    """,
                    (kamp_id, bruker_id),
                )

                # Organiser spillere etter posisjon
                spillere = {"Keeper": [], "Forsvar": [], "Midtbane": [], "Angrep": []}

                for row in cursor.fetchall():
                    spiller = {
                        "id": row[0],
                        "navn": row[1],
                        "posisjon": row[2],
                        "er_med": bool(row[3]),
                    }
                    spillere[spiller["posisjon"]].append(spiller)

                logger.debug("Kamptropp data: %s", spillere)
                return {"spillere": spillere}

        except Exception as e:
            logger.error("Feil ved henting av kamptropp: %s", e)
            raise DatabaseError(f"Kunne ikke hente kamptropp: {e}")

    def oppdater_kamptropp(self, kamp_id: int, spillere: list[dict[str, int]]) -> bool:
        """Oppdaterer kamptropp for en kamp.

        Args:
            kamp_id: ID for kampen
            spillere: Liste med spillere som skal være med i kamptroppen

        Returns:
            bool: True hvis oppdateringen var vellykket
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Slett eksisterende kamptropp
                cursor.execute(
                    """
                    DELETE FROM kamptropp
                    WHERE kamp_id = ?
                    """,
                    (kamp_id,),
                )

                # Legg til nye spillere
                for spiller in spillere:
                    cursor.execute(
                        """
                        INSERT INTO kamptropp (kamp_id, spiller_id, er_med)
                        VALUES (?, ?, 1)
                        """,
                        (kamp_id, spiller["spiller_id"]),
                    )

                conn.commit()
                return True

        except Exception as e:
            logger.error("Feil ved oppdatering av kamptropp: %s", e)
            raise DatabaseError(f"Kunne ikke oppdatere kamptropp: {e}")

    def oppdater_spiller_status(
        self, kamp_id: int, spiller_id: int, er_med: bool
    ) -> None:
        """Oppdaterer status for en spiller i kamptroppen.

        Args:
            kamp_id: ID for kampen
            spiller_id: ID for spilleren
            er_med: Om spilleren er med i kamptroppen
        """
        try:
            with self._database_handler.connection() as conn:
                cursor = conn.cursor()

                # Slett eksisterende status hvis den finnes
                cursor.execute(
                    """
                    DELETE FROM kamptropp
                    WHERE kamp_id = ? AND spiller_id = ?
                    """,
                    (kamp_id, spiller_id),
                )

                # Legg til ny status hvis spilleren skal være med
                if er_med:
                    cursor.execute(
                        """
                        INSERT INTO kamptropp (kamp_id, spiller_id, er_med)
                        VALUES (?, ?, 1)
                        """,
                        (kamp_id, spiller_id),
                    )

                conn.commit()

        except Exception as e:
            logger.error("Feil ved oppdatering av spillerstatus: %s", e)
            msg = "Kunne ikke oppdatere spillerstatus: "
            raise DatabaseError(msg + str(e))
