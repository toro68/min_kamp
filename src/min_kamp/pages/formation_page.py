"""
Formasjon side.

Viser og administrerer formasjoner for en fotballkamp.
Støtter periodevis oversikt over spillerposisjoner og lagring av formasjoner.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import pdfkit
import streamlit as st
import streamlit.components.v1 as components
from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.utils.bytteplan_utils import formater_bytter, hent_bytter

logger = logging.getLogger(__name__)

POSISJONER = ["Keeper", "Forsvar", "Midtbane", "Angrep"]

try:
    # Sjekk om wkhtmltopdf er tilgjengelig
    options = {"quiet": ""}
    test_html = "<html><body>Test</body></html>"
    pdfkit.from_string(test_html, None, options=options)
    HAS_PDFKIT = True
except ImportError:
    HAS_PDFKIT = False
    logger.warning("pdfkit er ikke installert. " "Installer med: pip install pdfkit")
except OSError:
    HAS_PDFKIT = False
    logger.warning(
        "wkhtmltopdf er ikke installert eller ikke funnet i PATH. "
        "Installer wkhtmltopdf fra: https://wkhtmltopdf.org/downloads.html"
    )
except Exception as e:
    HAS_PDFKIT = False
    logger.warning("Kunne ikke initialisere PDF-støtte: %s", str(e))

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
    app_handler: AppHandler, kamp_id: int, periode_id: int, posisjoner: Dict[int, str]
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


def lag_fotballbane_html(
    posisjoner: Optional[List[Tuple[float, float]]] = None,
    spillere: Optional[List[SpillerPosisjon]] = None,
    spillere_paa_benken: Optional[List[Dict[str, Any]]] = None,
    width: int = 1000,
    height: int = 1000,
    kamp_id: Optional[int] = None,
    periode_id: Optional[int] = None,
) -> str:
    """Lager HTML for fotballbanen med spillere."""
    margin = 50
    spiller_radius = 20
    bench_start_x = width + margin
    bench_spacing = spiller_radius * 3
    sixteen_meter_height = 150
    sixteen_meter_width = 400

    # Generer HTML for spillerposisjonene
    spillere_html = ""
    if spillere and posisjoner:
        for spiller, pos in zip(spillere, posisjoner):
            if not isinstance(pos, tuple) or len(pos) != 2:
                logger.warning(f"Ugyldig posisjon for spiller {spiller['id']}: {pos}")
                continue

            x, y = beregn_spiller_posisjon(pos[0], pos[1], width, height)
            spillere_html += f"""
            <div class="spiller" draggable="true"
                 id="spiller_{spiller['id']}"
                 data-spiller-id="{spiller['id']}"
                 style="position: absolute;
                        left: {x-spiller_radius}px;
                        top: {y-spiller_radius}px;
                        width: {spiller_radius*2}px;
                        height: {spiller_radius*2}px;
                        background-color: white;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 12px;
                        color: black;
                        cursor: move;
                        user-select: none;
                        -webkit-user-select: none;
                        touch-action: none;
                        z-index: 1000;">
                {spiller['navn']}
            </div>
            """

    # Generer HTML for spillere på benken
    if spillere_paa_benken:
        for i, spiller in enumerate(spillere_paa_benken):
            y = margin + i * bench_spacing
            spillere_html += f"""
            <div class="spiller" draggable="true"
                 id="spiller_{spiller['id']}"
                 data-spiller-id="{spiller['id']}"
                 style="position: absolute;
                        left: {bench_start_x}px;
                        top: {y}px;
                        width: {spiller_radius*2}px;
                        height: {spiller_radius*2}px;
                        background-color: #ddd;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 12px;
                        color: black;
                        cursor: move;
                        user-select: none;
                        -webkit-user-select: none;
                        touch-action: none;
                        z-index: 1000;">
                {spiller['navn']}
            </div>
            """

    # Bygg komplett HTML
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .fotballbane {{
                    position: relative;
                    overflow: visible !important;
                    touch-action: none;
                    user-select: none;
                    -webkit-user-select: none;
                }}
                .spiller {{
                    position: absolute;
                    cursor: grab;
                    user-select: none;
                    -webkit-user-select: none;
                    touch-action: none;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .spiller:hover {{
                    transform: scale(1.1);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                    cursor: grab;
                }}
                .spiller:active {{
                    cursor: grabbing;
                }}
                .dragging {{
                    opacity: 0.8;
                    transform: scale(1.1);
                    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
                    pointer-events: none;
                }}
                .lagre-knapp {{
                    position: absolute;
                    top: {height + margin}px;
                    left: {margin}px;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }}
                .lagre-knapp:hover {{
                    background-color: #45a049;
                }}
            </style>
        </head>
        <body>
            <div style="width: {width+300}px; height: {height}px;
                        position: relative; overflow: visible;"
                 class="fotballbane"
                 data-periode-id="{periode_id}">
                <svg width="{width}" height="{height}"
                     style="background-color: #2e8b57;">
                    <!-- Ytre ramme -->
                    <rect x="{margin}" y="{margin}"
                          width="{width-2*margin}" height="{height-2*margin}"
                          fill="none" stroke="white" stroke-width="2"/>

                    <!-- Midtlinje -->
                    <line x1="{margin}" y1="{height/2}"
                          x2="{width-margin}" y2="{height/2}"
                          stroke="white" stroke-width="2"/>

                    <!-- Midtsirkel -->
                    <circle cx="{width/2}" cy="{height/2}" r="{height/8}"
                            fill="none" stroke="white" stroke-width="2"/>

                    <!-- Øvre 16-meter -->
                    <rect x="{(width-sixteen_meter_width)/2}" y="{margin}"
                          width="{sixteen_meter_width}"
                          height="{sixteen_meter_height}"
                          fill="none" stroke="white" stroke-width="2"/>

                    <!-- Nedre 16-meter -->
                    <rect x="{(width-sixteen_meter_width)/2}"
                          y="{height-margin-sixteen_meter_height}"
                          width="{sixteen_meter_width}"
                          height="{sixteen_meter_height}"
                          fill="none" stroke="white" stroke-width="2"/>
                </svg>

                <!-- Spillere -->
                {spillere_html}
            </div>
            <button class="lagre-knapp" onclick="lagreFormasjon({periode_id})">
                Lagre posisjoner
            </button>
            <script>
                document.addEventListener('DOMContentLoaded', () => {{
                    const spillere = document.querySelectorAll('.spiller');
                    const fotballbane = document.querySelector('.fotballbane');

                    let draggedElement = null;
                    let initialX = 0;
                    let initialY = 0;
                    let isDragging = false;

                    spillere.forEach(spiller => {{
                        spiller.addEventListener('mousedown', handleDragStart);
                        spiller.addEventListener(
                            'touchstart',
                            handleTouchStart,
                            {{ passive: false }}
                        );
                    }});

                    document.addEventListener('mousemove', handleDrag);
                    document.addEventListener('mouseup', handleDragEnd);
                    document.addEventListener(
                        'touchmove',
                        handleTouchMove,
                        {{ passive: false }}
                    );

                    function handleTouchStart(event) {{
                        if (isDragging) return;
                        event.preventDefault();
                        const touch = event.touches[0];
                        draggedElement = this;
                        const rect = draggedElement.getBoundingClientRect();
                        initialX = touch.clientX - rect.left;
                        initialY = touch.clientY - rect.top;
                        draggedElement.classList.add('dragging');
                        isDragging = true;
                    }}

                    function handleTouchMove(event) {{
                        if (!draggedElement || !isDragging) return;
                        event.preventDefault();

                        const touch = event.touches[0];
                        const x = touch.clientX - initialX;
                        const y = touch.clientY - initialY;

                        // Begrens bevegelse innenfor fotballbanen
                        const baneRect = fotballbane.getBoundingClientRect();
                        const spillerRect = draggedElement.getBoundingClientRect();

                        const minX = baneRect.left;
                        const maxX = baneRect.right - spillerRect.width;
                        const minY = baneRect.top;
                        const maxY = baneRect.bottom - spillerRect.height;

                        const boundedX = Math.max(minX, Math.min(maxX, x));
                        const boundedY = Math.max(minY, Math.min(maxY, y));

                        draggedElement.style.left = boundedX + 'px';
                        draggedElement.style.top = boundedY + 'px';
                    }}

                    function handleTouchEnd(event) {{
                        if (!draggedElement || !isDragging) return;
                        event.preventDefault();
                        draggedElement.classList.remove('dragging');
                        draggedElement = null;
                        isDragging = false;
                    }}

                    function handleDragStart(event) {{
                        if (isDragging) return;
                        draggedElement = this;
                        const rect = draggedElement.getBoundingClientRect();
                        initialX = event.clientX - rect.left;
                        initialY = event.clientY - rect.top;
                        draggedElement.classList.add('dragging');
                        isDragging = true;
                    }}

                    function handleDrag(event) {{
                        if (!draggedElement || !isDragging) return;
                        event.preventDefault();

                        const x = event.clientX - initialX;
                        const y = event.clientY - initialY;

                        // Begrens bevegelse innenfor fotballbanen
                        const baneRect = fotballbane.getBoundingClientRect();
                        const spillerRect = draggedElement.getBoundingClientRect();

                        const minX = baneRect.left;
                        const maxX = baneRect.right - spillerRect.width;
                        const minY = baneRect.top;
                        const maxY = baneRect.bottom - spillerRect.height;

                        const boundedX = Math.max(minX, Math.min(maxX, x));
                        const boundedY = Math.max(minY, Math.min(maxY, y));

                        draggedElement.style.left = boundedX + 'px';
                        draggedElement.style.top = boundedY + 'px';
                    }}

                    function handleDragEnd(event) {{
                        if (!draggedElement || !isDragging) return;
                        draggedElement.classList.remove('dragging');
                        draggedElement = null;
                        isDragging = false;
                    }}
                }});

                function lagreFormasjon(periodeId) {{
                    const spillere = document.querySelectorAll('.spiller');
                    const fotballbane = document.querySelector('.fotballbane');
                    const posisjoner = {{}};

                    try {{
                        spillere.forEach(spiller => {{
                            const spillerId = spiller.dataset.spillerId;
                            const rect = spiller.getBoundingClientRect();
                            const baneRect = fotballbane.getBoundingClientRect();

                            // Beregn relative posisjoner i prosent
                            const x = (
                                (rect.left - baneRect.left) / baneRect.width
                            ) * 100;
                            const y = (
                                (rect.top - baneRect.top) / baneRect.height
                            ) * 100;

                            // Begrens verdiene til 0-100%
                            const boundedX = Math.max(0, Math.min(100, x));
                            const boundedY = Math.max(0, Math.min(100, y));

                            posisjoner[spillerId] = {{x: boundedX, y: boundedY}};
                        }});

                        const data = {{
                            type: 'banekart',
                            posisjoner: posisjoner
                        }};

                        window.parent.postMessage({{
                            type: 'streamlit:setQueryParam',
                            queryParams: {{
                                [`banekart_${{periodeId}}`]: JSON.stringify(data)
                            }}
                        }}, '*');
                    }} catch (error) {{
                        console.error('Feil ved lagring av posisjoner:', error);
                    }}
                }}
            </script>
        </body>
        </html>
    """

    return html


def beregn_spiller_posisjon(
    x: Optional[float], y: Optional[float], width: int = 800, height: int = 1000
) -> Tuple[float, float]:
    """Beregner spillerens posisjon på banen.

    Args:
        x: X-koordinat i prosent (0-100)
        y: Y-koordinat i prosent (0-100)
        width: Banens bredde i piksler
        height: Banens høyde i piksler

    Returns:
        Tuple med (x,y) koordinater i piksler
    """
    margin = 50

    # Hvis x eller y er None, returner midtpunktet av banen
    if x is None or y is None:
        return width / 2, height / 2

    # Beregn x-koordinat med margin
    ny_x = margin + (x / 100) * (width - 2 * margin)

    # Beregn y-koordinat med margin
    # Juster y for å unngå overlapp med 16-meter
    ny_y = margin + (y / 100) * (height - 2 * margin)

    return ny_x, ny_y


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
                    COALESCE(ss.er_paa, 0) as er_paa
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
                spiller = {"id": row[0], "navn": row[1].strip(), "posisjon_index": None}

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
    periode_tekst = (
        f"Periode {periode['id'] + 1} " f"({periode['start']} - {periode['slutt']})"
    )

    spillere_html = "".join(
        f"<tr><td>{s['navn']}</td><td>{s['posisjon']}</td></tr>" for s in spillere
    )

    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ padding: 20px; }}
            .field-container {{ margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 8px; border: 1px solid #ddd; }}
            th {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Kampformasjon</h1>
            <h2>{kamp_info['hjemmelag']} vs {kamp_info['bortelag']}</h2>
            <h3>{periode_tekst}</h3>

            <div class="field-container">
                {fotballbane_html}
            </div>

            <h3>Spillere på banen</h3>
            <table>
                <tr>
                    <th>Navn</th>
                    <th>Posisjon</th>
                </tr>
                {spillere_html}
            </table>
        </div>
    </body>
    </html>
    """


def valider_spillerposisjoner(spillerposisjoner: dict) -> Tuple[bool, str]:
    """Validerer spillerposisjoner før lagring."""
    if not isinstance(spillerposisjoner, dict):
        return False, "Ugyldig format på spillerposisjoner"

    for spiller_id, posisjon in spillerposisjoner.items():
        if not isinstance(posisjon, dict):
            return False, f"Ugyldig posisjonsformat for spiller {spiller_id}"

        x = posisjon.get("x")
        y = posisjon.get("y")

        if x is None or y is None:
            return False, f"Mangler x/y koordinater for spiller {spiller_id}"

        try:
            x_float = float(x)
            y_float = float(y)
            if not (0 <= x_float <= 100 and 0 <= y_float <= 100):
                return (
                    False,
                    f"Koordinater utenfor gyldig område for spiller {spiller_id}",
                )
        except ValueError:
            return False, f"Ugyldige koordinatverdier for spiller {spiller_id}"

    return True, ""


def lagre_banekart(
    app_handler: AppHandler, kamp_id: int, periode_id: int, spillerposisjoner: dict
) -> bool:
    """Lagrer banekart med spillerposisjoner for en gitt kamp og periode."""
    logger.debug("=== START LAGRE BANEKART ===")
    logger.debug("Input parametre:")
    logger.debug("- kamp_id: %s (type: %s)", kamp_id, type(kamp_id))
    logger.debug("- periode_id: %s (type: %s)", periode_id, type(periode_id))
    logger.debug("- spillerposisjoner: %s", json.dumps(spillerposisjoner, indent=2))

    # Valider bruker_id
    bruker_id_str = st.query_params.get("bruker_id")
    if not bruker_id_str:
        logger.error("FEIL: Ingen bruker innlogget")
        st.error("Du må være innlogget for å lagre formasjon")
        return False

    try:
        bruker_id = int(bruker_id_str)
    except ValueError:
        logger.error("FEIL: Ugyldig bruker_id format: %s", bruker_id_str)
        st.error("Ugyldig bruker-ID")
        return False

    # Valider input
    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("FEIL: Ugyldig kamp_id: %s", kamp_id)
        st.error("Ugyldig kamp-ID")
        return False

    if not isinstance(periode_id, int) or periode_id < 0:
        logger.error("FEIL: Ugyldig periode_id: %s", periode_id)
        st.error("Ugyldig periode-ID")
        return False

    # Valider spillerposisjoner
    er_gyldig, feilmelding = valider_spillerposisjoner(spillerposisjoner)
    if not er_gyldig:
        logger.error("FEIL: %s", feilmelding)
        st.error(f"Kunne ikke lagre posisjoner: {feilmelding}")
        return False

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            logger.debug("Database tilkobling opprettet")

            # Start transaksjon
            cursor.execute("BEGIN TRANSACTION")
            logger.debug("Transaksjon startet")

            try:
                # Sjekk om kamp eksisterer og tilhører brukeren
                cursor.execute(
                    """SELECT id FROM kamper
                    WHERE id = ? AND bruker_id = ?""",
                    (kamp_id, bruker_id),
                )
                kamp = cursor.fetchone()
                if not kamp:
                    error_msg = (
                        "FEIL: Kamp med ID %s finnes ikke eller "
                        "tilhører ikke bruker %s"
                    )
                    logger.error(error_msg, kamp_id, bruker_id)
                    conn.rollback()
                    st.error("Du har ikke tilgang til denne kampen")
                    return False

                # Slett eventuelle eksisterende posisjoner
                logger.debug("Sletter eksisterende posisjoner...")
                cursor.execute(
                    """DELETE FROM banekart
                    WHERE kamp_id = ? AND periode_id = ?""",
                    (kamp_id, periode_id),
                )
                logger.debug(
                    "Eksisterende posisjoner slettet. Antall rader påvirket: %d",
                    cursor.rowcount,
                )

                # Lagre nye posisjoner
                logger.debug("Lagrer nye posisjoner...")
                spillerposisjoner_json = json.dumps(spillerposisjoner)
                logger.debug("JSON som skal lagres: %s", spillerposisjoner_json)

                cursor.execute(
                    """INSERT INTO banekart (
                        kamp_id,
                        periode_id,
                        spillerposisjoner,
                        opprettet_dato,
                        sist_oppdatert
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    (kamp_id, periode_id, spillerposisjoner_json),
                )
                logger.debug("SQL INSERT utført")

                # Verifiser at dataene ble lagret
                cursor.execute(
                    """SELECT spillerposisjoner
                    FROM banekart
                    WHERE kamp_id = ? AND periode_id = ?""",
                    (kamp_id, periode_id),
                )
                lagret_data = cursor.fetchone()
                if not lagret_data:
                    logger.error("FEIL: Data ble ikke funnet etter lagring")
                    conn.rollback()
                    st.error("Kunne ikke verifisere lagrede data")
                    return False

                logger.debug("Verifisert lagret data: %s", lagret_data[0])

                # Commit transaksjon
                conn.commit()
                logger.info(
                    "Banekart lagret for kamp %s, periode %s", kamp_id, periode_id
                )
                logger.debug("=== SLUTT LAGRE BANEKART (SUKSESS) ===")
                st.success("Posisjoner lagret")
                return True

            except Exception as e:
                conn.rollback()
                logger.error("FEIL ved lagring av banekart: %s", str(e))
                logger.error("Exception type: %s", type(e).__name__)
                logger.error("Stack trace:", exc_info=True)
                logger.debug("=== SLUTT LAGRE BANEKART (FEILET) ===")
                st.error("Kunne ikke lagre posisjoner")
                return False

    except Exception as e:
        logger.error("KRITISK FEIL ved database operasjon: %s", str(e))
        logger.error("Exception type: %s", type(e).__name__)
        logger.error("Stack trace:", exc_info=True)
        logger.debug("=== SLUTT LAGRE BANEKART (FEILET) ===")
        st.error("En feil oppstod ved lagring")
        return False


def hent_banekart(
    app_handler: AppHandler, kamp_id: int, periode_id: int
) -> Optional[Dict[str, Dict[str, float]]]:
    """Henter lagret banekart for en gitt kamp og periode.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID for kampen
        periode_id: ID for perioden

    Returns:
        Optional[Dict[str, Dict[str, float]]]: Spillerposisjoner hvis funnet,
        ellers None
    """
    logger.debug("=== Start hent_banekart ===")
    logger.debug("Input parametre:")
    logger.debug("- kamp_id: %s (type: %s)", kamp_id, type(kamp_id))
    logger.debug("- periode_id: %s (type: %s)", periode_id, type(periode_id))

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            logger.debug("Database tilkobling opprettet")

            cursor.execute(
                """SELECT spillerposisjoner
                FROM banekart
                WHERE kamp_id = ? AND periode_id =?""",
                (kamp_id, periode_id),
            )
            logger.debug("SQL spørring utført")

            row = cursor.fetchone()
            if not row:
                msg = (
                    f"Ingen banekart funnet for kamp {kamp_id}, "
                    f"periode {periode_id}"
                )
                logger.info(msg)
                logger.debug("=== Slutt hent_banekart (ingen data) ===")
                return None

            posisjoner = json.loads(row[0])
            pos_str = json.dumps(posisjoner, indent=2)
            logger.debug("Hentet posisjoner: %s", pos_str)
            logger.debug("=== Slutt hent_banekart (suksess) ===")
            return posisjoner

    except Exception as e:
        logger.error("Feil ved henting av banekart: %s", str(e))
        logger.error("Exception type: %s", type(e).__name__)
        logger.exception("Full feilmelding:")
        logger.debug("=== Slutt hent_banekart (feilet) ===")
        return None


def vis_periodevis_oversikt(app_handler: AppHandler, kamp_id: int) -> None:
    """Viser oversikt over formasjoner per periode."""
    # Hent kampinnstillinger først
    _, antall_perioder, _ = _hent_kampinnstillinger(app_handler, kamp_id)

    perioder = []
    for i in range(antall_perioder):
        perioder.append(
            {
                "id": i,
                "start": "Start",
                "slutt": "Slutt",
                "beskrivelse": f"Periode {i + 1}",
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
            cursor: grab;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            touch-action: none;
            z-index: 1000;
            background-color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: black;
            transition: transform 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
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
            z-index: 1001;
            cursor: grabbing;
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
        paa_banen, paa_benken = hent_alle_spillere_for_periode(
            app_handler, periode["id"], kamp_id
        )

        # Oppdater spillerdata med status for denne perioden
        for spiller in paa_banen + paa_benken:
            if spiller["navn"] not in spillere:
                spillere[spiller["navn"]] = {"perioder": {}}
            spillere[spiller["navn"]]["perioder"][periode["id"]] = spiller in paa_banen

    # Debug logging
    logger.debug("Komplett spillerdata for alle perioder: %s", spillere)

    for periode in perioder:
        periode_tekst = (
            f"Periode {periode['id'] + 1} " f"({periode['start']} - {periode['slutt']})"
        )
        with st.expander(periode_tekst, expanded=True):
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
                bytter_inn, bytter_ut = hent_bytter(spillere, periode_id)
                bytter_tekst = formater_bytter(bytter_inn, bytter_ut)
                if bytter_tekst != "-":
                    st.info(f"Bytter denne perioden: {bytter_tekst}")

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

            with col2:
                # Legg til lagre-knapp for hver periode
                if st.button("Lagre formasjon", key=f"lagre_{periode['id']}"):
                    logger.debug(
                        "Lagre formasjon knapp trykket for periode %s", periode["id"]
                    )
                    try:
                        if lagre_grunnformasjon(
                            app_handler, kamp_id, selected_formation
                        ):
                            logger.info(
                                "Formasjon lagret for periode %s: %s",
                                periode["id"],
                                selected_formation,
                            )
                            st.success("Formasjon lagret")
                            st.rerun()
                        else:
                            logger.error(
                                "Kunne ikke lagre formasjon for periode %s",
                                periode["id"],
                            )
                            st.error("Kunne ikke lagre formasjon")
                    except Exception as e:
                        logger.error(
                            "Feil ved lagring av formasjon for periode %s: %s",
                            periode["id"],
                            str(e),
                        )
                        logger.exception("Full feilmelding:")
                        st.error("Kunne ikke lagre formasjon")

            if selected_formation:
                # Sjekk om vi har mottatt posisjonsdata
                banekart_data = st.query_params.get(f"banekart_{periode_id}")
                if banekart_data:
                    try:
                        data = json.loads(banekart_data)
                        logger.debug("Mottok data fra JavaScript: %s", data)

                        if isinstance(data, dict) and data.get("type") == "banekart":
                            posisjoner = data.get("posisjoner", {})
                            logger.debug("Posisjoner fra JavaScript: %s", posisjoner)

                            if posisjoner:
                                success = lagre_banekart(
                                    app_handler, kamp_id, periode_id, posisjoner
                                )
                                if success:
                                    st.success("Posisjoner lagret")
                                    # Fjern query parameter og oppdater siden
                                    del st.query_params[f"banekart_{periode_id}"]
                                    st.rerun()
                                else:
                                    st.error("Kunne ikke lagre posisjoner")
                            else:
                                st.warning("Ingen posisjoner å lagre")
                    except json.JSONDecodeError as e:
                        logger.error("Ugyldig JSON-data: %s", e)
                        st.error("Ugyldig data mottatt")

                # Vis fotballbanen med spillere
                posisjoner = formations[selected_formation]["posisjoner"]

                # Hent lagret banekart hvis det finnes
                lagret_banekart = hent_banekart(app_handler, kamp_id, periode_id)

                # Konverter spillere til SpillerPosisjon format
                spillere_paa_banen: List[SpillerPosisjon] = []
                for spiller in paa_banen:
                    spiller_posisjon: SpillerPosisjon = {
                        "id": spiller["id"],
                        "navn": spiller["navn"],
                        "posisjon_index": None,
                        "posisjon": None,
                    }

                    # Hvis vi har lagret banekart, bruk de lagrede posisjonene
                    if lagret_banekart:
                        for spiller_id, posisjon in lagret_banekart.items():
                            if str(spiller["id"]) == str(spiller_id):
                                spiller_posisjon["posisjon"] = posisjon

                    spillere_paa_banen.append(spiller_posisjon)

                fotballbane = lag_fotballbane_html(
                    posisjoner=posisjoner,
                    spillere=spillere_paa_banen,
                    spillere_paa_benken=paa_benken,
                    kamp_id=int(kamp_id),
                    periode_id=periode_id,
                )
                components.html(fotballbane, height=1000)


def sett_opp_startoppstilling(app_handler: AppHandler, kamp_id: int) -> bool:
    """Setter opp startoppstillingen (periode 0) med de første 11 spillerne i kamptroppen."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Hent de første 11 spillerne fra kamptroppen
            cursor.execute(
                """
                SELECT s.id, s.navn
                FROM spillere s
                JOIN kamptropp kt ON s.id = kt.spiller_id
                WHERE kt.kamp_id = ? AND kt.er_med = 1
                ORDER BY s.navn
                LIMIT 11
            """,
                (kamp_id,),
            )

            spillere = cursor.fetchall()

            if len(spillere) < 11:
                logger.error("Ikke nok spillere i kamptroppen")
                return False

            # Slett eventuelle eksisterende oppføringer for periode 0
            cursor.execute(
                """
                DELETE FROM spillere_i_periode
                WHERE kamp_id = ? AND periode_id = 0
            """,
                (kamp_id,),
            )

            # Sett opp startoppstillingen
            for spiller_id, navn in spillere:
                cursor.execute(
                    """
                    INSERT INTO spillere_i_periode (
                        kamp_id, periode_id, spiller_id, er_paa, sist_oppdatert
                    ) VALUES (?, 0, ?, 1, CURRENT_TIMESTAMP)
                """,
                    (kamp_id, spiller_id),
                )

            conn.commit()
            logger.info("Startoppstilling satt opp for kamp %s", kamp_id)
            return True

    except Exception as e:
        logger.error("Feil ved oppsett av startoppstilling: %s", str(e))
        return False


def get_bruker_id() -> int:
    """Henter bruker ID fra query parameters."""
    bruker_id_str = st.query_params.get("bruker_id")
    if not bruker_id_str:
        st.error("Ingen bruker innlogget")
        st.stop()

    try:
        return int(bruker_id_str)
    except ValueError as e:
        st.error(f"Ugyldig bruker ID format: {bruker_id_str}")
        logger.error("Konvertering av bruker_id feilet: %s", e)
        st.stop()


def vis_formasjon_side(app_handler: AppHandler) -> None:
    """Viser formasjonssiden."""
    try:
        logger.debug("=== Start vis_formasjon_side ===")
        logger.debug("Sjekker query params og bruker...")

        # Hent kamp_id fra query params
        kamp_id_str = st.query_params.get("kamp_id")
        logger.debug("Hentet kamp_id fra query params: %s", kamp_id_str)

        if not kamp_id_str:
            logger.error("Ingen kamp_id i query params")
            st.error("Ingen kamp valgt")
            return

        try:
            kamp_id = int(kamp_id_str)
            logger.debug("Konvertert kamp_id til int: %d", kamp_id)
        except ValueError:
            logger.error("Ugyldig kamp_id format: %s", kamp_id_str)
            st.error("Ugyldig kamp ID")
            return

        # Hent tilgjengelige formasjoner
        try:
            formations = get_available_formations()
            logger.debug("Hentet %d tilgjengelige formasjoner", len(formations))
            for form in formations:
                logger.debug("Tilgjengelig formasjon: %s", form)
        except Exception as e:
            logger.error("Feil ved henting av formasjoner: %s", str(e))
            st.error("Kunne ikke hente formasjoner")
            return

        # Hent lagret formasjon
        lagret_formasjon = hent_grunnformasjon(app_handler, kamp_id)
        logger.debug("Hentet lagret formasjon: %s", lagret_formasjon)

        # Finn index for lagret formasjon
        formasjon_index = (
            list(formations.keys()).index(lagret_formasjon) if lagret_formasjon else 0
        )
        logger.debug("Bruker formasjon index: %d", formasjon_index)

        # Vis formasjonsvelger
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_formation = st.selectbox(
                "Velg formasjon",
                options=list(formations.keys()),
                index=formasjon_index,
            )
            logger.debug("Valgt formasjon: %s", selected_formation)

        with col2:
            logger.debug("Setter opp 'Lagre som grunnformasjon' knapp")
            if st.button("Lagre som grunnformasjon"):
                logger.debug("Lagre grunnformasjon knapp trykket")
                try:
                    logger.debug(
                        "Forsøker å lagre grunnformasjon: %s", selected_formation
                    )
                    if lagre_grunnformasjon(app_handler, kamp_id, selected_formation):
                        logger.info("Grunnformasjon lagret: %s", selected_formation)
                        st.success("Grunnformasjon lagret")
                        logger.debug("Starter rerun etter vellykket lagring")
                        st.rerun()
                    else:
                        logger.error("lagre_grunnformasjon returnerte False")
                        st.error("Kunne ikke lagre grunnformasjon")
                except Exception as e:
                    logger.error("Feil ved lagring av grunnformasjon: %s", str(e))
                    logger.error("Exception type: %s", type(e).__name__)
                    logger.exception("Full feilmelding:")
                    st.error("Kunne ikke lagre grunnformasjon")

        # Vis periodevis oversikt
        logger.debug("Starter visning av periodevis oversikt")
        vis_periodevis_oversikt(app_handler, kamp_id)
        logger.debug("Periodevis oversikt vist for kamp %s", kamp_id)

    except Exception as e:
        logger.error("Uventet feil i vis_formasjon_side: %s", str(e))
        logger.error("Exception type: %s", type(e).__name__)
        logger.exception("Full feilmelding:")
        st.error("En uventet feil oppstod")
    finally:
        logger.debug("=== Slutt vis_formasjon_side ===")


def vis_formation_page(app_handler: AppHandler):
    """Viser formasjonssiden."""
    try:
        # Sjekk autentisering og behold bruker_id
        bruker_id = st.query_params.get("bruker_id")
        if not check_auth(app_handler.auth_handler):
            return

        st.header("Formasjon")

        # Hent kamp ID fra query parameters
        kamp_id = st.query_params.get("kamp_id")
        if not kamp_id:
            st.warning("Velg en kamp først")
            if st.button("Gå til oppsett for å velge kamp"):
                st.query_params.clear()
                st.query_params["page"] = "oppsett"
                if bruker_id:
                    st.query_params["bruker_id"] = bruker_id
                st.rerun()
            return

        # Sett bruker_id tilbake i query params hvis den mangler
        if bruker_id and not st.query_params.get("bruker_id"):
            st.query_params["bruker_id"] = bruker_id

        # Vis formasjonssiden med app_handler
        vis_formasjon_side(app_handler)

    except Exception as e:
        logger.error("Feil ved visning av formasjon: %s", e)
        logger.exception("Full feilmelding:")
        st.error(f"En feil oppstod ved visning av formasjon: {str(e)}")


def lagre_grunnformasjon(app_handler: AppHandler, kamp_id: int, formasjon: str) -> bool:
    """Lagrer grunnformasjon for kampen og spillerposisjoner i banekartet."""
    try:
        logger.debug("=== Start lagre_grunnformasjon ===")
        logger.debug("Parametre: kamp_id=%s, formasjon=%s", kamp_id, formasjon)

        # Valider input
        if not isinstance(kamp_id, int) or kamp_id <= 0:
            logger.error(
                "Ugyldig kamp_id: %s (type: %s)",
                kamp_id,
                type(kamp_id)
            )
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
                    "Hentet %d posisjoner fra formasjon %s", len(posisjoner), formasjon
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
                        # Slett eksisterende posisjoner
                        cursor.execute(
                            "DELETE FROM banekart WHERE kamp_id = ? AND periode_id = 0",
                            (kamp_id,),
                        )
                        logger.debug("Slettet eksisterende posisjoner")

                        # Lagre nye posisjoner
                        cursor.execute(
                            """INSERT INTO banekart (
                                kamp_id,
                                periode_id,
                                spillerposisjoner,
                                opprettet_dato,
                                sist_oppdatert
                            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                            (kamp_id, 0, json.dumps(spillerposisjoner)),
                        )
                        logger.debug("Nye posisjoner lagret i banekart")

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
                SELECT nokkel, verdi
                FROM app_innstillinger
                WHERE (bruker_id = ? OR kamp_id = ?)
                AND nokkel IN (
                    'kamplengde',
                    'antall_perioder',
                    'antall_paa_banen'
                )
                ORDER BY kamp_id DESC
            """
            cursor.execute(sql, (bruker_id, kamp_id))

            # Konverter resultater til dict
            innstillinger = {}
            for row in cursor.fetchall():
                innstillinger[row[0]] = row[1]

            # Hent verdier med standardverdier
            kamplengde = int(innstillinger.get("kamplengde", 70))
            antall_perioder = int(innstillinger.get("antall_perioder", 7))
            antall_paa_banen = int(innstillinger.get("antall_paa_banen", 7))

            # Logg innstillingene
            logger.info(
                "Kampinnstillinger for kamp %d: " "lengde=%d, perioder=%d, spillere=%d",
                kamp_id,
                kamplengde,
                antall_perioder,
                antall_paa_banen,
            )
            return kamplengde, antall_perioder, antall_paa_banen

    except Exception as e:
        logger.error("Feil ved henting av kampinnstillinger: %s", str(e))
        logger.exception("Full feilmelding:")
        return 70, 7, 7


def hent_bytter_for_periode(
    app_handler: AppHandler, kamp_id: int, periode_id: int
) -> List[Dict[str, Any]]:
    """Henter alle bytter for en periode."""
    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Først hent alle endringer i perioden
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
                SELECT
                    s.navn,
                    e.er_paa,
                    e.sist_oppdatert
                FROM EndringerIPeriode e
                JOIN spillere s ON e.spiller_id = s.id
                WHERE (e.er_paa != e.forrige_status OR e.forrige_status IS NULL)
                ORDER BY e.sist_oppdatert
            """,
                (kamp_id, periode_id),
            )

            endringer = cursor.fetchall()
            bytter = []

            # Grupper endringer i inn/ut par
            for i in range(0, len(endringer), 2):
                ut = None
                inn = None

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
