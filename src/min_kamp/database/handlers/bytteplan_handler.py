"""
Definerer bytteplan handler for bytteplanshåndtering.
"""

import logging
import os
from sqlite3 import Error as SQLiteError
from typing import Any, Dict, List, Optional

from min_kamp.database.errors import DatabaseError
from min_kamp.database.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class BytteplanHandler(BaseHandler):
    """Handler for bytteplanshåndtering"""

    def registrer_bytteplan(
        self, kamp_id: int, periode: int, spillere: List[int]
    ) -> bool:
        """Registrerer en bytteplan for en periode

        Args:
            kamp_id: ID til kampen
            periode: Periodenummer
            spillere: Liste med spiller-IDer som skal spille i perioden

        Returns:
            True hvis registrering var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()

            # Slett eksisterende bytteplan for perioden
            cursor.execute(
                "DELETE FROM bytteplan WHERE kamp_id = ? AND periode = ?",
                (kamp_id, periode),
            )

            # Registrer ny bytteplan
            for spiller_id in spillere:
                cursor.execute(
                    """
                    INSERT INTO bytteplan (kamp_id, periode, spiller_id)
                    VALUES (?, ?, ?)
                    """,
                    (kamp_id, periode, spiller_id),
                )

            self.db_handler.commit()

            logger.info(
                "Registrerte bytteplan for kamp %d, periode %d", kamp_id, periode
            )
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved registrering av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke registrere bytteplan") from e
        except Exception as e:
            logger.error("Uventet feil ved registrering av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke registrere bytteplan") from e

    def hent_bytteplan(self, kamp_id: int, periode: int) -> Optional[List[int]]:
        """Henter bytteplan for en periode

        Args:
            kamp_id: ID til kampen
            periode: Periodenummer

        Returns:
            Liste med spiller-IDer hvis funnet, None ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                SELECT spiller_id
                FROM bytteplan
                WHERE kamp_id = ? AND periode = ?
                ORDER BY spiller_id
                """,
                (kamp_id, periode),
            )
            resultat = cursor.fetchall()

            if resultat:
                return [row[0] for row in resultat]
            return None

        except SQLiteError as e:
            logger.error("SQLite-feil ved henting av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke hente bytteplan") from e
        except Exception as e:
            logger.error("Uventet feil ved henting av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke hente bytteplan") from e

    def slett_bytteplan(self, kamp_id: int) -> bool:
        """Sletter alle bytteplaner for en kamp

        Args:
            kamp_id: ID til kampen

        Returns:
            True hvis sletting var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute("DELETE FROM bytteplan WHERE kamp_id = ?", (kamp_id,))
            self.db_handler.commit()

            logger.info("Slettet alle bytteplaner for kamp %d", kamp_id)
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved sletting av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke slette bytteplan") from e
        except Exception as e:
            logger.error("Uventet feil ved sletting av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke slette bytteplan") from e

    def lagre_bytteplan(self, kamp_id: str, bytter: List[Dict[str, Any]]) -> bool:
        """Lagrer en komplett bytteplan for en kamp

        Args:
            kamp_id: ID for kampen
            bytter: Liste med bytter som skal lagres

        Returns:
            True hvis lagring var vellykket, False ellers

        Raises:
            DatabaseError: Ved databasefeil
        """
        try:
            cursor = self.db_handler.get_cursor()

            # Slett eksisterende bytteplan
            cursor.execute("DELETE FROM bytteplan WHERE kamp_id = ?", (kamp_id,))

            # Lagre nye bytter
            for bytte in bytter:
                cursor.execute(
                    """
                    INSERT INTO bytteplan (
                        kamp_id,
                        periode_nummer,
                        spiller_id,
                        er_paa_banen
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        kamp_id,
                        bytte["periode_nummer"],
                        bytte["spiller_id"],
                        bytte["er_paa_banen"],
                    ),
                )

            self.db_handler.commit()
            logger.info("Lagret bytteplan for kamp %s", kamp_id)
            return True

        except SQLiteError as e:
            logger.error("SQLite-feil ved lagring av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke lagre bytteplan") from e
        except Exception as e:
            logger.error("Uventet feil ved lagring av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke lagre bytteplan") from e

    def eksporter_bytteplan(self, kamp_id: str, filnavn: Optional[str] = None) -> str:
        """Eksporterer bytteplan til en fil

        Args:
            kamp_id: ID for kampen
            filnavn: Valgfritt filnavn for eksporten

        Returns:
            Sti til eksportert fil

        Raises:
            DatabaseError: Ved databasefeil
            IOError: Ved feil under filskriving
        """
        try:
            cursor = self.db_handler.get_cursor()
            cursor.execute(
                """
                SELECT b.*, s.navn, s.posisjon
                FROM bytteplan b
                JOIN spillere s ON b.spiller_id = s.spiller_id
                WHERE b.kamp_id = ?
                ORDER BY b.periode_nummer, s.posisjon, s.navn
                """,
                (kamp_id,),
            )
            bytteplan = cursor.fetchall()

            if not bytteplan:
                logger.warning("Ingen bytteplan funnet for kamp %s", kamp_id)
                return ""

            # Generer filnavn hvis ikke spesifisert
            if not filnavn:
                filnavn = f"bytteplan_kamp_{kamp_id}.csv"

            # Sikre at mappen eksisterer
            os.makedirs(os.path.dirname(filnavn), exist_ok=True)

            # Eksporter til CSV
            with open(filnavn, "w", encoding="utf-8") as f:
                # Skriv header
                f.write("Periode,Spiller,Posisjon,På banen\n")

                # Skriv data
                for bytte in bytteplan:
                    f.write(
                        f"{bytte['periode_nummer']},{bytte['navn']},"
                        f"{bytte['posisjon']},{bytte['er_paa_banen']}\n"
                    )

            logger.info("Eksporterte bytteplan for kamp %s til %s", kamp_id, filnavn)
            return filnavn

        except SQLiteError as e:
            logger.error("SQLite-feil ved eksportering av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke eksportere bytteplan") from e
        except IOError as e:
            logger.error("IO-feil ved eksportering av bytteplan: %s", e)
            raise
        except Exception as e:
            logger.error("Uventet feil ved eksportering av bytteplan: %s", e)
            raise DatabaseError("Kunne ikke eksportere bytteplan") from e
