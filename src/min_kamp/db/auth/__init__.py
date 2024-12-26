"""
Autentiseringsmodul for Min Kamp applikasjonen.

Eksporterer:
    AuthHandler: Hovedklasse for autentisering
    vis_login_side: Funksjon for å vise login-siden
"""

from ..handlers.auth_handler import AuthHandler
from .auth_views import vis_login_side

__all__ = [
    "AuthHandler",  # Brukes i database/handlers/base_handler.py
    "vis_login_side",  # Brukes i pages/page_renderer.py
]
