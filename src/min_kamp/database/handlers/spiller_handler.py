"""
Definerer spiller handler for spillerhåndtering.
"""

import logging
from sqlite3 import Error as SQLiteError
from typing import Optional, List, Dict, Any

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class SpillerHandler(BaseHandler):
    """Handler for spillerhåndtering"""

    def registrer_spiller(self, navn: str, posisjon: str) -> bool:
        """Registrerer en ny spiller

        Args:
            navn: Navnet til spilleren
            posisjon: Posisjonen til spilleren

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
                    INSERT INTO spillere (navn, posisjon, aktiv)
                    VALUES (?, ?, 1)
                    """,
                    (navn, posisjon),
                )

                logger.info("Registrerte spiller %s (%s)", navn, posisjon)
                return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved registrering av spiller: %s", e)
            raise DatabaseError("Kunne ikke registrere spiller") from e
        except Exception as e:
            logger.error("Uventet feil ved registrering av spiller: %s", e)
            raise DatabaseError("Kunne ikke registrere spiller") from e

    def hent_spiller(self, spiller_id: int) -> Optional[tuple]:
        """Henter en spiller

        Args:
            spiller_id: ID til spilleren

        Returns:
            Tuple med (navn, posisjon) hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT navn, posisjon FROM spillere WHERE id = ?", (spiller_id,)
                )
                resultat = cursor.fetchone()

                if resultat:
                    return resultat
                return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av spiller: %s", e)
            raise DatabaseError("Kunne ikke hente spiller") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av spiller: %s", e)
            raise DatabaseError("Kunne ikke hente spiller") from e

    def hent_alle_spillere(self, bare_aktive: bool = True) -> List[Dict[str, Any]]:
        """Henter alle spillere

        Args:
            bare_aktive: Hvis True, returner kun aktive spillere. Hvis False, returner alle spillere.

        Returns:
            Liste med spillere, der hver spiller er en dictionary med følgende nøkler:
            - id: Spiller-ID
            - navn: Navnet til spilleren
            - posisjon: Posisjonen til spilleren
            - aktiv: Om spilleren er aktiv

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                if bare_aktive:
                    where_clause = "WHERE aktiv = 1"
                else:
                    where_clause = ""

                cursor.execute(
                    f"""
                    SELECT id, navn, posisjon, aktiv
                    FROM spillere
                    {where_clause}
                    ORDER BY navn
                    """
                )

                spillere = []
                for row in cursor.fetchall():
                    spillere.append(
                        {
                            "id": row[0],
                            "navn": row[1],
                            "posisjon": row[2],
                            "aktiv": bool(row[3]),
                        }
                    )

                return spillere

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av spillere: %s", e)
            raise DatabaseError("Kunne ikke hente spillere") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av spillere: %s", e)
            raise DatabaseError("Kunne ikke hente spillere") from e

    def aktiver_spiller(self, spiller_id: int) -> bool:
        """Aktiverer en spiller

        Args:
            spiller_id: ID til spilleren som skal aktiveres

        Returns:
            True hvis aktivering var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE spillere
                    SET aktiv = 1
                    WHERE id = ?
                    """,
                    (spiller_id,),
                )

                if cursor.rowcount > 0:
                    logger.info("Aktiverte spiller med ID %s", spiller_id)
                    return True
                return False

        except SQLiteError as e:
            logger.error("SQLite-feil ved aktivering av spiller: %s", e)
            raise DatabaseError("Kunne ikke aktivere spiller") from e
        except Exception as e:
            logger.error("Uventet feil ved aktivering av spiller: %s", e)
            raise DatabaseError("Kunne ikke aktivere spiller") from e

    def importer_spillere(self, spillere: List[Dict[str, str]]) -> List[bool]:
        """Importerer en liste med spillere

        Args:
            spillere: Liste med spillere der hver spiller er en dictionary med følgende nøkler:
                     - navn: Navnet til spilleren
                     - posisjon: Posisjonen til spilleren

        Returns:
            Liste med boolske verdier som indikerer om hver spiller ble importert vellykket

        Raises:
            DatabaseError: Ved databasefeil
        """
        # Gyldige posisjoner
        POSISJONER = ["Keeper", "Forsvar", "Midtbane", "Angrep"]

        resultater = []
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Hent alle eksisterende spillere først
                cursor.execute("SELECT id, navn, aktiv, posisjon FROM spillere")
                alle_spillere = cursor.fetchall()
                logger.info(
                    "Fant %d eksisterende spillere i databasen", len(alle_spillere)
                )
                for spiller in alle_spillere:
                    logger.info(
                        "Eksisterende spiller: ID=%s, navn='%s', aktiv=%s, posisjon='%s'",
                        spiller[0],
                        spiller[1],
                        spiller[2],
                        spiller[3],
                    )

                eksisterende_spillere = {
                    navn.lower(): (id, aktiv, posisjon)
                    for id, navn, aktiv, posisjon in alle_spillere
                }

                for spiller in spillere:
                    try:
                        # Logg innkommende data for debugging
                        logger.info("Importerer spiller: %s", spiller)

                        # Valider at vi har navn
                        if not spiller.get("navn"):
                            logger.error("Manglende navn for spiller: %s", spiller)
                            resultater.append(False)
                            continue

                        # Fjern eventuelle ekstra mellomrom
                        navn = spiller["navn"].strip()
                        posisjon = spiller.get("posisjon", "").strip()

                        # Valider posisjon
                        if not posisjon or posisjon not in POSISJONER:
                            logger.warning(
                                "Ugyldig posisjon '%s' for spiller %s, setter til 'Midtbane'",
                                posisjon,
                                navn,
                            )
                            posisjon = "Midtbane"

                        # Sjekk om spilleren allerede eksisterer
                        navn_lower = navn.lower()
                        logger.info(
                            "Sjekker om spiller '%s' (lower: '%s') eksisterer",
                            navn,
                            navn_lower,
                        )
                        if navn_lower in eksisterende_spillere:
                            spiller_id, er_aktiv, gjeldende_posisjon = (
                                eksisterende_spillere[navn_lower]
                            )
                            logger.info(
                                "Fant eksisterende spiller: ID=%s, er_aktiv=%s, gjeldende_posisjon=%s",
                                spiller_id,
                                er_aktiv,
                                gjeldende_posisjon,
                            )

                            # Oppdater posisjon og aktiver spilleren hvis den var deaktivert
                            if not er_aktiv or gjeldende_posisjon != posisjon:
                                cursor.execute(
                                    """
                                    UPDATE spillere
                                    SET posisjon = ?, aktiv = 1
                                    WHERE id = ?
                                    """,
                                    (posisjon, spiller_id),
                                )

                                if not er_aktiv:
                                    logger.info(
                                        "Reaktiverte spiller %s med posisjon: %s",
                                        navn,
                                        posisjon,
                                    )
                                else:
                                    logger.info(
                                        "Oppdaterte spiller %s med posisjon: %s -> %s",
                                        navn,
                                        gjeldende_posisjon,
                                        posisjon,
                                    )

                            resultater.append(True)

                        else:
                            logger.info(
                                "Fant ikke eksisterende spiller med navn '%s', legger til ny",
                                navn,
                            )
                            # Legg til ny spiller
                            cursor.execute(
                                """
                                INSERT INTO spillere (navn, posisjon, aktiv)
                                VALUES (?, ?, 1)
                                """,
                                (navn, posisjon),
                            )
                            logger.info(
                                "La til ny spiller: %s med posisjon: %s", navn, posisjon
                            )
                            resultater.append(True)

                    except SQLiteError as e:
                        logger.error(
                            "SQLite-feil ved import av spiller %s: %s",
                            spiller.get("navn", "Ukjent"),
                            e,
                        )
                        resultater.append(False)
                    except Exception as e:
                        logger.error(
                            "Uventet feil ved import av spiller %s: %s",
                            spiller.get("navn", "Ukjent"),
                            e,
                        )
                        resultater.append(False)

                # Hent oppdatert liste over spillere for debugging
                cursor.execute("SELECT id, navn, aktiv, posisjon FROM spillere")
                oppdaterte_spillere = cursor.fetchall()
                logger.info(
                    "Etter import: %d spillere i databasen", len(oppdaterte_spillere)
                )
                for spiller in oppdaterte_spillere:
                    logger.info(
                        "Oppdatert spiller: ID=%s, navn='%s', aktiv=%s, posisjon='%s'",
                        spiller[0],
                        spiller[1],
                        spiller[2],
                        spiller[3],
                    )

                return resultater

        except SQLiteError as e:
            logger.error("SQLite-feil ved import av spillere: %s", e)
            raise DatabaseError("Kunne ikke importere spillere") from e
        except Exception as e:
            logger.error("Uventet feil ved import av spillere: %s", e)
            raise DatabaseError("Kunne ikke importere spillere") from e

    def endre_spiller_posisjon(self, spiller_id: int, ny_posisjon: str) -> bool:
        """Endrer posisjonen til en spiller

        Args:
            spiller_id: ID til spilleren
            ny_posisjon: Den nye posisjonen til spilleren

        Returns:
            True hvis endringen var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE spillere
                    SET posisjon = ?
                    WHERE id = ? AND aktiv = 1
                    """,
                    (ny_posisjon, spiller_id),
                )

                if cursor.rowcount > 0:
                    logger.info(
                        "Endret posisjon for spiller %s til %s", spiller_id, ny_posisjon
                    )
                    return True
                return False

        except SQLiteError as e:
            logger.error("SQLite-feil ved endring av spillerposisjon: %s", e)
            raise DatabaseError("Kunne ikke endre spillerposisjon") from e
        except Exception as e:
            logger.error("Uventet feil ved endring av spillerposisjon: %s", e)
            raise DatabaseError("Kunne ikke endre spillerposisjon") from e

    def slett_spiller(self, spiller_id: int) -> bool:
        """Sletter (deaktiverer) en spiller

        Args:
            spiller_id: ID til spilleren som skal slettes

        Returns:
            True hvis sletting var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            with self.db_handler.get_connection() as conn:
                cursor = conn.cursor()

                # Sjekk først om spilleren eksisterer
                cursor.execute("SELECT navn FROM spillere WHERE id = ?", (spiller_id,))
                spiller = cursor.fetchone()

                if not spiller:
                    logger.warning("Fant ikke spiller med ID %s", spiller_id)
                    return False

                # Deaktiver spilleren
                cursor.execute(
                    """
                    UPDATE spillere
                    SET aktiv = 0
                    WHERE id = ?
                    """,
                    (spiller_id,),
                )

                logger.info(
                    "Slettet (deaktiverte) spiller %s (ID: %s)", spiller[0], spiller_id
                )
                return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved sletting av spiller: %s", e)
            raise DatabaseError("Kunne ikke slette spiller") from e
        except Exception as e:
            logger.error("Uventet feil ved sletting av spiller: %s", e)
            raise DatabaseError("Kunne ikke slette spiller") from e
