"""
Definerer feilklasser for databaseoperasjoner.
"""

from typing import Optional


class Error(Exception):
    """Base-klasse for alle feil i databaseoperasjoner."""


class DatabaseError(Error):
    """Generell feil i databaseoperasjoner."""


class ConnectionError(DatabaseError):
    """Feil ved tilkobling til database."""


class UniqueConstraintError(DatabaseError):
    """Feil ved brudd på UNIQUE constraint."""

    def __init__(
        self,
        message: str = "Duplikat verdi ikke tillatt",
        column: Optional[str] = None,
    ) -> None:
        self.column = column
        super().__init__(f"{message} i kolonne {column}" if column else message)


class ForeignKeyError(DatabaseError):
    """Feil ved brudd på FOREIGN KEY constraint."""


class NotNullError(DatabaseError):
    """Feil ved brudd på NOT NULL constraint."""

    def __init__(
        self,
        message: str = "Null-verdi ikke tillatt",
        column: Optional[str] = None,
    ) -> None:
        self.column = column
        super().__init__(f"{message} i kolonne {column}" if column else message)


class CheckConstraintError(DatabaseError):
    """Feil ved brudd på CHECK constraint."""


class NotFoundError(DatabaseError):
    """Feil når en ressurs ikke blir funnet."""
