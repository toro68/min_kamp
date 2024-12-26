# Min Kamp

En Streamlit-applikasjon for håndtering av kamper og spillere.

## Beskrivelse

Min Kamp er et system for å:
- Administrere kamper og spilletid
- Håndtere spillerdata
- Generere bytteplaner
- Analysere kampstatistikk

## Teknisk Stack

- Python 3.9+
- Streamlit
- SQLAlchemy (database)
- Pandas (dataanalyse)
- JWT (autentisering)

## Installasjon

1. Klon repositoriet:
```bash
git clone [repo-url]
cd min_kamp
```

2. Opprett og aktiver virtuelt miljø:
```bash
python -m venv venv
source venv/bin/activate  # På Windows: venv\Scripts\activate
```

3. Installer avhengigheter:
```bash
pip install -e .  # Installerer pakken i utviklingsmodus
pip install -r requirements-dev.txt  # Installerer utviklingsavhengigheter
```

4. Sett opp miljøvariabler:
```bash
cp .env.example .env
# Rediger .env med dine innstillinger
```

## Kjøring

Start applikasjonen:
```bash
streamlit run streamlit_app.py
```

## Prosjektstruktur

```
min_kamp/
├── src/              # Kildekode
├── data/             # Data og eksporter
├── docs/             # Dokumentasjon
├── scripts/          # Hjelpeskript
├── logs/             # Logger
└── tests/            # Tester
```

## Utvikling

1. Installer utviklingsverktøy:
```bash
pre-commit install
```

2. Kjør tester:
```bash
pytest
```

3. Kjør linting:
```bash
mypy .
ruff .
```

## Lisens

[Din valgte lisens]
