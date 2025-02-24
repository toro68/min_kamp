# Min Kamp

## Prosjektoppsett

### Forutsetninger
- Python 3.9+
- pip
- virtualenv (valgfritt, men anbefalt)

### Installasjon

1. Klone repository:
```bash
git clone https://github.com/toro68/min_kamp.git
cd min_kamp
```

2. Opprett virtuelt miljø (valgfritt, men anbefalt):
```bash
python3 -m venv venv
source venv/bin/activate  # På macOS/Linux
# eller
venv\Scripts\activate  # På Windows
```

3. Installer prosjektet:
```bash
pip install -e .
```

### Kjøre Appen

```bash
streamlit run src/min_kamp/streamlit_app.py
```

## Utvikling

### Kjøre Tester
```bash
pytest
```

### Kodekvalitet
```bash
black .
flake8
mypy .
```

## Avhengigheter
Se `pyproject.toml` for full liste over avhengigheter.

## Lisens
[Angi lisens]
