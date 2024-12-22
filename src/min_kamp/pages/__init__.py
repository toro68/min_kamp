"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Eksporterer sider.
Se spesielt:
- avhengigheter.md -> Frontend -> Pages
- system.md -> Frontend -> Pages
"""

from min_kamp.pages.oppsett_page import render_oppsett_page

__all__ = [
    "render_oppsett_page",
]
