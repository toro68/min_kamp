"""
Definerer kamp handler for kamphåndtering.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional, List, Dict, Any
from datetime import datetime

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class KampHandler(BaseHandler):
    """Handler for kamphåndtering"""

    def registrer_kamp(
        self, dato: str, motstander: str, hjemmebane: bool, user_id: int
    ) -> bool:
        """Registrerer en ny kamp

        Args:
            dato: Datoen for kampen (YYYY-MM-DD)
            motstander: Navnet på motstanderlaget
            hjemmebane: True hvis hjemmekamp, False hvis bortekamp
            user_id: ID til brukeren som registrerer kampen

        Returns:
            True hvis registrering var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO kamper (dato, motstander, hjemmebane, antall_perioder, spillere_per_periode, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (dato, motstander, hjemmebane, 2, 7, user_id),
                )

                logger.info(
                    "Registrerte kamp mot %s den %s (%s)",
                    motstander,
                    dato,
                    "hjemme" if hjemmebane else "borte",
                )
                return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved registrering av kamp: %s", e)
            raise DatabaseError("Kunne ikke registrere kamp") from e
        except Exception as e:
            logger.error("Uventet feil ved registrering av kamp: %s", e)
            raise DatabaseError("Kunne ikke registrere kamp") from e

    def hent_kamp(self, kamp_id: int) -> Optional[tuple]:
        """Henter en kamp

        Args:
            kamp_id: ID til kampen

        Returns:
            Tuple med (dato, motstander, hjemmebane) hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT dato, motstander, hjemmebane FROM kamper WHERE id = ?",
                    (kamp_id,),
                )
                resultat = cursor.fetchone()

                if resultat:
                    return resultat
                return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av kamp: %s", e)
            raise DatabaseError("Kunne ikke hente kamp") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av kamp: %s", e)
            raise DatabaseError("Kunne ikke hente kamp") from e

    def slett_kamp(self, kamp_id: int) -> bool:
        """Sletter en kamp

        Args:
            kamp_id: ID til kampen

        Returns:
            True hvis sletting var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM kamper WHERE id = ?", (kamp_id,))

                logger.info("Slettet kamp %d", kamp_id)
                return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved sletting av kamp: %s", e)
            raise DatabaseError("Kunne ikke slette kamp") from e
        except Exception as e:
            logger.error("Uventet feil ved sletting av kamp: %s", e)
            raise DatabaseError("Kunne ikke slette kamp") from e

    def hent_kamper(self, user_id: int) -> List[Dict[str, Any]]:
        """Henter alle kamper for en bruker.

        Args:
            user_id: ID til brukeren

        Returns:
            Liste med kamper, der hver kamp er en dictionary med følgende nøkler:
            - kamp_id: ID til kampen
            - dato: Dato for kampen
            - motstander: Navn på motstanderlaget
            - hjemmebane: True hvis hjemmekamp, False hvis bortekamp

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id as kamp_id, dato, motstander, hjemmebane
                    FROM kamper
                    WHERE user_id = ?
                    ORDER BY dato DESC
                    """,
                    (user_id,),
                )

                kamper = []
                for row in cursor.fetchall():
                    kamper.append(dict(row))

                return kamper

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av kamper: %s", e)
            raise DatabaseError("Kunne ikke hente kamper") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av kamper: %s", e)
            raise DatabaseError("Kunne ikke hente kamper") from e

    def opprett_kamp(self, motstander: str, user_id: int) -> Optional[int]:
        """Oppretter en ny kamp.

        Args:
            motstander: Navn på motstanderlaget
            user_id: ID til brukeren som oppretter kampen

        Returns:
            ID til den opprettede kampen hvis vellykket, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            # Bruk with-statement for å sikre at tilkoblingen lukkes
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Sjekk at brukeren eksisterer
                cursor.execute("SELECT id FROM brukere WHERE id = ?", (user_id,))
                if not cursor.fetchone():
                    logger.error("Ugyldig bruker-ID: %d", user_id)
                    return None

                # Opprett kampen
                cursor.execute(
                    """
                    INSERT INTO kamper (dato, motstander, hjemmebane, antall_perioder, spillere_per_periode, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().strftime("%Y-%m-%d"),
                        motstander,
                        True,
                        2,
                        7,
                        user_id,
                    ),
                )

                kamp_id = cursor.lastrowid
                logger.info(
                    "Opprettet kamp %d mot %s for bruker %d",
                    kamp_id,
                    motstander,
                    user_id,
                )
                return kamp_id

        except SQLiteError as e:
            logger.error("SQLite-feil ved opprettelse av kamp: %s", e)
            raise DatabaseError("Kunne ikke opprette kamp") from e
        except Exception as e:
            logger.error("Uventet feil ved opprettelse av kamp: %s", e)
            raise DatabaseError("Kunne ikke opprette kamp") from e

    def hent_kamptropp(self, kamp_id: int, user_id: int) -> Dict[int, Dict[str, Any]]:
        """Henter kamptroppen for en kamp.

        Args:
            kamp_id: ID til kampen
            user_id: ID til brukeren som eier kampen

        Returns:
            Dictionary med spiller-ID som nøkkel og spillerinfo som verdi.
            Spillerinfo inneholder:
            - navn: Spillerens navn
            - posisjon: Spillerens posisjon
            - er_med: True hvis spilleren er med i troppen, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Sjekk først at brukeren eier kampen
                cursor.execute(
                    "SELECT id FROM kamper WHERE id = ? AND user_id = ?",
                    (kamp_id, user_id),
                )
                if not cursor.fetchone():
                    raise DatabaseError("Ugyldig kamp-ID eller tilgang nektet")

                # Hent alle spillere og om de er med i troppen
                cursor.execute(
                    """
                    SELECT
                        s.id as spiller_id,
                        s.navn,
                        s.posisjon,
                        CASE WHEN kt.id IS NOT NULL THEN 1 ELSE 0 END as er_med
                    FROM spillere s
                    LEFT JOIN kamptropp kt ON kt.spiller_id = s.id AND kt.kamp_id = ?
                    WHERE s.aktiv = 1
                    ORDER BY s.navn
                    """,
                    (kamp_id,),
                )

                kamptropp = {}
                for row in cursor.fetchall():
                    kamptropp[row["spiller_id"]] = {
                        "navn": row["navn"],
                        "posisjon": row["posisjon"],
                        "er_med": bool(row["er_med"]),
                    }

                return kamptropp

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av kamptropp: %s", e)
            raise DatabaseError("Kunne ikke hente kamptropp") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av kamptropp: %s", e)
            raise DatabaseError("Kunne ikke hente kamptropp") from e

    def lagre_kamptropp(
        self, kamp_id: int, spiller_ids: List[int], user_id: int
    ) -> bool:
        """Lagrer kamptroppen for en kamp.

        Args:
            kamp_id: ID til kampen
            spiller_ids: Liste med spiller-IDer som skal være med i troppen
            user_id: ID til brukeren som eier kampen

        Returns:
            True hvis lagring var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Sjekk først at brukeren eier kampen
                cursor.execute(
                    "SELECT id FROM kamper WHERE id = ? AND user_id = ?",
                    (kamp_id, user_id),
                )
                if not cursor.fetchone():
                    raise DatabaseError("Ugyldig kamp-ID eller tilgang nektet")

                # Slett eksisterende kamptropp
                cursor.execute("DELETE FROM kamptropp WHERE kamp_id = ?", (kamp_id,))

                # Legg til nye spillere i troppen
                for spiller_id in spiller_ids:
                    cursor.execute(
                        """
                        INSERT INTO kamptropp (kamp_id, spiller_id)
                        VALUES (?, ?)
                        """,
                        (kamp_id, spiller_id),
                    )

                logger.info("Lagret kamptropp for kamp %d", kamp_id)
                return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved lagring av kamptropp: %s", e)
            raise DatabaseError("Kunne ikke lagre kamptropp") from e
        except Exception as e:
            logger.error("Uventet feil ved lagring av kamptropp: %s", e)
            raise DatabaseError("Kunne ikke lagre kamptropp") from e
