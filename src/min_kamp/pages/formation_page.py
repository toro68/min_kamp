"""
Formasjon side.

Viser og administrerer formasjoner for en fotballkamp.
Støtter periodevis oversikt over spillerposisjoner og lagring av formasjoner.
"""

import json
import logging
import tempfile
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


def beregn_spiller_posisjon(
    x_percent: float, y_percent: float, width: int, height: int, margin: int = 50
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
        for spiller, pos in zip(spillere_liste, posisjoner):
            if not isinstance(pos, tuple) or len(pos) != 2:
                logger.warning(f"Ugyldig posisjon for spiller {spiller['id']}: {pos}")
                continue

            x, y = beregn_spiller_posisjon(pos[0], pos[1], width, height, margin)
            spillere_html += f"""
            <div class="spiller"
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
        _, antall_perioder, _ = _hent_kampinnstillinger(app_handler, kamp_id)
        periode_nummer = periode_id + 1  # Konverter til 1-basert

        # Bygg opp spillere dictionary på samme måte som i oversikten
        spillere: dict[str, dict[str, dict[int, bool]]] = {}
        for p_id in range(periode_id + 1):
            paa_banen_temp, paa_benken_temp = hent_alle_spillere_for_periode(
                app_handler, p_id, kamp_id
            )
            for spiller in paa_banen_temp + paa_benken_temp:
                if spiller["navn"] not in spillere:
                    spillere[spiller["navn"]] = {"perioder": {}}
                spillere[spiller["navn"]]["perioder"][p_id] = spiller in paa_banen_temp

        # Hent bytter for perioden på samme måte som i oversikten
        bytter_inn, bytter_ut = hent_bytter(spillere, periode_id)
        bytter_tekst = formater_bytter(bytter_inn, bytter_ut)

        # Lag periode_html med bytter-info
        periode_html = (
            '<div style="position:absolute;top:10px;left:10px;'
            "background-color:rgba(255,255,255,0.9);padding:5px 10px;"
            'border-radius:5px;font-weight:bold;z-index:1000">'
            "Periode {} (Start - Slutt)<br>"
            "Bytter denne perioden: {}"
            "</div>"
        ).format(periode_nummer, bytter_tekst)

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
                }}
                .spiller {{
                    position: absolute;
                    width: {0}px;
                    height: {0}px;
                    background-color: white;
                    border: 3px solid #1565C0;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: grab;
                    user-select: none;
                    font-size: 16px;
                    font-weight: bold;
                    z-index: 1000;
                }}
                .spiller:hover {{
                    transform: scale(1.1);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
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
            </style>
            <script>
            function getSpillerPosisjoner() {{
                const spillere = document.querySelectorAll('.spiller:not(.paa-benken)');
                const posisjoner = {{}};
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

                return posisjoner;
            }}

            function lagrePosisjoner() {{
                const posisjoner = getSpillerPosisjoner();
                const bane = document.querySelector('.fotballbane');
                const periode_id = bane.getAttribute('data-periode-id');

                console.log('Lagrer posisjoner:', {{ periode_id, posisjoner }});

                // Send data til Streamlit via URL-parameter
                const data = {{
                    periode_id: periode_id,
                    posisjoner: posisjoner
                }};

                // Oppdater URL med data
                const searchParams = new URLSearchParams(window.parent.location.search);
                searchParams.set('banekart_data', JSON.stringify(data));
                const newUrl = window.parent.location.pathname + '?' +
                    searchParams.toString();
                window.parent.history.pushState({{}}, '', newUrl);

                // Trigger en Streamlit rerun
                window.parent.postMessage({{
                    type: 'streamlit:setUrlInfo',
                    queryParams: Object.fromEntries(searchParams)
                }}, '*');
            }}

            document.addEventListener('DOMContentLoaded', function() {{
                const spillere = document.querySelectorAll('.spiller');
                let aktivSpiller = null;
                let startX = 0;
                let startY = 0;
                let offsetX = 0;
                let offsetY = 0;

                spillere.forEach(spiller => {{
                    spiller.addEventListener('mousedown', startDrag);
                    spiller.addEventListener('touchstart', startDrag);
                }});

                function startDrag(e) {{
                    e.preventDefault();
                    aktivSpiller = this;
                    aktivSpiller.classList.add('dragging');

                    if (e.type === 'mousedown') {{
                        startX = e.clientX;
                        startY = e.clientY;
                    }} else {{
                        startX = e.touches[0].clientX;
                        startY = e.touches[0].clientY;
                    }}

                    const style = window.getComputedStyle(aktivSpiller);
                    offsetX = parseFloat(style.left) || 0;
                    offsetY = parseFloat(style.top) || 0;

                    document.addEventListener('mousemove', drag);
                    document.addEventListener('touchmove', drag);
                    document.addEventListener('mouseup', stopDrag);
                    document.addEventListener('touchend', stopDrag);
                }}

                function drag(e) {{
                    if (!aktivSpiller) return;

                    let clientX, clientY;
                    if (e.type === 'mousemove') {{
                        clientX = e.clientX;
                        clientY = e.clientY;
                    }} else {{
                        clientX = e.touches[0].clientX;
                        clientY = e.touches[0].clientY;
                    }}

                    const dx = clientX - startX;
                    const dy = clientY - startY;

                    aktivSpiller.style.left = `${{offsetX + dx}}px`;
                    aktivSpiller.style.top = `${{offsetY + dy}}px`;
                }}

                function stopDrag() {{
                    if (aktivSpiller) {{
                        aktivSpiller.classList.remove('dragging');
                        aktivSpiller = null;
                        lagrePosisjoner();
                    }}

                    document.removeEventListener('mousemove', drag);
                    document.removeEventListener('touchmove', drag);
                    document.removeEventListener('mouseup', stopDrag);
                    document.removeEventListener('touchend', stopDrag);
                }}
            }});
            </script>
        </head>
        <body>
            <div class="fotballbane"
                 data-periode-id="{2}"
                 style="width: {3}px; height: {4}px;">
                {5}
                {6}
                <svg width="{3}" height="{4}">
                    <!-- Ytre ramme -->
                    <rect x="{1}" y="{1}"
                          width="{7}" height="{8}"
                          fill="none" stroke="white" stroke-width="2"/>

                    <!-- Midtlinje -->
                    <line x1="{1}" y1="{9}"
                          x2="{7}" y2="{9}"
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
    """.format(
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
    return html


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


def lag_pdf(
    app_handler: AppHandler,
    kamp_id: int,
    periode_id: int,
    fotballbane_html: str,
    spillere: List[Dict[str, Any]],
) -> Optional[str]:
    """Lager PDF med formasjon og spillerliste."""
    logger.debug("Genererer PDF for kamp %s, periode %s", kamp_id, periode_id)

    # Valider input og sjekk avhengigheter
    if not HAS_PDFKIT:
        error_msg = (
            "PDF-generering er ikke tilgjengelig. "
            "Installer wkhtmltopdf fra: https://wkhtmltopdf.org/downloads.html\n"
            "Deretter kjør: pip install pdfkit"
        )
        logger.error(error_msg)
        st.error(error_msg)
        return None

    if not isinstance(kamp_id, int) or kamp_id <= 0:
        logger.error("Ugyldig kamp_id: %s", kamp_id)
        return None

    if not isinstance(periode_id, int) or periode_id < 0:
        logger.error("Ugyldig periode_id: %s", periode_id)
        return None

    if not spillere:
        logger.error("Ingen spillere å inkludere i PDF")
        return None

    try:
        # Hent kampinfo
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT hjemmelag, bortelag, dato
                FROM kamper
                WHERE id = ?
            """,
                (kamp_id,),
            )
            kamp_data = cursor.fetchone()
            if not kamp_data:
                logger.error("Fant ikke kamp med ID %s", kamp_id)
                return None

            kamp_info = {
                "hjemmelag": kamp_data[0],
                "bortelag": kamp_data[1],
                "dato": kamp_data[2],
            }

        # Generer HTML
        html_content = generer_pdf_html(
            fotballbane_html,
            spillere,
            {"id": periode_id, "start": "Start", "slutt": "Slutt"},
            kamp_info,
        )

        # Konfigurer PDF-generering
        options = {"quiet": "", "encoding": "UTF-8", "enable-local-file-access": None}

        # Lag PDF
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False, mode="wb"
        ) as pdf_file:
            logger.debug("Genererer PDF til: %s", pdf_file.name)
            try:
                pdfkit.from_string(html_content, pdf_file.name, options=options)
                logger.info("PDF generert for kamp %s, periode %s", kamp_id, periode_id)
                return pdf_file.name
            except Exception as pdf_error:
                logger.error(
                    "Feil ved PDF-generering: %s\nHTML: %s",
                    str(pdf_error),
                    html_content[:500],  # Logg første 500 tegn av HTML
                )
                raise

    except Exception as e:
        logger.error("Feil ved generering av PDF: %s", e)
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


def vis_periodevis_oversikt(app_handler: AppHandler, kamp_id: int) -> None:
    """Viser oversikt over formasjoner per periode."""
    # Hent kampinnstillinger først
    _, antall_perioder, _ = _hent_kampinnstillinger(app_handler, kamp_id)

    # Sett aktiv periode fra URL eller bruk 0 som standard
    aktiv_periode_str = st.query_params.get("periode_id", "0")
    try:
        aktiv_periode = int(aktiv_periode_str)
    except ValueError:
        aktiv_periode = 0

    logger.debug("Aktiv periode: %d", aktiv_periode)

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
            width: 80px;
            height: 80px;
            background-color: white;
            border: 3px solid #1565C0;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: grab;
            user-select: none;
            font-size: 16px;
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
                # Sjekk om vi har mottatt posisjonsdata fra URL
                banekart_data_str = st.query_params.get("banekart_data")
                if banekart_data_str:
                    try:
                        banekart_data = json.loads(banekart_data_str)
                        logger.debug("Mottok data fra URL: %s", banekart_data)

                        if isinstance(banekart_data, dict):
                            try:
                                periode_id = int(banekart_data.get("periode_id", 0))
                                posisjoner = banekart_data.get("posisjoner", {})
                                logger.debug("Posisjoner fra URL: %s", posisjoner)

                                if posisjoner:
                                    success = lagre_banekart(
                                        app_handler, kamp_id, periode_id, posisjoner
                                    )
                                    if success:
                                        st.success("Posisjoner lagret")
                                        # Fjern data fra URL
                                        st.query_params.pop("banekart_data", None)
                                        st.rerun()
                                    else:
                                        st.error("Kunne ikke lagre posisjoner")
                                else:
                                    st.warning("Ingen posisjoner å lagre")
                            except ValueError as e:
                                logger.error("Ugyldig periode_id: %s", str(e))
                                st.error("Ugyldig periode ID")
                    except json.JSONDecodeError as e:
                        logger.error("Ugyldig JSON data: %s", str(e))
                        st.error("Ugyldig data mottatt")
                    except Exception as e:
                        logger.error("Feil ved håndtering av banekart data: %s", str(e))
                        st.error("Kunne ikke håndtere banekart data")

                    # Fjern data fra URL uansett
                    st.query_params.pop("banekart_data", None)

                # Vis fotballbanen med spillere
                posisjoner = formations[selected_formation]["posisjoner"]

                # Hent lagret banekart hvis det finnes
                lagret_banekart = hent_banekart(app_handler, kamp_id, periode_id)
                logger.debug("Hentet lagret banekart: %s", lagret_banekart)

                # Konverter spillere til SpillerPosisjon format og sett posisjoner
                spillere_paa_banen: List[SpillerPosisjon] = []
                brukte_posisjoner = 0

                for spiller in paa_banen:
                    spiller_posisjon: SpillerPosisjon = {
                        "id": spiller["id"],
                        "navn": spiller["navn"],
                        "posisjon_index": None,
                        "posisjon": None,
                    }

                    # Hvis vi har lagret banekart, bruk de lagrede posisjonene
                    if lagret_banekart and str(spiller["id"]) in lagret_banekart:
                        pos = lagret_banekart[str(spiller["id"])]
                        logger.debug(
                            "Bruker lagret posisjon for spiller %s: %s",
                            spiller["id"],
                            pos,
                        )
                        spiller_posisjon["posisjon"] = pos
                        x_percent = float(pos["x"])
                        y_percent = float(pos["y"])
                        posisjoner[brukte_posisjoner] = (x_percent, y_percent)
                    else:
                        logger.debug(
                            "Bruker standardposisjon %d for spiller %s",
                            brukte_posisjoner,
                            spiller["id"],
                        )

                    brukte_posisjoner += 1
                    spillere_paa_banen.append(spiller_posisjon)

                fotballbane = lag_fotballbane_html(
                    posisjoner=posisjoner,
                    spillere_liste=spillere_paa_banen,
                    spillere_paa_benken=paa_benken,
                    kamp_id=kamp_id,
                    periode_id=periode_id,
                    app_handler=app_handler,
                )

                # Oppdater URL med aktiv periode når fotballbane vises
                if periode["id"] == aktiv_periode:
                    st.query_params["periode_id"] = str(periode_id)

                components.html(fotballbane, height=1000)


def sett_opp_startoppstilling(app_handler: AppHandler, kamp_id: int) -> bool:
    """
    Setter opp startoppstillingen (periode 0) med de første 11 spillerne
    i kamptroppen.
    """
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

        # Sett opp event handler for banekart
        components.html(
            """
            <div id="banekart-container"></div>
            <script>
            function sendToStreamlit(data) {
                try {
                    console.log('Prøver å sende data:', data);
                    const event = new CustomEvent('streamlit:message', {
                        bubbles: true,
                        detail: { type: 'streamlit:banekart', data: data }
                    });
                    window.dispatchEvent(event);
                    console.log('Data sendt');
                } catch (error) {
                    console.error('Feil ved sending av data:', error);
                }
            }

            window.addEventListener('message', function(e) {
                if (e.data && e.data.type === 'streamlit:banekart') {
                    console.log('Mottok banekart data:', e.data);
                    sendToStreamlit(e.data.data);
                }
            });
            </script>
            """,
            height=0,
        )

        # Håndter banekart event
        if "component_value" in st.session_state:
            banekart_data = st.session_state.component_value
            logger.debug("Mottok banekart data i session state: %s", banekart_data)

            try:
                if isinstance(banekart_data, dict):
                    periode_id = int(banekart_data.get("periode_id", 0))
                    posisjoner = banekart_data.get("posisjoner", {})

                    if posisjoner:
                        logger.debug(
                            "Lagrer posisjoner for periode %d: %s",
                            periode_id,
                            posisjoner,
                        )
                        success = lagre_banekart(
                            app_handler, kamp_id, periode_id, posisjoner
                        )
                        if success:
                            logger.info("Posisjoner lagret for periode %d", periode_id)
                            st.success("Posisjoner lagret")
                            del st.session_state["component_value"]
                            st.rerun()
                        else:
                            logger.error(
                                "Kunne ikke lagre posisjoner for periode %d", periode_id
                            )
                            st.error("Kunne ikke lagre posisjoner")
                    else:
                        logger.warning("Ingen posisjoner å lagre")
            except Exception as e:
                logger.error("Feil ved håndtering av banekart data: %s", str(e))
                st.error("Kunne ikke håndtere banekart data")

            # Fjern data fra URL uansett
            st.query_params.pop("banekart_data", None)

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


def lagre_banekart(
    app_handler: AppHandler, kamp_id: int, periode_id: int, spillerposisjoner: dict
) -> bool:
    """Lagrer banekart med spillerposisjoner for en gitt kamp og periode."""
    logger.debug("=== START LAGRE BANEKART ===")
    logger.debug("Input parametre:")
    logger.debug("- kamp_id: %s (type: %s)", kamp_id, type(kamp_id))
    logger.debug("- periode_id: %s (type: %s)", periode_id, type(periode_id))
    logger.debug("- spillerposisjoner: %s", json.dumps(spillerposisjoner, indent=2))

    try:
        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            logger.debug("Database tilkobling opprettet")

            # Start transaksjon
            cursor.execute("BEGIN TRANSACTION")
            logger.debug("Transaksjon startet")

            try:
                # Sjekk om kamp eksisterer
                cursor.execute("SELECT id FROM kamper WHERE id = ?", (kamp_id,))
                kamp = cursor.fetchone()
                if not kamp:
                    logger.error("FEIL: Kamp med ID %s finnes ikke", kamp_id)
                    conn.rollback()
                    return False
                logger.debug("Kamp funnet: %s", kamp)

                # Valider spillerposisjoner
                if not isinstance(spillerposisjoner, dict):
                    logger.error(
                        "FEIL: Ugyldig spillerposisjoner format: %s (type: %s)",
                        spillerposisjoner,
                        type(spillerposisjoner),
                    )
                    conn.rollback()
                    return False

                # Sjekk at alle spillere har gyldige posisjoner
                logger.debug("Validerer spillerposisjoner...")
                for spiller_id, posisjon in spillerposisjoner.items():
                    logger.debug(
                        "Validerer spiller %s: %s",
                        spiller_id,
                        json.dumps(posisjon, indent=2),
                    )

                    if not isinstance(posisjon, dict):
                        logger.error(
                            "FEIL: Ugyldig posisjonsformat for spiller %s: %s",
                            spiller_id,
                            posisjon,
                        )
                        conn.rollback()
                        return False

                    x = posisjon.get("x")
                    y = posisjon.get("y")

                    if x is None or y is None:
                        logger.error(
                            "FEIL: Mangler x/y koordinater for spiller %s: %s",
                            spiller_id,
                            posisjon,
                        )
                        conn.rollback()
                        return False

                    try:
                        x_float = float(x)
                        y_float = float(y)
                        logger.debug(
                            "Koordinater for spiller %s: x=%f, y=%f",
                            spiller_id,
                            x_float,
                            y_float,
                        )

                        if not (0 <= x_float <= 100 and 0 <= y_float <= 100):
                            logger.error(
                                "FEIL: Koordinater utenfor gyldig område (0-100) "
                                "for spiller %s: x=%f, y=%f",
                                spiller_id,
                                x_float,
                                y_float,
                            )
                            conn.rollback()
                            return False
                    except ValueError as e:
                        logger.error(
                            "FEIL: Kunne ikke konvertere koordinater til float "
                            "for spiller %s: %s",
                            spiller_id,
                            str(e),
                        )
                        conn.rollback()
                        return False

                logger.debug("Alle spillerposisjoner validert OK")

                # Slett eventuelle eksisterende posisjoner
                logger.debug("Sletter eksisterende posisjoner...")
                cursor.execute(
                    """DELETE FROM banekart
                    WHERE kamp_id = ? AND periode_id =?""",
                    (kamp_id, periode_id),
                )
                logger.debug(
                    "Eksisterende posisjoner slettet. " "Antall rader påvirket: %d",
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
                    WHERE kamp_id = ? AND periode_id =?""",
                    (kamp_id, periode_id),
                )
                lagret_data = cursor.fetchone()
                if not lagret_data:
                    logger.error("FEIL: Data ble ikke funnet etter lagring")
                    conn.rollback()
                    return False

                logger.debug("Verifisert lagret data: %s", lagret_data[0])

                # Commit transaksjon
                conn.commit()
                logger.info(
                    "Banekart lagret for kamp %s, periode %s", kamp_id, periode_id
                )
                logger.debug("=== SLUTT LAGRE BANEKART (SUKSESS) ===")
                return True

            except Exception as e:
                conn.rollback()
                logger.error("FEIL ved lagring av banekart: %s", str(e))
                logger.error("Exception type: %s", type(e).__name__)
                logger.error("Stack trace:", exc_info=True)
                logger.debug("=== SLUTT LAGRE BANEKART (FEILET) ===")
                return False

    except Exception as e:
        logger.error("KRITISK FEIL ved database operasjon: %s", str(e))
        logger.error("Exception type: %s", type(e).__name__)
        logger.error("Stack trace:", exc_info=True)
        logger.debug("=== SLUTT LAGRE BANEKART (FEILET) ===")
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
