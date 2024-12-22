"""Definerer feilklasser for databasehåndtering"""


class DatabaseError(Exception):
    """Basis feilklasse for databasefeil"""

    pass


class AuthenticationError(DatabaseError):
    """Feil ved autentisering"""

    pass


class ConnectionError(DatabaseError):
    """Feil ved databasetilkobling"""

    pass


class QueryError(DatabaseError):
    """Feil ved databasespørring"""

    pass
