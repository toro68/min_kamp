"""
Formasjon side.

Viser og administrerer formasjoner for en fotballkamp.
Støtter periodevis oversikt over spillerposisjoner og lagring av formasjoner.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import streamlit as st
import streamlit.components.v1 as components
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.utils.bytteplan_utils import formater_bytter, hent_bytter

logger = logging.getLogger(__name__)

POSISJONER = [
    "Keeper",
    "Forsvar",
    "Midtbane",
    "Angrep",
]

# Prøv å importere pdfkit, men fortsett uten hvis det ikke er tilgjengelig
try:
    import pdfkit

    # Sjekk om wkhtmltopdf er tilgjengelig
    options = {"quiet": ""}
    test_html = "<html><body>Test</body></html>"
    pdfkit.from_string(test_html, None, options=options)
    HAS_PDFKIT = True
except (ImportError, OSError, Exception) as e:
    logger.warning("PDF-støtte er ikke tilgjengelig: %s", str(e))
    logger.warning("For PDF-støtte, installer pdfkit og wkhtmltopdf")

try:
    import imgkit
except ImportError:
    imgkit = None

logger = logging.getLogger(__name__)

POSISJONER = ["Keeper", "Forsvar", "Midtbane", "Angrep"]


class SpillerPosisjon(TypedDict):
    """Type for spiller med posisjon."""

    id: int
    navn: str
    posisjon_index: Optional[int]  # Settes av drag-and-drop
    posisjon: Optional[Dict[str, float]]  # x,y koordinater i prosent


def get_spillerposisjon_index(
    spillerposisjoner: Dict[int, str], spiller_id: int, standard_posisjon: str
) -> int:
    """Henter index for spillerens posisjon i POSISJONER listen."""
    logger.debug(
        "Henter posisjon for spiller %s med standard posisjon %s",
        spiller_id,
        standard_posisjon,
    )

    if not isinstance(spiller_id, int):
        logger.error("Ugyldig spiller_id type: %s", type(spiller_id))
        raise ValueError("spiller_id må være et heltall")

    if standard_posisjon not in POSISJONER:
        logger.error("Ugyldig standard posisjon: %s", standard_posisjon)
        raise ValueError(f"standard_posisjon må være en av: {POSISJONER}")

    posisjon = spillerposisjoner.get(spiller_id, standard_posisjon)
    if posisjon not in POSISJONER:
        logger.error("Ugyldig posisjon funnet: %s", posisjon)
        return POSISJONER.index(standard_posisjon)

    return POSISJONER.index(posisjon)


def lagre_formasjon(
    app_handler: AppHandler,
    kamp_id: int,
    periode_id: int,
    posisjoner: Dict[int, str],
) -> bool:
    """Lagrer spillerposisjoner for en periode."""
    logger.debug(
        "Lagrer formasjon - Kamp: %s, Periode: %s, Posisjoner: %s",
        kamp_id,
        periode_id,
        posisjoner,
    )

    # Valider input
    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("Ugyldig kamp_id: %s", kamp_id)
        return False

    if not isinstance(periode_id, int) or periode_id < 0:
        logger.error("Ugyldig periode_id: %s", periode_id)
        return False

    if not posisjoner:
        logger.error("Ingen posisjoner å lagre")
        return False

    # Valider at alle posisjoner er gyldige
    for spiller_id, posisjon in posisjoner.items():
        if posisjon not in POSISJONER:
            logger.error("Ugyldig posisjon for spiller %s: %s", spiller_id, posisjon)
            return False

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            for spiller_id, posisjon in posisjoner.items():
                cursor.execute(
                    """
                    UPDATE kamptropp
                    SET posisjon = ?
                    WHERE kamp_id = ? AND spiller_id = ?
                """,
                    (posisjon, kamp_id, spiller_id),
                )
            conn.commit()
            logger.info("Formasjon lagret for kamp %s, periode %s", kamp_id, periode_id)
            return True
    except Exception as e:
        logger.error("Feil ved lagring av formasjon: %s", e)
        logger.exception("Full feilmelding:")
        return False


def hent_lagret_formasjon(app_handler: AppHandler, kamp_id: int) -> Optional[Dict]:
    """Henter lagret formasjon for kampen.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID for kampen

    Returns:
        Optional[Dict]: Formasjonsdata hvis funnet
    """
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent formasjon
            cursor.execute(
                """
                SELECT verdi
                FROM app_innstillinger
                WHERE nokkel = 'formasjon'
                AND kamp_id = ?
            """,
                (kamp_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            formasjon = row[0]

            # Hent spillerposisjoner
            cursor.execute(
                """
                SELECT spiller_id, posisjon
                FROM kamptropp
                WHERE kamp_id = ?
                AND posisjon IS NOT NULL
            """,
                (kamp_id,),
            )

            posisjoner = {row[0]: row[1] for row in cursor.fetchall()}

            return {"formasjon": formasjon, "posisjoner": posisjoner}
    except Exception as e:
        logger.error("Feil ved henting av formasjon: %s", e)
        return None


def beregn_spiller_posisjon(
    x_percent: float,
    y_percent: float,
    width: int,
    height: int,
    margin: int = 50,
) -> Tuple[float, float]:
    """
    Beregner spillerens pikselposisjon basert på prosentposisjoner.
    Tar hensyn til banens margin og faktiske spillbare område.
    """
    # Beregn det faktiske spillbare området
    spillbart_width = width - 2 * margin
    spillbart_height = height - 2 * margin

    # Konverter prosent til piksler innenfor det spillbare området
    x_pixels = margin + (spillbart_width * float(x_percent) / 100)
    y_pixels = margin + (spillbart_height * float(y_percent) / 100)

    return x_pixels, y_pixels


def lag_fotballbane_html(
    posisjoner: Optional[List[Tuple[float, float]]] = None,
    spillere_liste: Optional[List[SpillerPosisjon]] = None,
    spillere_paa_benken: Optional[List[Dict[str, Any]]] = None,
    width: int = 1000,
    height: int = 1000,
    kamp_id: Optional[int] = None,
    periode_id: Optional[int] = None,
    app_handler: Optional[AppHandler] = None,
) -> str:
    """Lager HTML for fotballbanen."""
    margin = 50
    sixteen_meter_width = 400
    sixteen_meter_height = 150
    spiller_radius = 40

    # Generer HTML for spillerposisjonene
    spillere_html = ""
    if spillere_liste and posisjoner:
        # Legg til mer detaljert logging for bytter
        try:
            # Lag en dictionary med spillernavn for bytter-søk
            spillere_dict = {}
            for spiller in spillere_liste:
                spillere_dict[spiller["navn"]] = {
                    "perioder": {
                        p: {"er_paa": False, "sist_oppdatert": None} for p in range(10)
                    },  # Støtt flere perioder
                    "id": spiller["id"],
                }

            # Detaljert debug logging
            logger.debug("===== BYTTER DEBUG START =====")
            logger.debug(f"Periode som søkes: {periode_id}")
            logger.debug(f"Spillere som søkes: {list(spillere_dict.keys())}")
            logger.debug(
                "Spillere dict detaljer: %s",
                json.dumps(spillere_dict, indent=2),
            )

            # Sikre at periode_id er en gyldig int
            periode = 0 if periode_id is None else periode_id

            # Hent bytter med mer kontekst
            try:
                # Oppdater spillere_dict med faktisk status
                if app_handler is not None and kamp_id is not None:
                    for p_id in range(periode + 1):
                        paa_banen_temp, paa_benken_temp = (
                            hent_alle_spillere_for_periode(app_handler, p_id, kamp_id)
                        )
                        for spiller in paa_banen_temp + paa_benken_temp:
                            if spiller["navn"] in spillere_dict:
                                spillere_dict[spiller["navn"]]["perioder"][p_id] = {
                                    "er_paa": spiller in paa_banen_temp,
                                    "sist_oppdatert": datetime.now().isoformat(),
                                }

                bytter_inn, bytter_ut = hent_bytter(spillere_dict, periode)
            except Exception as bytter_feil:
                logger.error(f"Feil ved henting av bytter: {bytter_feil}")
                bytter_inn = []
                bytter_ut = []
        except Exception as e:
            logger.error(f"Kritisk feil ved håndtering av bytter: {e}")
            logger.exception("Full feilmelding:")
            bytter_inn = []
            bytter_ut = []

        for spiller, pos in zip(spillere_liste, posisjoner):
            if not isinstance(pos, tuple) or len(pos) != 2:
                logger.warning(f"Ugyldig posisjon for spiller {spiller['id']}: {pos}")
                continue

            x, y = beregn_spiller_posisjon(pos[0], pos[1], width, height, margin)

            # Legg til CSS-klasse for spillere som byttes inn
            byttet_inn_klasse = ""
            er_paa_banen = pos[0] is not None and pos[1] is not None
            if spiller["navn"] in bytter_inn and er_paa_banen:
                logger.debug(
                    "Markerer %s som byttet inn - bekreftet på banen",
                    spiller["navn"],
                )
                byttet_inn_klasse = "byttet-inn"
            elif spiller["navn"] in bytter_inn:
                logger.warning(
                    "Spiller %s er i bytter_inn listen men ikke på banen",
                    spiller["navn"],
                )

            spillere_html += f"""
            <div class="spiller {byttet_inn_klasse}"
                 id="spiller_{spiller['id']}"
                 data-spiller-id="{spiller['id']}"
                 style="left: {x-spiller_radius}px;
                        top: {y-spiller_radius}px;">
                {spiller['navn']}
            </div>
            """

    # Generer periode og bytter info HTML
    periode_html = ""
    bytter_html = ""
    if periode_id is not None and kamp_id is not None and app_handler is not None:
        # Hent kampinnstillinger
        kamplengde, antall_perioder, _ = _hent_kampinnstillinger(app_handler, kamp_id)
        periode_nummer = periode_id + 1  # Konverter til 1-basert

        # Beregn periodelengde og minutter
        periode_lengde = kamplengde / antall_perioder
        start_minutt = int(periode_id * periode_lengde)
        slutt_minutt = int((periode_id + 1) * periode_lengde)

        # Bygg opp spillere dictionary på samme måte som i oversikten
        spillere = {}  # type: Dict[str, Dict[str, Any]]
        for p_id in range(periode_id + 1):
            paa_banen_temp, paa_benken_temp = hent_alle_spillere_for_periode(
                app_handler, p_id, kamp_id
            )
            for spiller in paa_banen_temp + paa_benken_temp:
                if spiller["navn"] not in spillere:
                    spillere[spiller["navn"]] = {"perioder": {}}
                spillere[spiller["navn"]]["perioder"][p_id] = {
                    "er_paa": spiller in paa_banen_temp,
                    "sist_oppdatert": datetime.now().isoformat(),
                }

        # Hent bytter for perioden på samme måte som i oversikten
        bytter_inn, bytter_ut = hent_bytter(spillere, periode_id)
        bytter_tekst = formater_bytter(bytter_inn, bytter_ut)

        # Lag periode_html med bytter-info og minutter
        periode_html = (
            '<div style="position:absolute;top:10px;left:10px;'
            "background-color:rgba(255,255,255,0.9);padding:5px 10px;"
            'border-radius:5px;font-weight:bold;z-index:1000">'
            "Periode {0} ({1}-{2} min)<br>"
            "Bytter denne perioden: {3}"
            "</div>"
        ).format(periode_nummer, start_minutt, slutt_minutt, bytter_tekst)

        # Fjern den gamle bytter_html siden den nå er inkludert i periode_html
        bytter_html = ""

    # Pre-evaluer uttrykk
    spiller_diameter = spiller_radius * 2
    width_minus_margin = width - margin
    height_minus_margin = height - 2 * margin
    height_half = height / 2
    width_half = width / 2
    sixteen_meter_x = (width - sixteen_meter_width) / 2
    sixteen_meter_bottom_y = height - margin - sixteen_meter_height
    periode_id_value = periode_id if periode_id is not None else 0

    html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                .fotballbane {{
                    position: relative;
                    overflow: visible !important;
                    touch-action: none;
                    user-select: none;
                    -webkit-user-select: none;
                    background-color: #2e8b57;
                    width: {3}px;
                    height: {4}px;
                }}
                .straffeomraade {{
                    position: absolute;
                    border: 2px solid white;
                    width: 40%;
                    height: 20%;
                    left: 30%;
                    box-sizing: border-box;
                }}
                .straffeomraade-topp {{
                    top: 0;
                }}
                .straffeomraade-bunn {{
                    bottom: 0;
                }}
                .midtlinje {{
                    position: absolute;
                    width: 100%;
                    height: 0;
                    top: 50%;
                    border-top: 2px solid white;
                }}
                .midtsirkel {{
                    position: absolute;
                    width: 200px;
                    height: 200px;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    border: 2px solid white;
                    border-radius: 50%;
                }}
                .spiller {{
                    position: absolute;
                    width: {0}px;
                    height: {0}px;
                    border-radius: 50%;
                    background-color: red;
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-weight: bold;
                    cursor: move;
                    z-index: 10;
                    touch-action: none;
                    user-select: none;
                    -webkit-user-select: none;
                }}
                .spiller.paa-benken {{
                    position: relative;
                    display: inline-flex;
                    margin: 5px;
                }}
                .benk {{
                    position: absolute;
                    top: 100%;
                    left: 0;
                    width: 100%;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-top: 2px solid #ccc;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                }}
                .periode-velger {{
                    position: absolute;
                    top: -40px;
                    left: 0;
                    width: 100%;
                    display: flex;
                    justify-content: center;
                }}
                .periode-knapp {{
                    margin: 0 5px;
                    padding: 5px 10px;
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    cursor: pointer;
                }}
                .periode-knapp.aktiv {{
                    background-color: #4CAF50;
                    color: white;
                }}
                .bytter {{
                    position: absolute;
                    top: -80px;
                    left: 0;
                    width: 100%;
                    display: flex;
                    justify-content: center;
                    font-size: 14px;
                }}
            </style>
            <script>
            // Throttle-funksjon for å begrense antall kall
            function throttle(func, limit) {
                let inThrottle;
                return function() {
                    const args = arguments;
                    const context = this;
                    if (!inThrottle) {
                        func.apply(context, args);
                        inThrottle = true;
                        setTimeout(() => inThrottle = false, limit);
                    }
                };
            }
            
            function getSpillerPosisjoner() {
                const spillere = document.querySelectorAll('.spiller:not(.paa-benken)');
                const posisjoner = {};
                const bane = document.querySelector('.fotballbane');
                const baneRect = bane.getBoundingClientRect();
                const margin = {1};

                // Beregn det spillbare området
                const spillbartWidth = baneRect.width - 2 * margin;
                const spillbartHeight = baneRect.height - 2 * margin;

                spillere.forEach(spiller => {{
                    const rect = spiller.getBoundingClientRect();
                    const spillerId = spiller.getAttribute('data-spiller-id');

                    // Beregn senterpunkt for spilleren
                    const spillerSenterX = rect.left + rect.width/2;
                    const spillerSenterY = rect.top + rect.height/2;

                    // Beregn relativ posisjon fra banens venstre/topp kant
                    const relativeX = spillerSenterX - baneRect.left - margin;
                    const relativeY = spillerSenterY - baneRect.top - margin;

                    // Konverter til prosent av spillbart område
                    const x = (relativeX / spillbartWidth) * 100;
                    const y = (relativeY / spillbartHeight) * 100;

                    posisjoner[spillerId] = {{
                        x: Math.max(0, Math.min(100, x)).toFixed(2),
                        y: Math.max(0, Math.min(100, y)).toFixed(2)
                    }};
                }});

                const periode_id = bane.getAttribute('data-periode-id');
                return posisjoner;
            }}

            function lagrePosisjoner() {
                const posisjoner = getSpillerPosisjoner();
                const bane = document.querySelector('.fotballbane');
                const periode_id = bane.getAttribute('data-periode-id');

                console.log('Lagrer posisjoner:', periode_id, posisjoner);

                // Send data til Streamlit via URL-parameter
                const data = {{
                    periode_id: periode_id,
                    posisjoner: posisjoner
                }};

                // Oppdater URL med data
                const searchParams = new URLSearchParams(window.parent.location.search);
                searchParams.set('banekart_data', JSON.stringify(data));
                const newUrl = window.parent.location.pathname + '?' + searchParams.toString();
                window.parent.history.pushState({}, '', newUrl);

                // Trigger en Streamlit rerun
                window.parent.postMessage({{
                    type: 'streamlit:setUrlInfo',
                    queryParams: Object.fromEntries(searchParams)
                }}, '*');
            }

            document.addEventListener('DOMContentLoaded', function() {
                const spillere = document.querySelectorAll('.spiller');
                let aktivSpiller = null;
                let startX = 0;
                let startY = 0;
                let offsetX = 0;
                let offsetY = 0;
                let lastX = 0;
                let lastY = 0;

                spillere.forEach(spiller => {{
                    spiller.addEventListener('mousedown', startDrag);
                    spiller.addEventListener('touchstart', startDrag, {{ passive: false }});
                }});

                function startDrag(e) {
                    e.preventDefault();
                    aktivSpiller = this;
                    aktivSpiller.classList.add('dragging');

                    if (e.type === 'mousedown') {
                        startX = e.clientX;
                        startY = e.clientY;
                    } else {
                        startX = e.touches[0].clientX;
                        startY = e.touches[0].clientY;
                    }

                    const style = window.getComputedStyle(aktivSpiller);
                    offsetX = parseFloat(style.left) || 0;
                    offsetY = parseFloat(style.top) || 0;
                    
                    // Lagre siste posisjon for å beregne delta
                    lastX = startX;
                    lastY = startY;

                    document.addEventListener('mousemove', throttledDrag);
                    document.addEventListener('touchmove', throttledDrag, {{ passive: false }});
                    document.addEventListener('mouseup', stopDrag);
                    document.addEventListener('touchend', stopDrag);
                }

                const throttledDrag = throttle(drag, 16); // Ca. 60fps

                function drag(e) {
                    if (!aktivSpiller) return;
                    e.preventDefault();

                    let clientX, clientY;
                    if (e.type === 'mousemove') {
                        clientX = e.clientX;
                        clientY = e.clientY;
                    } else {
                        clientX = e.touches[0].clientX;
                        clientY = e.touches[0].clientY;
                    }

                    // Beregn delta fra siste posisjon i stedet for startposisjon
                    // Dette gir mer presis bevegelse
                    const dx = clientX - lastX;
                    const dy = clientY - lastY;
                    
                    // Oppdater siste posisjon
                    lastX = clientX;
                    lastY = clientY;

                    // Oppdater posisjon med delta
                    offsetX += dx;
                    offsetY += dy;
                    
                    aktivSpiller.style.left = `${offsetX}px`;
                    aktivSpiller.style.top = `${offsetY}px`;
                }

                function stopDrag(e) {
                    if (aktivSpiller) {
                        aktivSpiller.classList.remove('dragging');
                        
                        // Lagre posisjoner bare når dragging er ferdig
                        lagrePosisjoner();
                        
                        aktivSpiller = null;
                    }

                    document.removeEventListener('mousemove', throttledDrag);
                    document.removeEventListener('touchmove', throttledDrag);
                    document.removeEventListener('mouseup', stopDrag);
                    document.removeEventListener('touchend', stopDrag);
                }
            });
            </script>
        </head>
        <body>
            <div class="fotballbane"
                 data-periode-id="{2}"
                 style="width: {3}px; height: {4}px;">
                {5}
                {6}
                <svg width="{3}" height="{4}" viewBox="0 0 {3} {4}" xmlns="http://www.w3.org/2000/svg">
                    <!-- Ytre ramme -->
                    <rect x="{1}"
                          y="{1}"
                          width="{7}"
                          height="{8}"
                          fill="none" stroke="white" stroke-width="2"/>

                    <!-- Midtlinje -->
                    <line x1="{1}"
                          y1="{9}"
                          x2="{7}"
                          y2="{9}"
                          stroke="white" stroke-width="2"/>

                    <!-- Midtsirkel -->
                    <circle cx="{10}" cy="{9}" r="100"
                            fill="none" stroke="white" stroke-width="2"/>

                    <!-- Øvre 16-meter -->
                    <rect x="{11}"
                          y="{1}"
                          width="{12}"
                          height="{13}"
                          fill="none" stroke="white" stroke-width="2"/>

                    <!-- Nedre 16-meter -->
                    <rect x="{11}"
                          y="{14}"
                          width="{12}"
                          height="{13}"
                          fill="none" stroke="white" stroke-width="2"/>
                </svg>
                {15}
            </div>
        </body>
        </html>
    """
    return html.format(
        spiller_diameter,  # 0
        margin,  # 1
        periode_id_value,  # 2
        width,  # 3
        height,  # 4
        periode_html,  # 5
        bytter_html,  # 6
        width_minus_margin,  # 7
        height_minus_margin,  # 8
        height_half,  # 9
        width_half,  # 10
        sixteen_meter_x,  # 11
        sixteen_meter_width,  # 12
        sixteen_meter_height,  # 13
        sixteen_meter_bottom_y,  # 14
        spillere_html,  # 15
    )


def get_available_formations() -> Dict[str, Dict]:
    """Returnerer tilgjengelige formasjoner med posisjoner."""
    return {
        "4-4-2": {
            "forsvar": 4,
            "midtbane": 4,
            "angrep": 2,
            "posisjoner": [
                (50, 90),  # Keeper - nederst midt på
                (20, 75),
                (40, 75),
                (60, 75),
                (80, 75),  # Forsvar
                (20, 50),
                (40, 50),
                (60, 50),
                (80, 50),  # Midtbane
                (35, 25),
                (65, 25),  # Angrep
            ],
        },
        "4-3-3": {
            "forsvar": 4,
            "midtbane": 3,
            "angrep": 3,
            "posisjoner": [
                (50, 90),  # Keeper
                (20, 75),
                (40, 75),
                (60, 75),
                (80, 75),  # Forsvar
                (30, 50),
                (50, 50),
                (70, 50),  # Midtbane
                (25, 25),
                (50, 25),
                (75, 25),  # Angrep
            ],
        },
        "4-2-3-1": {
            "forsvar": 4,
            "midtbane": 5,
            "angrep": 1,
            "posisjoner": [
                (50, 90),  # Keeper
                (20, 75),
                (40, 75),
                (60, 75),
                (80, 75),  # Forsvar
                (35, 60),
                (65, 60),  # Defensive midtbane
                (25, 40),
                (50, 35),
                (75, 40),  # Offensive midtbane
                (50, 25),  # Spiss
            ],
        },
        "3-5-2": {
            "forsvar": 3,
            "midtbane": 5,
            "angrep": 2,
            "posisjoner": [
                (50, 90),  # Keeper
                (30, 75),
                (50, 75),
                (70, 75),  # Forsvar
                (20, 50),
                (35, 50),
                (50, 50),
                (65, 50),
                (80, 50),  # Midtbane
                (35, 25),
                (65, 25),  # Angrep
            ],
        },
    }


def hent_bytteplanperioder(app_handler: AppHandler, kamp_id: int) -> List[Dict]:
    """Henter alle perioder fra bytteplanen."""
    logger.debug("Henter perioder for kamp %s", kamp_id)

    # Valider input
    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("Ugyldig kamp_id: %s", kamp_id)
        return []

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT periode,
                       MIN(opprettet_dato) as start_tid,
                       MAX(sist_oppdatert) as slutt_tid
                FROM bytteplan
                WHERE kamp_id = ?
                GROUP BY periode
                ORDER BY periode
            """,
                (kamp_id,),
            )

            perioder = [
                {
                    "id": row[0],  # periode
                    "start": row[1],
                    "slutt": row[2],
                    "beskrivelse": f"Periode {row[0] + 1}",
                }
                for row in cursor.fetchall()
            ]

            logger.info("Fant %s perioder for kamp %s", len(perioder), kamp_id)
            return perioder

    except Exception as e:
        logger.error("Feil ved henting av bytteplanperioder: %s", e)
        logger.exception("Full feilmelding:")
        return []


def hent_spillere_i_periode(conn, periode_id):
    """Henter alle spillere for en gitt periode."""

    sql = """
    WITH SisteStatus AS (
        SELECT
            spiller_id,
            er_paa,
            periode,
            sist_oppdatert,
            ROW_NUMBER() OVER (
                PARTITION BY spiller_id
                ORDER BY periode DESC, sist_oppdatert DESC
            ) as rn
        FROM bytteplan
        WHERE kamp_id = 16 AND periode = ?
    )
    SELECT
        s.id,
        s.navn,
        COALESCE(ss.er_paa, 0) as er_paa,
        ss.periode
    FROM spillere s
    JOIN kamptropp kt ON s.id = kt.spiller_id AND kt.kamp_id = 16
    LEFT JOIN SisteStatus ss ON s.id = ss.spiller_id AND ss.rn = 1
    WHERE kt.er_med = 1
    ORDER BY s.navn;
    """

    spillere = []
    cursor = conn.cursor()
    cursor.execute(sql, (periode_id,))

    for row in cursor.fetchall():
        spiller = {
            "id": row[0],
            "navn": row[1].strip(),
            "er_paa": row[2],
            "periode": row[3],
        }
        spillere.append(spiller)

    return spillere


def hent_alle_spillere_for_periode(
    app_handler: AppHandler, periode_id: int, kamp_id: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Henter alle spillere for en periode, både på banen og på benken."""
    logger.debug("Henter alle spillere for periode %s i kamp %s", periode_id, kamp_id)

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent alle spillere i kamptroppen med deres siste status
            cursor.execute(
                """
                WITH SisteStatus AS (
                    SELECT
                        spiller_id,
                        er_paa,
                        sist_oppdatert,
                        ROW_NUMBER() OVER (
                            PARTITION BY spiller_id
                            ORDER BY sist_oppdatert DESC
                        ) as rn
                    FROM bytteplan
                    WHERE kamp_id = ? AND periode = ?
                )
                SELECT
                    s.id,
                    s.navn,
                    COALESCE(ss.er_paa, 0) as er_paa,
                    ss.sist_oppdatert
                FROM spillere s
                JOIN kamptropp kt ON s.id = kt.spiller_id AND kt.kamp_id = ?
                LEFT JOIN SisteStatus ss ON s.id = ss.spiller_id AND ss.rn = 1
                WHERE kt.er_med = 1
                ORDER BY s.navn
            """,
                (kamp_id, periode_id, kamp_id),
            )

            paa_banen = []
            paa_benken = []

            for row in cursor.fetchall():
                spiller = {
                    "id": row[0],
                    "navn": row[1].strip(),
                    "posisjon_index": None,
                }

                if row[2]:  # er_paa = 1
                    paa_banen.append(spiller)
                else:
                    paa_benken.append(spiller)

            logger.info(
                "Fant %d spillere på banen og %d på benken for periode %s",
                len(paa_banen),
                len(paa_benken),
                periode_id,
            )

            logger.debug("Hentet %d spillere på banen for periode 0", len(paa_banen))

            logger.debug(
                "Fant %d spillere på banen og %d på benken",
                len(paa_banen),
                len(paa_benken),
            )

            return paa_banen, paa_benken

    except Exception as e:
        logger.error("Feil ved henting av spillere for periode: %s", e)
        logger.exception("Full feilmelding:")
        return [], []


def generer_pdf_html(
    fotballbane_html: str, spillere: List[Dict], periode: Dict, kamp_info: Dict
) -> str:
    """Genererer HTML for PDF-eksport."""
    return f"""
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; overflow: hidden; }}
            .field-container {{ width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        {fotballbane_html}
    </body>
    </html>
    """


def lag_png(
    app_handler: AppHandler,
    kamp_id: int,
    periode_id: int,
    fotballbane_html: str,
    spillere: List[Dict[str, Any]],
) -> Optional[str]:
    """Lager en PNG med formasjon og spillerliste."""
    logger.debug("Genererer PNG for kamp %s, periode %s", kamp_id, periode_id)

    try:
        from html2image import Html2Image  # type: ignore
    except ImportError:
        error_msg = "html2image mangler. Installer med: pip install html2image"
        logger.error(error_msg)
        st.error(error_msg)
        return None

    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("Ugyldig kamp_id: %s", kamp_id)
        return None

    if not isinstance(periode_id, int) or periode_id < 0:
        logger.error("Ugyldig periode_id: %s", periode_id)
        return None

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            # Forenklet spørring som ikke er avhengig av hjemmelag/bortelag kolonner
            try:
                cursor.execute(
                    "SELECT dato FROM kamper WHERE id = ?",
                    (kamp_id,),
                )
                kamp_data = cursor.fetchone()
                dato = (
                    kamp_data[0] if kamp_data else datetime.now().strftime("%Y-%m-%d")
                )
            except Exception as db_error:
                logger.warning(
                    "Kunne ikke hente kampdata: %s. Bruker standardverdier.",
                    db_error,
                )
                dato = datetime.now().strftime("%Y-%m-%d")

            # Bruk tomme strenger for hjemmelag/bortelag siden de ikke er viktige
            kamp_info = {
                "hjemmelag": "",
                "bortelag": "",
                "dato": dato,
            }
            logger.debug("Bruker kamp_info: %s", kamp_info)

        html_content = generer_pdf_html(
            fotballbane_html,
            spillere,
            {"id": periode_id, "start": "Start", "slutt": "Slutt"},
            kamp_info,
        )

        # Bruk nedlastingsmappen i stedet for temp-mappen
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(download_dir):
            logger.warning("Nedlastingsmappe ikke funnet, bruker temp-mappe i stedet")
            download_dir = tempfile.gettempdir()

        logger.debug("Bruker nedlastingsmappe: %s", download_dir)

        hti = Html2Image(
            output_path=download_dir,
            browser_executable="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            custom_flags=["--headless=new"],  # Bruk ny headless-modus
        )
        file_name = f"formation_{kamp_id}_{periode_id}.png"
        output_path = os.path.join(download_dir, file_name)
        # Logg før screenshot-kallet
        logger.info("Starter screenshot for kamp %s, periode %s", kamp_id, periode_id)
        # Ekstra debug logging for html_content
        html_preview = html_content[:100] if html_content else ""
        logger.debug(
            "html_content lengde: %d, preview: %s",
            len(html_content),
            html_preview,
        )
        # Bruker en fast størrelse (1000x1000); denne kan tilpasses om nødvendig
        try:
            logger.debug("Starter screenshot med Html2Image...")
            hti.screenshot(html_str=html_content, save_as=file_name, size=(1000, 1000))
            logger.debug("Screenshot-kall fullført")
        except Exception as e:
            logger.exception("Feil under screenshot-generering: %s", e)
            return None

        # Logg etter screenshot-kallet
        logger.info("Screenshot fullført, sjekker fil: %s", output_path)
        if os.path.exists(output_path):
            logger.info("PNG generert for kamp %s, periode %s", kamp_id, periode_id)
            # Vis melding til brukeren om hvor filen ble lagret
            st.success(f"PNG lagret i nedlastingsmappen: {output_path}")
            return output_path
        else:
            logger.error(
                "PNG-generering feilet: filen %s ble ikke funnet etter screenshot",
                output_path,
            )
            st.error("Kunne ikke generere PNG-fil. Sjekk loggene for detaljer.")
            return None
    except Exception as e:
        logger.error("Feil ved generering av PNG: %s", e)
        logger.exception("Full feilmelding:")
        return None


def lagre_grunnformasjon(app_handler: AppHandler, kamp_id: int, formasjon: str) -> bool:
    """Lagrer grunnformasjon for kampen og spillerposisjoner i banekartet."""
    try:
        logger.debug("=== Start lagre_grunnformasjon ===")
        logger.debug("Parametre: kamp_id=%s, formasjon=%s", kamp_id, formasjon)

        # Valider input
        if not isinstance(kamp_id, int) or kamp_id <= 0:
            logger.error("Ugyldig kamp_id: %s (type: %s)", kamp_id, type(kamp_id))
            return False

        if not formasjon or not isinstance(formasjon, str):
            logger.error("Ugyldig formasjon: %s (type: %s)", formasjon, type(formasjon))
            return False

        bruker_id_str = st.query_params.get("bruker_id")
        logger.debug("Hentet bruker_id_str: %s", bruker_id_str)

        if not bruker_id_str:
            logger.error("Ingen bruker innlogget")
            return False

        try:
            bruker_id = int(bruker_id_str)
            logger.debug("Konvertert bruker_id: %d", bruker_id)
        except (ValueError, TypeError) as e:
            logger.error("Ugyldig bruker ID: %s - %s", bruker_id_str, str(e))
            return False

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            logger.debug("Database tilkobling opprettet")

            try:
                # Lagre formasjonstype i app_innstillinger
                sql = """
                    INSERT OR REPLACE INTO app_innstillinger
                    (kamp_id, bruker_id, nokkel, verdi)
                    VALUES (?, ?, 'grunnformasjon', ?)
                """
                logger.debug("SQL for lagring av grunnformasjon: %s", sql)
                logger.debug(
                    "Parametere: kamp_id=%s, bruker_id=%s, formasjon=%s",
                    kamp_id,
                    bruker_id,
                    formasjon,
                )

                cursor.execute(sql, (kamp_id, bruker_id, formasjon))
                logger.debug("Grunnformasjon lagret i app_innstillinger")

                # Hent spillere som er på banen
                logger.debug("Henter spillere på banen...")
                paa_banen, paa_benken = hent_alle_spillere_for_periode(
                    app_handler, 0, kamp_id
                )
                logger.debug("Fant %d spillere på banen", len(paa_banen))
                logger.debug("Spillere på banen: %s", paa_banen)

                if not paa_banen:
                    logger.warning("Ingen spillere funnet på banen")
                    return True  # Returnerer True siden grunnformasjon ble lagret

                # Hent posisjoner fra valgt formasjon
                formations = get_available_formations()
                if formasjon not in formations:
                    logger.error("Ugyldig formasjon valgt: %s", formasjon)
                    return False

                posisjoner = formations[formasjon]["posisjoner"]
                logger.debug(
                    "Hentet %d posisjoner fra formasjon %s",
                    len(posisjoner),
                    formasjon,
                )
                logger.debug("Posisjoner: %s", posisjoner)

                # Lag spillerposisjoner dict
                spillerposisjoner = {}
                for spiller, pos in zip(paa_banen, posisjoner):
                    if isinstance(pos, tuple) and len(pos) == 2:
                        spillerposisjoner[str(spiller["id"])] = {
                            "x": pos[0],
                            "y": pos[1],
                        }
                logger.debug("Opprettet spillerposisjoner: %s", spillerposisjoner)

                # Lagre spillerposisjoner i banekart tabellen
                if spillerposisjoner:
                    try:
                        # Slett eksisterende posisjoner med feilhåndtering
                        try:
                            cursor.execute(
                                "DELETE FROM banekart WHERE kamp_id = ? AND periode_id = 0",
                                (kamp_id,),
                            )
                            logger.debug(
                                "Slettet eksisterende posisjoner for kamp_id %s",
                                kamp_id,
                            )
                        except Exception as e:
                            logger.exception(
                                "Feil ved sletting av posisjoner for kamp_id %s: %s",
                                kamp_id,
                                e,
                            )
                            raise

                        # Lagre nye posisjoner med feilhåndtering
                        try:
                            cursor.execute(
                                "INSERT INTO banekart (kamp_id, periode_id, data, opprettet_dato, sist_oppdatert) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                                (kamp_id, 0, json.dumps(spillerposisjoner)),
                            )
                            logger.debug(
                                "Nye posisjoner lagret i banekart for kamp_id %s",
                                kamp_id,
                            )
                        except Exception as e:
                            logger.exception(
                                "Feil ved lagring av nye posisjoner for kamp_id %s: %s",
                                kamp_id,
                                e,
                            )
                            raise

                    except Exception as e:
                        logger.error("Feil ved lagring av banekart: %s", str(e))
                        logger.error("SQL state: %s", e.__class__.__name__)
                        conn.rollback()
                        return False

                conn.commit()
                logger.debug("=== Fullført lagre_grunnformasjon ===")
                return True

            except Exception as e:
                logger.error("Feil ved lagring av data: %s", str(e))
                logger.error("SQL state: %s", e.__class__.__name__)
                conn.rollback()
                return False

    except Exception as e:
        logger.error("Uventet feil i lagre_grunnformasjon: %s", str(e))
        logger.exception("Full feilmelding:")
        return False


def hent_grunnformasjon(app_handler: AppHandler, kamp_id: int) -> Optional[str]:
    """Henter lagret grunnformasjon for kampen."""
    logger.debug("Henter grunnformasjon for kamp %s", kamp_id)

    # Valider input
    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("Ugyldig kamp_id: %s", kamp_id)
        return None

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT verdi
                FROM app_innstillinger
                WHERE kamp_id = ? AND nokkel = 'grunnformasjon'
            """,
                (kamp_id,),
            )
            row = cursor.fetchone()

            if row:
                logger.info("Fant grunnformasjon for kamp %s: %s", kamp_id, row[0])
            else:
                logger.info("Ingen grunnformasjon funnet for kamp %s", kamp_id)

            return row[0] if row else None

    except Exception as e:
        logger.error("Feil ved henting av grunnformasjon: %s", e)
        logger.exception("Full feilmelding:")
        return None


def _hent_kampinnstillinger(
    app_handler: AppHandler, kamp_id: int
) -> Tuple[int, int, int]:
    """Henter kampinnstillinger fra databasen."""
    try:
        bruker_id_str = st.query_params.get("bruker_id")
        if not bruker_id_str:
            logger.error("Ingen bruker innlogget")
            return 70, 7, 7

        try:
            bruker_id = int(bruker_id_str)
        except (ValueError, TypeError):
            logger.error("Ugyldig bruker ID")
            return 70, 7, 7

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent innstillinger fra databasen
            sql = """
                SELECT nokkel, verdi, kamp_id, bruker_id, sist_oppdatert
                FROM app_innstillinger
                WHERE (bruker_id = ? OR kamp_id = ?)
                AND nokkel IN ('kamplengde', 'antall_perioder', 'antall_paa_banen')
                ORDER BY
                    CASE
                        WHEN kamp_id = ? THEN 1
                        WHEN bruker_id = ? THEN 2
                        ELSE 3
                    END,
                    sist_oppdatert DESC
            """
            cursor.execute(sql, (bruker_id, kamp_id, kamp_id, bruker_id))

            # Prioriterte innstillinger
            innstillinger = {
                "kamplengde": 70,
                "antall_perioder": 7,
                "antall_paa_banen": 7,
            }

            # Detaljert logging av alle resultater
            logger.debug("DEBUG: Alle innstillinger funnet:")
            for rad in cursor.fetchall():
                nokkel, verdi, rad_kamp_id, rad_bruker_id, sist_oppdatert = rad
                logger.debug(
                    "DEBUG: Rad - Nokkel: %s, Verdi: %s, Kamp ID: %s, "
                    "Bruker ID: %s, Sist oppdatert: %s",
                    nokkel,
                    verdi,
                    rad_kamp_id,
                    rad_bruker_id,
                    sist_oppdatert,
                )

            # Kjør spørringen på nytt for å kunne iterere
            cursor.execute(sql, (bruker_id, kamp_id, kamp_id, bruker_id))

            # Gjennomgå resultater med prioritet
            for (
                nokkel,
                verdi,
                rad_kamp_id,
                rad_bruker_id,
                sist_oppdatert,
            ) in cursor.fetchall():
                logger.debug(
                    "DEBUG: Vurderer innstilling - Nokkel: %s, Verdi: %s, "
                    "Gjeldende kamp_id: %s, Rad kamp_id: %s, Rad bruker_id: %s",
                    nokkel,
                    verdi,
                    kamp_id,
                    rad_kamp_id,
                    rad_bruker_id,
                )

                # Prioriter kamp-spesifikke innstillinger
                if rad_kamp_id == kamp_id:
                    innstillinger[nokkel] = verdi
                    logger.debug(
                        f"DEBUG: Valgt kamp-spesifikk innstilling: {nokkel} = {verdi}"
                    )

                # Deretter bruker-spesifikke
                elif rad_bruker_id == bruker_id and nokkel not in innstillinger:
                    innstillinger[nokkel] = verdi
                    logger.debug(
                        f"DEBUG: Valgt bruker-spesifikk innstilling: {nokkel} = {verdi}"
                    )

            # Logg alle innhentede innstillinger
            logger.debug(
                f"DEBUG: Endelige innstillinger for kamp {kamp_id}: {innstillinger}"
            )

            # Hent verdier med prioritet
            kamplengde = int(innstillinger["kamplengde"])
            antall_perioder = int(innstillinger["antall_perioder"])
            antall_paa_banen = int(innstillinger["antall_paa_banen"])

            # Logg innstillingene
            logger.info(
                "Kampinnstillinger for kamp %s: lengde=%s, " "perioder=%s, spillere=%s",
                kamp_id,
                kamplengde,
                antall_perioder,
                antall_paa_banen,
            )
            return kamplengde, antall_perioder, antall_paa_banen

    except Exception as e:
        logger.error(f"Feil ved henting av kampinnstillinger: {str(e)}")
        logger.exception("Full feilmelding:")
        return 70, 7, 7


def hent_bytter_for_periode(
    app_handler: AppHandler, kamp_id: int, periode_id: int
) -> List[Dict[str, Any]]:
    """Henter alle bytter for en periode."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent alle endringer i perioden
            cursor.execute(
                """
                WITH EndringerIPeriode AS (
                    SELECT
                        spiller_id,
                        er_paa,
                        sist_oppdatert,
                        LAG(er_paa) OVER (
                            PARTITION BY spiller_id
                            ORDER BY sist_oppdatert
                        ) as forrige_status
                    FROM bytteplan
                    WHERE kamp_id = ? AND periode = ?
                    ORDER BY sist_oppdatert
                )
                SELECT s.navn, e.er_paa, e.sist_oppdatert
                FROM EndringerIPeriode e
                JOIN spillere s ON e.spiller_id = s.id
                WHERE (
                    e.er_paa != e.forrige_status
                    OR e.forrige_status IS NULL
                )
                ORDER BY e.sist_oppdatert
            """,
                (kamp_id, periode_id),
            )

            endringer = cursor.fetchall()
            bytter = []

            # Grupper endringer i inn/ut par
            for i in range(0, len(endringer), 2):
                ut, inn = None, None

                # Finn ut og inn par
                for j in range(i, min(i + 2, len(endringer))):
                    if endringer[j][1] == 0:  # er_paa = 0 (ut)
                        ut = endringer[j][0]  # navn
                    elif endringer[j][1] == 1:  # er_paa = 1 (inn)
                        inn = endringer[j][0]  # navn

                if ut and inn:
                    bytter.append({"ut": ut, "inn": inn, "tidspunkt": endringer[i][2]})

            logger.info(
                "Fant %d bytter for periode %d i kamp %d",
                len(bytter),
                periode_id,
                kamp_id,
            )
            return bytter

    except Exception as e:
        logger.error("Feil ved henting av bytter: %s", e)
        return []


def vis_periodevis_oversikt(app_handler: AppHandler, kamp_id: int) -> None:
    """Viser oversikt over formasjoner per periode."""
    # Hent kampinnstillinger først
    kamplengde, antall_perioder, _ = _hent_kampinnstillinger(app_handler, kamp_id)

    # Beregn periodelengde
    periode_lengde = kamplengde / antall_perioder

    # Sett aktiv periode fra URL eller bruk 0 som standard
    aktiv_periode_str = st.query_params.get("periode_id", "0")
    try:
        aktiv_periode = int(aktiv_periode_str)
    except ValueError:
        aktiv_periode = 0

    logger.debug("Aktiv periode: %d", aktiv_periode)

    perioder = []
    for i in range(antall_perioder):
        start_minutt = int(i * periode_lengde)
        slutt_minutt = int((i + 1) * periode_lengde)
        perioder.append(
            {
                "id": i,
                "start": f"{start_minutt}",
                "slutt": f"{slutt_minutt}",
                "beskrivelse": f"Periode {i + 1} ({start_minutt}-{slutt_minutt} min)",
            }
        )

    if not perioder:
        st.warning("Ingen perioder funnet i bytteplanen. Opprett bytteplan først.")
        if st.button("Gå til bytteplan"):
            st.query_params["page"] = "bytteplan"
            st.rerun()
        return

    # Hent grunnformasjon som standard
    grunnformasjon = hent_grunnformasjon(app_handler, kamp_id)

    # Hent tilgjengelige formasjoner
    formations = get_available_formations()

    # Container for alle perioder
    st.markdown(
        """
        <style>
        .stExpander {
            min-height: 800px !important;
            margin-bottom: 20px !important;
            overflow: visible !important;
        }
        .streamlit-expanderContent {
            min-height: 800px !important;
            overflow: visible !important;
            padding-bottom: 20px !important;
        }
        .streamlit-expanderContent > div {
            min-height: 800px !important;
            overflow: visible !important;
        }
        .element-container {
            overflow: visible !important;
        }
        .stMarkdown {
            overflow: visible !important;
        }
        .spiller {
            position: absolute;
            width: 100px;
            height: 100px;
            background-color: white;
            border: 3px solid #1565C0;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: grab;
            user-select: none;
            font-size: 24px;
            font-weight: bold;
            z-index: 1000;
        }
        .spiller:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .spiller:active {
            cursor: grabbing;
        }
        .dragging {
            opacity: 0.8;
            transform: scale(1.1);
            box-shadow: 0 8px 16px rgba(0,0,0,0.4);
            pointer-events: none;
        }
        .fotballbane {
            position: relative;
            overflow: visible !important;
            touch-action: none;
            user-select: none;
            -webkit-user-select: none;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Hent alle spillere og deres status for alle perioder først
    spillere = {}
    for periode in perioder:
        logger.debug(
            "Henter spillere for periode %d (id: %d)",
            periode["id"] + 1,
            periode["id"],
        )
        paa_banen, paa_benken = hent_alle_spillere_for_periode(
            app_handler, periode["id"], kamp_id
        )

        # Oppdater spillerdata med status for denne perioden
        for spiller in paa_banen + paa_benken:
            if spiller["navn"] not in spillere:
                spillere[spiller["navn"]] = {"perioder": {}}

            # Sjekk om vi allerede har en status for denne perioden
            periode_id = periode["id"]
            if periode_id in spillere[spiller["navn"]]["perioder"]:
                # Hvis vi har en nyere status, bruk den
                if (spiller.get("sist_oppdatert") or "") > (
                    spillere[spiller["navn"]]["perioder"][periode_id].get(
                        "sist_oppdatert", ""
                    )
                ):
                    logger.debug(
                        "Oppdaterer status for %s i periode %d: "
                        "er_paa=%s, sist_oppdatert=%s",
                        spiller["navn"],
                        periode_id,
                        spiller in paa_banen,
                        spiller.get("sist_oppdatert"),
                    )
                    spillere[spiller["navn"]]["perioder"][periode_id] = {
                        "er_paa": spiller in paa_banen,
                        "sist_oppdatert": spiller.get("sist_oppdatert"),
                    }
            else:
                # Første gang vi ser denne perioden
                logger.debug(
                    "Setter første status for %s i periode %d: "
                    "er_paa=%s, sist_oppdatert=%s",
                    spiller["navn"],
                    periode_id,
                    spiller in paa_banen,
                    spiller.get("sist_oppdatert"),
                )
                spillere[spiller["navn"]]["perioder"][periode_id] = {
                    "er_paa": spiller in paa_banen,
                    "sist_oppdatert": spiller.get("sist_oppdatert"),
                }

    # Debug logging
    logger.debug(
        "Komplett spillerdata for alle perioder: %s",
        json.dumps(spillere, indent=2),
    )

    for periode in perioder:
        with st.expander(periode["beskrivelse"], expanded=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                # Hent spillere for perioden
                periode_id = periode["id"]
                paa_banen, paa_benken = hent_alle_spillere_for_periode(
                    app_handler, periode_id, kamp_id
                )

                if not paa_banen and not paa_benken:
                    st.info("Ingen spillere funnet for denne perioden")
                    continue

                # Hent og vis bytter for perioden
                try:
                    bytter_inn, bytter_ut = hent_bytter(spillere, periode_id)
                    logger.debug(f"Periode {periode_id} - Bytter inn: {bytter_inn}")
                    logger.debug(f"Periode {periode_id} - Bytter ut: {bytter_ut}")
                    logger.debug(
                        f"Periode {periode_id} - Spillere på banen: {[s['navn'] for s in paa_banen]}"
                    )

                    # Sjekk hver spiller som skal være byttet inn
                    for spiller_navn in bytter_inn:
                        if any(s["navn"] == spiller_navn for s in paa_banen):
                            logger.debug(f"Bekrefter at {spiller_navn} er på banen")
                        else:
                            logger.warning(
                                f"Spiller som skulle vært byttet inn er ikke på banen: {spiller_navn}"
                            )

                    bytter_tekst = formater_bytter(bytter_inn, bytter_ut)
                    if bytter_tekst != "-":
                        logger.info(f"Bytter i periode {periode_id}: {bytter_tekst}")
                except Exception as e:
                    logger.error(f"Feil ved håndtering av bytter: {str(e)}")
                    bytter_inn = []
                    bytter_ut = []

                # Finn index for grunnformasjon
                formasjon_index = 0
                if grunnformasjon:
                    form_keys = list(formations.keys())
                    formasjon_index = form_keys.index(grunnformasjon)

                # Lag format funksjon for formasjon selectbox
                def format_formasjon(x: str) -> str:
                    return (
                        f"{x} ({formations[x]['forsvar']}-"
                        f"{formations[x]['midtbane']}-"
                        f"{formations[x]['angrep']})"
                    )

                selected_formation = st.selectbox(
                    "Velg formasjon for perioden",
                    options=list(formations.keys()),
                    key=f"formation_{periode['id']}",
                    index=formasjon_index,
                    format_func=format_formasjon,
                )

                # Vis fotballbane i nettleseren
                try:
                    spillere_liste = [
                        SpillerPosisjon(
                            id=s["id"],
                            navn=s["navn"],
                            posisjon_index=None,
                            posisjon=None,
                        )
                        for s in paa_banen
                    ]
                    fotballbane_html = lag_fotballbane_html(
                        posisjoner=formations[selected_formation]["posisjoner"],
                        spillere_liste=spillere_liste,
                        spillere_paa_benken=paa_benken,
                        kamp_id=kamp_id,
                        periode_id=periode["id"],
                        app_handler=app_handler,
                    )
                    components.html(fotballbane_html, height=1000, width=1000)
                    with st.container():
                        st.markdown(
                            "---"
                        )  # Delingslinje for å skille banen fra knappene
                        cols = st.columns(2)
                        with cols[0]:
                            if st.button(
                                "Last ned PNG",
                                key=f"last_ned_{periode['id']}",
                                use_container_width=True,
                            ):
                                try:
                                    # Generer PNG istedenfor PDF
                                    png_path = lag_png(
                                        app_handler,
                                        kamp_id,
                                        periode["id"],
                                        fotballbane_html,
                                        paa_banen,
                                    )
                                    if png_path:
                                        st.success(f"PNG generert: {png_path}")
                                    else:
                                        st.error("PNG-generering feilet")
                                except Exception as e:
                                    logger.error("Feil ved PNG-generering: %s", str(e))
                                    st.error("Feil ved PNG-generering")
                        with cols[1]:
                            if st.button(
                                "Lagre formasjon",
                                key=f"lagre_{periode['id']}",
                                use_container_width=True,
                            ):
                                try:
                                    # Bruk en dict comprehension for å få riktig type for lagre_formasjon
                                    success = lagre_formasjon(
                                        app_handler,
                                        kamp_id,
                                        periode["id"],
                                        {s["id"]: s["navn"] for s in paa_banen},
                                    )
                                    if success:
                                        st.success("Formasjon lagret")
                                    else:
                                        st.error("Kunne ikke lagre formasjon")
                                except Exception as e:
                                    logger.error(
                                        "Feil ved lagring av formasjon: %s",
                                        str(e),
                                    )
                                    st.error("Feil ved lagring av formasjon")
                except Exception as e:
                    logger.error("Feil ved visning av fotballbane: %s", str(e))
                    st.error("Kunne ikke vise fotballbane")


def vis_formasjon_side(app_handler: AppHandler) -> None:
    """Viser formasjonssiden.

    Dette er en wrapper-funksjon som kaller vis_periodevis_oversikt.
    """
    # Hent kamp_id fra URL
    kamp_id_str = st.query_params.get("kamp_id")
    if not kamp_id_str:
        st.error("Ingen kamp valgt. Velg en kamp først.")
        if st.button("Gå til kampoversikt"):
            st.query_params["page"] = "kamp"
            st.rerun()
        return

    try:
        kamp_id = int(kamp_id_str)
        vis_periodevis_oversikt(app_handler, kamp_id)
    except ValueError:
        st.error(f"Ugyldig kamp-ID: {kamp_id_str}")
        if st.button("Gå til kampoversikt"):
            st.query_params["page"] = "kamp"
            st.rerun()
        return
