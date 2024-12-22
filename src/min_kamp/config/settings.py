"""
Konfigurasjonsfil for applikasjonen.
Inneholder alle globale innstillinger og konstanter.
"""

import logging
import os
from dataclasses import dataclass, fields
from typing import Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class SpillerSettings:
    """Innstillinger for spillere"""

    MIN_SPILLERE: int = 5
    MAX_SPILLERE: int = 11
    STANDARD_PERIODE_LENGDE: int = 5
    MIN_KAMPTID: int = 20
    MAX_KAMPTID: int = 90


@dataclass
class UISettings:
    """Innstillinger for brukergrensesnitt"""

    TEMA: str = "light"
    SIDEBAR_STATE: str = "expanded"
    PAGE_ICON: str = "⚽"
    PAGE_TITLE: str = "Min Kamp"


@dataclass
class DatabaseSettings:
    """Innstillinger for database"""

    DB_PATH: str = "data/minkamp.db"
    DB_BACKUP_PATH: str = "data/backup"
    MAX_BACKUP_COUNT: int = 5


@dataclass
class LoggingSettings:
    """Innstillinger for logging"""

    LOG_PATH: str = "logs"
    LOG_LEVEL: str = "INFO"
    MAX_LOG_SIZE: int = 5_000_000  # 5MB
    MAX_LOG_COUNT: int = 3


@dataclass
class AppSettings:
    """Applikasjonsinnstillinger"""

    spiller: SpillerSettings
    ui: UISettings
    database: DatabaseSettings
    logging: LoggingSettings

    def __init__(self) -> None:
        """Initialiserer med standardverdier"""
        self.spiller = SpillerSettings()
        self.ui = UISettings()
        self.database = DatabaseSettings()
        self.logging = LoggingSettings()

    @classmethod
    def load_from_env(cls) -> "AppSettings":
        """
        Laster innstillinger fra miljøvariabler hvis de finnes.

        Returns:
            AppSettings: Instans med oppdaterte innstillinger
        """
        try:
            instance = cls()

            # Last inn miljøvariabler
            env_vars = {
                "spiller.MIN_SPILLERE": "MINKAMP_MIN_SPILLERE",
                "spiller.MAX_SPILLERE": "MINKAMP_MAX_SPILLERE",
                "spiller.STANDARD_PERIODE_LENGDE": "MINKAMP_PERIODE_LENGDE",
                "spiller.MIN_KAMPTID": "MINKAMP_MIN_KAMPTID",
                "spiller.MAX_KAMPTID": "MINKAMP_MAX_KAMPTID",
                "ui.TEMA": "MINKAMP_TEMA",
                "database.DB_PATH": "MINKAMP_DB_PATH",
                "logging.LOG_LEVEL": "MINKAMP_LOG_LEVEL",
            }

            for path, env_var in env_vars.items():
                if env_value := os.getenv(env_var):
                    try:
                        # Splitt path i objekt og attributt
                        obj_name, attr_name = path.split(".")
                        obj = getattr(instance, obj_name)
                        # Konverter til riktig type
                        field_type = type(getattr(obj, attr_name))
                        setattr(obj, attr_name, field_type(env_value))
                    except (ValueError, AttributeError) as e:
                        logger.warning("Kunne ikke konvertere %s: %s", env_var, e)

            return instance

        except (AttributeError, TypeError) as e:
            logger.error("Feil ved lasting av innstillinger: %s", e)
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """
        Konverterer innstillinger til dictionary.

        Returns:
            Dict[str, Any]: Innstillinger som dictionary
        """
        return {
            "spiller": {
                field.name: getattr(self.spiller, field.name)
                for field in fields(self.spiller)
            },
            "ui": {
                field.name: getattr(self.ui, field.name) for field in fields(self.ui)
            },
            "database": {
                field.name: getattr(self.database, field.name)
                for field in fields(self.database)
            },
            "logging": {
                field.name: getattr(self.logging, field.name)
                for field in fields(self.logging)
            },
        }

    def validate(self) -> bool:
        """
        Validerer at alle innstillinger har gyldige verdier.

        Returns:
            bool: True hvis alle innstillinger er gyldige
        """
        try:
            # Sjekk spillerinnstillinger
            if not 0 < self.spiller.MIN_SPILLERE <= self.spiller.MAX_SPILLERE:
                logger.error("Ugyldig antall spillere konfigurert")
                return False

            if not 0 < self.spiller.MIN_KAMPTID <= self.spiller.MAX_KAMPTID:
                logger.error("Ugyldig kamptid konfigurert")
                return False

            if self.spiller.STANDARD_PERIODE_LENGDE <= 0:
                logger.error("Ugyldig periodelengde")
                return False

            # Sjekk at paths eksisterer
            os.makedirs(os.path.dirname(self.database.DB_PATH), exist_ok=True)
            os.makedirs(self.database.DB_BACKUP_PATH, exist_ok=True)
            os.makedirs(self.logging.LOG_PATH, exist_ok=True)

            return True

        except (OSError, ValueError) as e:
            logger.error("Feil ved validering av innstillinger: %s", e)
            return False


# Global innstillingsinstans
app_settings = AppSettings.load_from_env()
if not app_settings.validate():
    logger.error("Ugyldig konfigurasjon")
    raise ValueError("Ugyldig konfigurasjon")
