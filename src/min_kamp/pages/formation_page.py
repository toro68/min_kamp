"""
Formasjon side.

Viser og administrerer formasjoner for en fotballkamp.
Støtter periodevis oversikt over spillerposisjoner og lagring av formasjoner.
"""

import logging
import tempfile
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import streamlit as st
from streamlit.components.v1 import html

try:
    import pdfkit  # type: ignore

    # Sjekk om wkhtmltopdf er tilgjengelig
    options = {"quiet": ""}
    test_html = "<html><body>Test</body></html>"
    pdfkit.from_string(test_html, None, options=options)
    HAS_PDFKIT = True
except ImportError:
    HAS_PDFKIT = False
    logger = logging.getLogger(__name__)
    logger.warning("pdfkit er ikke installert. " "Installer med: pip install pdfkit")
except OSError:
    HAS_PDFKIT = False
    logger = logging.getLogger(__name__)
    logger.warning(
        "wkhtmltopdf er ikke installert eller ikke funnet i PATH. "
        "Installer wkhtmltopdf fra: https://wkhtmltopdf.org/downloads.html"
    )
except Exception as e:
    HAS_PDFKIT = False
    logger = logging.getLogger(__name__)
    logger.warning("Kunne ikke initialisere PDF-støtte: %s", str(e))

from min_kamp.db.auth.auth_views import check_auth
from min_kamp.db.handlers.app_handler import AppHandler
from min_kamp.db.utils.bytteplan_utils import formater_bytter, hent_bytter

logger = logging.getLogger(__name__)

POSISJONER = ["Keeper", "Forsvar", "Midtbane", "Angrep"]


class SpillerPosisjon(TypedDict):
    """Type for spiller med posisjon."""

    id: int
    navn: str
    posisjon_index: Optional[int]  # Settes av drag-and-drop


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
    posisjoner: List[Tuple[float, float]] = None,
    spillere: Optional[List[SpillerPosisjon]] = None,
    spillere_paa_benken: Optional[List[Dict[str, Any]]] = None,
    width: int = 800,
    height: int = 1000,
) -> str:
    margin = 50
    seksten_meter_hoyde = height * 0.15  # 15% av banens høyde
    seksten_meter_bredde = width * 0.5  # 50% av banens bredde
    bane_bredde = width - 2 * margin
    bane_hoyde = height - 2 * margin
    spiller_radius = 25  # Mindre sirkler
    bench_spacing = 60

    logger.debug(f"Bane dimensjoner: {width}x{height}, margin: {margin}")

    # Beregn x-posisjon for 16-meteren
    seksten_meter_x = margin + (bane_bredde - seksten_meter_bredde) / 2

    html = f"""
    <div style="width: {width+100}px; height: {height}px; position: relative; overflow: visible;">
    <svg width="{width}" height="{height}" style="background-color: #2e8b57;">
        <!-- Ytre ramme -->
        <rect x="{margin}" y="{margin}"
              width="{bane_bredde}" height="{bane_hoyde}"
              fill="none" stroke="white" stroke-width="2"/>

        <!-- Midtlinje -->
        <line x1="{margin}" y1="{height/2}"
              x2="{width-margin}" y2="{height/2}"
              stroke="white" stroke-width="2"/>

        <!-- Øvre 16-meter -->
        <rect x="{seksten_meter_x}" y="{margin}"
              width="{seksten_meter_bredde}" height="{seksten_meter_hoyde}"
              fill="none" stroke="white" stroke-width="2"/>

        <!-- Nedre 16-meter -->
        <rect x="{seksten_meter_x}" y="{height-margin-seksten_meter_hoyde}"
              width="{seksten_meter_bredde}" height="{seksten_meter_hoyde}"
              fill="none" stroke="white" stroke-width="2"/>
    """

    # Legg til posisjoner som stiplede sirkler
    if posisjoner:
        for i, (x, y) in enumerate(posisjoner):
            # Beregn faktiske koordinater basert på prosent
            px = margin + (x / 100) * bane_bredde
            py = margin + (y / 100) * bane_hoyde

            # Stiplet sirkel for posisjon
            html += f"""
            <circle class="empty-position" cx="{px}" cy="{py}" r="{spiller_radius}"
                    fill="none" stroke="white" stroke-width="2"
                    stroke-dasharray="5,5"/>
            """

    # Plasser alle spillere langs venstre sidelinje
    if spillere:
        start_y = margin + spiller_radius
        for i, spiller in enumerate(spillere):
            py = start_y + (i * bench_spacing)
            px = margin + spiller_radius  # Litt inn fra venstre kant

            html += f"""
            <g class="player" data-position="{spiller.get('posisjon_index', -1)}" data-player-id="{spiller['id']}">
                <circle cx="{px}" cy="{py}" r="{spiller_radius}"
                        fill="white" stroke="black" stroke-width="2"/>
                <text x="{px}" y="{py}"
                      text-anchor="middle" dy=".3em"
                      font-family="Arial" font-size="14px">
                    {spiller['navn']}
                </text>
            </g>
            """

    # Legg til spillere på benken langs høyre side
    if spillere_paa_benken:
        bench_start_x = width - margin - spiller_radius  # Høyre sidelinje
        for i, spiller in enumerate(spillere_paa_benken):
            bench_y = margin + (i * bench_spacing)
            html += f"""
            <g class="bench-player" data-player-id="{spiller['id']}">
                <circle cx="{bench_start_x}" cy="{bench_y}" r="{spiller_radius}"
                        fill="white" stroke="black" stroke-width="2"/>
                <text x="{bench_start_x}" y="{bench_y}"
                      text-anchor="middle" dy=".3em"
                      font-family="Arial" font-size="14px">
                    {spiller['navn']}
                </text>
            </g>
            """

    html += "</svg>"

    # Legg til JavaScript for drag-and-drop
    js = (
        """
    <script>
        const svg = document.querySelector('svg');
        let selectedElement = null;
        let originalPosition = null;
        let isDragging = false;
        let spillerPosisjoner = {};

        function getMousePosition(evt) {
            const CTM = svg.getScreenCTM();
            return {
                x: (evt.clientX - CTM.e) / CTM.a,
                y: (evt.clientY - CTM.f) / CTM.d
            };
        }

        function startDrag(evt) {
            const target = evt.target.closest('.player, .bench-player');
            if (target) {
                selectedElement = target;
                isDragging = true;
                const circle = selectedElement.querySelector('circle');
                const text = selectedElement.querySelector('text');

                // Lagre original posisjon
                originalPosition = {
                    cx: circle.getAttribute('cx'),
                    cy: circle.getAttribute('cy'),
                    x: text.getAttribute('x'),
                    y: text.getAttribute('y')
                };

                // Flytt elementet sist i SVG for å være øverst
                svg.appendChild(selectedElement);
            }
        }

        function drag(evt) {
            if (selectedElement && isDragging) {
                evt.preventDefault();
                const mousePos = getMousePosition(evt);
                const circle = selectedElement.querySelector('circle');
                const text = selectedElement.querySelector('text');

                // Oppdater posisjon for både sirkel og tekst
                circle.setAttribute('cx', mousePos.x);
                circle.setAttribute('cy', mousePos.y);
                text.setAttribute('x', mousePos.x);
                text.setAttribute('y', mousePos.y);
            }
        }

        function endDrag(evt) {
            if (selectedElement && isDragging) {
                isDragging = false;
                const mousePos = getMousePosition(evt);
                const emptyPositions = Array.from(
                    document.querySelectorAll('.empty-position')
                );

                let closestPosition = null;
                let minDistance = Infinity;

                // Finn nærmeste tomme posisjon
                emptyPositions.forEach((pos) => {
                    const cx = parseFloat(pos.getAttribute('cx'));
                    const cy = parseFloat(pos.getAttribute('cy'));
                    const distance = Math.sqrt(
                        Math.pow(cx - mousePos.x, 2) +
                        Math.pow(cy - mousePos.y, 2)
                    );

                    if (distance < minDistance) {
                        minDistance = distance;
                        closestPosition = pos;
                    }
                });

                if (closestPosition && minDistance < 50) {
                    // Flytt spiller til nærmeste posisjon
                    const circle = selectedElement.querySelector('circle');
                    const text = selectedElement.querySelector('text');
                    const cx = closestPosition.getAttribute('cx');
                    const cy = closestPosition.getAttribute('cy');

                    circle.setAttribute('cx', cx);
                    circle.setAttribute('cy', cy);
                    text.setAttribute('x', cx);
                    text.setAttribute('y', cy);

                    // Beregn prosentvis posisjon
                    const baneWidth = """
        + str(width - 2 * margin)
        + """;
                    const baneHeight = """
        + str(height - 2 * margin)
        + """;
                    const margin = """
        + str(margin)
        + """;

                    const xProsent = ((cx - margin) / baneWidth) * 100;
                    const yProsent = ((cy - margin) / baneHeight) * 100;

                    // Lagre spillerens posisjon
                    const spillerId = selectedElement.dataset.playerId;
                    spillerPosisjoner[spillerId] = {
                        x: xProsent,
                        y: yProsent
                    };

                    // Send oppdatering til Python
                    window.streamlit.setComponentValue({
                        type: 'posisjon_oppdatert',
                        spiller_id: spillerId,
                        posisjon: {x: xProsent, y: yProsent}
                    });
                } else {
                    // Flytt tilbake til original posisjon
                    const circle = selectedElement.querySelector('circle');
                    const text = selectedElement.querySelector('text');

                    circle.setAttribute('cx', originalPosition.cx);
                    circle.setAttribute('cy', originalPosition.cy);
                    text.setAttribute('x', originalPosition.x);
                    text.setAttribute('y', originalPosition.y);
                }

                selectedElement = null;
                originalPosition = null;
            }
        }

        svg.addEventListener('mousedown', startDrag);
        svg.addEventListener('mousemove', drag);
        svg.addEventListener('mouseup', endDrag);
        svg.addEventListener('mouseleave', endDrag);
    </script>
    """
    )

    return f"""
        {html}
        {js}
    </div>
    """


def beregn_spiller_posisjon(x, y, width=600, height=400):
    margin = 40
    # Juster y-koordinatene for å unngå overlapping med 16-meteren
    if y > 70:  # For spillere nær 16-meteren
        y = min(y, 85)  # Begrens hvor nær målet spillerne kan være

    ny_x = margin + (x / 100) * (width - 2 * margin)
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
    """Lagrer grunnformasjon for kampen."""
    try:
        bruker_id_str = st.query_params.get("bruker_id")
        if not bruker_id_str:
            logger.error("Ingen bruker innlogget")
            return False

        try:
            bruker_id = int(bruker_id_str)
        except (ValueError, TypeError):
            logger.error("Ugyldig bruker ID")
            return False

        logger.debug("Prøver å lagre grunnformasjon:")
        logger.debug("- Bruker ID: %s", bruker_id)
        logger.debug("- Kamp ID: %s", kamp_id)
        logger.debug("- Formasjon: %s", formasjon)

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Sjekk om tabellen har riktig struktur
            cursor.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='app_innstillinger'
            """)
            table_def = cursor.fetchone()
            logger.debug("Tabell definisjon: %s", table_def[0] if table_def else None)

            # Prøv å lagre
            sql = """
                INSERT OR REPLACE INTO app_innstillinger
                (kamp_id, bruker_id, nokkel, verdi)
                VALUES (?, ?, 'grunnformasjon', ?)
            """
            logger.debug("SQL: %s", sql)
            logger.debug("Parametre: (%s, %s, %s)", kamp_id, bruker_id, formasjon)

            cursor.execute(sql, (kamp_id, bruker_id, formasjon))
            conn.commit()
            logger.debug("Grunnformasjon lagret vellykket")
            return True

    except Exception as e:
        logger.error("Feil ved lagring av grunnformasjon: %s", e)
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
        st.warning("Ingen perioder funnet i bytteplanen. " "Opprett bytteplan først.")
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
        }
        .streamlit-expanderContent {
            height: auto !important;
            overflow: visible !important;
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

                if selected_formation:
                    # Hent lagret banekart hvis det finnes
                    lagret_banekart = hent_banekart(app_handler, kamp_id, periode_id)

                    # Konverter spillere til SpillerPosisjon format
                    spillere_paa_banen: List[SpillerPosisjon] = []
                    for spiller in paa_banen:
                        spiller_posisjon: SpillerPosisjon = {
                            "id": spiller["id"],
                            "navn": spiller["navn"],
                            "posisjon_index": None,
                        }

                        # Hvis vi har et lagret banekart, bruk det
                        spiller_id = str(spiller["id"])
                        if lagret_banekart and spiller_id in lagret_banekart:
                            spiller["posisjon"] = lagret_banekart[spiller_id]

                        spillere_paa_banen.append(spiller_posisjon)

                    # Vis fotballbanen med spillere
                    posisjoner = formations[selected_formation]["posisjoner"]
                    fotballbane = lag_fotballbane_html(
                        posisjoner=posisjoner,
                        spillere=spillere_paa_banen,
                        spillere_paa_benken=paa_benken,
                    )

                    # Vis banen og håndter callback
                    banekart_data = html(fotballbane, height=1100)

                    if banekart_data:
                        if isinstance(banekart_data, dict):
                            if banekart_data.get("type") == "posisjon_oppdatert":
                                spiller_id = banekart_data["spiller_id"]
                                posisjon = banekart_data["posisjon"]

                                # Oppdater spillerens posisjon
                                for spiller in paa_banen:
                                    if str(spiller["id"]) == spiller_id:
                                        spiller["posisjon"] = posisjon
                                        break

                    # Legg til Lagre banekart-knapp
                    lagre_key = f"lagre_banekart_{periode_id}"
                    if st.button("Lagre banekart", key=lagre_key):
                        # Samle alle posisjoner
                        posisjoner = {}
                        for spiller in paa_banen:
                            if "posisjon" in spiller:
                                posisjoner[str(spiller["id"])] = spiller["posisjon"]

                        # Lagre banekart
                        if posisjoner:
                            success = lagre_banekart(
                                app_handler, kamp_id, periode_id, posisjoner
                            )
                            if success:
                                st.success("Banekart lagret")
                            else:
                                st.error("Kunne ikke lagre banekart")
                        else:
                            st.warning(
                                "Ingen spillerposisjoner å lagre. "
                                "Plasser spillerne på banen først."
                            )


def vis_formasjon_side(app_handler: AppHandler) -> None:
    """Viser formasjonssiden med periodevis oversikt og grunnformasjon."""
    try:
        # Sjekk autentisering
        if not check_auth(app_handler.auth_handler):
            return

        st.header("Formasjon")

        # Hent kamp ID fra query parameters
        kamp_id = st.query_params.get("kamp_id")
        if not kamp_id:
            st.warning("Velg en kamp først")
            if st.button("Gå til oppsett for å velge kamp"):
                st.query_params["page"] = "oppsett"
                st.rerun()
            return

        # Vis grunnformasjon først
        st.subheader("Velg grunnformasjon")

        formations = get_available_formations()

        # Hent lagret grunnformasjon
        lagret_formasjon = hent_grunnformasjon(app_handler, int(kamp_id))

        # Finn index for lagret formasjon
        formasjon_index = (
            list(formations.keys()).index(lagret_formasjon) if lagret_formasjon else 0
        )

        selected_formation = st.selectbox(
            "Velg formasjon",
            options=list(formations.keys()),
            index=formasjon_index,
            format_func=lambda x: (
                f"{x} ({formations[x]['forsvar']}-"
                f"{formations[x]['midtbane']}-"
                f"{formations[x]['angrep']})"
            ),
            help="Velg ønsket grunnformasjon for laget",
        )

        if selected_formation:
            st.write(f"Valgt formasjon: {selected_formation}")
            st.write(f"Forsvar: {formations[selected_formation]['forsvar']}")
            st.write(f"Midtbane: {formations[selected_formation]['midtbane']}")
            st.write(f"Angrep: {formations[selected_formation]['angrep']}")

            # Vis fotballbanen med valgt formasjon
            fotballbane = lag_fotballbane_html(
                formations[selected_formation]["posisjoner"]
            )
            html(fotballbane, height=700)

            # Lagre grunnformasjon
            if st.button("Lagre som grunnformasjon"):
                success = lagre_grunnformasjon(
                    app_handler, int(kamp_id), selected_formation
                )
                if success:
                    st.success("Grunnformasjon lagret")
                else:
                    st.error("Kunne ikke lagre grunnformasjon")

        st.divider()

        # Vis periodevis oversikt
        st.subheader("Periodevis oversikt")
        vis_periodevis_oversikt(app_handler, int(kamp_id))

    except Exception as e:
        logger.error("Feil ved visning av formasjon: %s", e)
        st.error("En feil oppstod ved visning av formasjon")


def lagre_banekart(
    app_handler: AppHandler,
    kamp_id: int,
    periode_id: int,
    spillerposisjoner: Dict[str, Dict[str, float]],
) -> bool:
    """Lagrer banekart med spillerposisjoner for en periode.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID for kampen
        periode_id: ID for perioden
        spillerposisjoner: Dictionary med spiller-ID som nøkkel og posisjon som verdi
            Format: {'spiller_id': {'x': float, 'y': float}}

    Returns:
        bool: True hvis lagring var vellykket
    """
    try:
        bruker_id_str = st.query_params.get("bruker_id")
        if not bruker_id_str:
            logger.error("Ingen bruker innlogget")
            return False

        try:
            bruker_id = int(bruker_id_str)
        except (ValueError, TypeError):
            logger.error("Ugyldig bruker ID")
            return False

        # Valider input
        if not isinstance(kamp_id, int) or kamp_id <= 0:
            logger.error("Ugyldig kamp_id: %s", kamp_id)
            return False

        if not isinstance(periode_id, int) or periode_id < 0:
            logger.error("Ugyldig periode_id: %s", periode_id)
            return False

        if not spillerposisjoner:
            logger.error("Ingen spillerposisjoner å lagre")
            return False

        # Konverter til JSON-streng
        import json

        posisjoner_json = json.dumps(spillerposisjoner)

        # Lag unik nøkkel for denne perioden
        nokkel = f"banekart_periode_{periode_id}"

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()

            # Lagre i app_innstillinger
            sql = """
                INSERT OR REPLACE INTO app_innstillinger
                (kamp_id, bruker_id, nokkel, verdi)
                VALUES (?, ?, ?, ?)
            """

            cursor.execute(sql, (kamp_id, bruker_id, nokkel, posisjoner_json))
            conn.commit()

            logger.info("Banekart lagret for kamp %s, periode %s", kamp_id, periode_id)
            return True

    except Exception as e:
        logger.error("Feil ved lagring av banekart: %s", e)
        logger.exception("Full feilmelding:")
        return False


def hent_banekart(
    app_handler: AppHandler, kamp_id: int, periode_id: int
) -> Optional[Dict[str, Dict[str, float]]]:
    """Henter lagret banekart for en periode.

    Args:
        app_handler: AppHandler instans
        kamp_id: ID for kampen
        periode_id: ID for perioden

    Returns:
        Optional[Dict]: Banekart hvis funnet, ellers None
    """
    try:
        # Valider input
        if not isinstance(kamp_id, int) or kamp_id <= 0:
            logger.error("Ugyldig kamp_id: %s", kamp_id)
            return None

        if not isinstance(periode_id, int) or periode_id < 0:
            logger.error("Ugyldig periode_id: %s", periode_id)
            return None

        nokkel = f"banekart_periode_{periode_id}"

        with app_handler._database_handler.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT verdi
                FROM app_innstillinger
                WHERE kamp_id = ? AND nokkel = ?
            """,
                (kamp_id, nokkel),
            )

            row = cursor.fetchone()
            if not row:
                logger.info(
                    "Ingen banekart funnet for kamp %s, periode %s", kamp_id, periode_id
                )
                return None

            # Parse JSON
            import json

            try:
                banekart = json.loads(row[0])
                return banekart
            except json.JSONDecodeError as e:
                logger.error("Kunne ikke parse banekart JSON: %s", e)
                return None

    except Exception as e:
        logger.error("Feil ved henting av banekart: %s", e)
        logger.exception("Full feilmelding:")
        return None
