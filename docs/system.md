# Kampplanleggingsapp - Systembeskrivelse

## Formål
Appen er utviklet for å forenkle kampplanlegging i lagidrett, med fokus på:
- Administrasjon av spillertropp
- Planlegging av bytter under kamp
- Oppfølging av spilletid
- Eksport av kampdata

## Systemarkitektur

### Frontend
- **Streamlit-basert UI** med følgende hovedsider:
  - Oppsett (kampkonfigurasjon)
  - Kamptropp (velge spillere)
  - Bytteplan (administrere bytter)

### Backend
- **SQLite database** med følgende hovedtabeller:
  - spillertropp
  - kamp
  - kamptropp
  - bytteplan
  - lagrede_bytteplan
  - sist_brukte_kamptropp
  - users

### Autentisering
- Innloggingssystem med brukervalidering via auth_handler
- Sesjonsbasert autentisering via Streamlit
- Sikker passordhåndtering med kryptering
- Post-autentisering dataflyt:
  1. Brukervalidering
  2. Session initialisering
  3. Lasting av brukerdata
  4. Lasting av aktiv kamp

### Hovedfunksjonalitet

#### 1. Spilleradministrasjon
- Registrering av spillere med navn og posisjon
- Støtte for standard posisjoner (Keeper, Forsvar, Midtbane, Angrep)
- Automatisk lagring av sist brukte kamptropp

#### 2. Kampplanlegging
- Konfigurerbar kamptid (20-90 min)
- Fleksibel periodeinndeling (5/10/15 min)
- Automatisk beregning av antall perioder
- Validering av minimum/maksimum spillere på banen

#### 3. Bytteplanlegging
- Visuell oversikt over bytter per periode
- Automatisk validering av antall spillere på banen
- Posisjonsoversikt per periode
- Sanntidsoppdatering av spilletid
- Lagring av bytteplan for gjenbruk
- Oversikt over spillere på banen sortert etter posisjon:
  - Keeper
  - Forsvar
  - Midtbane
  - Angrep
  - Benk
- Pandas-basert visning av aktive spillere

#### 4. State Håndtering
- Sentralisert state management via StateHandler
  - Typehåndtering for session state verdier:
    - authenticated: bool
    - user_id: int
    - kamptid: int
    - antall_paa_banen: int
  - Automatisk typekonvertering ved initialisering
  - Validering av verdityper

#### 5. Logging og Debugging
- Detaljert session state tracking
- Automatisk stack trace for feil
- Separate loggfiler per komponent
- Roterende loggfiler (10MB maks)
- Ytelseslogging med tidtaking
- Funksjonskall-logging via dekoratører

## Teknisk Stack
- Python 3.9+
- Streamlit 1.40.1
- SQLite3
- pandas for dataanalyse
- Streamlit-Authenticator
- Logging med Python logging

### Prosjektstruktur
- src/
  - auth/ (autentisering)
    - auth_handler.py
    - auth_views.py
  - config/ (konfigurasjon)
    - constants.py
    - settings.py
  - database/ (databasehåndtering)
    - db_config.py
    - db_handler.py
  - models/ (datamodeller)
    - bytteplan_model.py
    - kamp_model.py
    - spiller_model.py
  - pages/ (sidekomponenter)
    - components/
      - bytteplan_table.py
    - bytteplan_page.py
    - kamp_page.py
    - kamptropp_page.py
    - oppsett_page.py
  - utils/ (hjelpefunksjoner)
    - export.py
    - logger_utils.py
    - spilletid_analyse.py
    - spilletid_utils.py
    - validation.py
- tests/ (enhetstester)
- logs/ (loggfiler)
  - auth/
  - bytteplan/
  - database/
  - errors/
  - performance/
- data/ (databasefiler)
- eksport/ (eksporterte filer)

### Logging
- Separate logger for ulike komponenter:
  - bytteplan.log
  - errors.log
  - auth.log
  - database.log
  - performance.log

### Konfigurasjon
Miljøvariabler (.env):
- DATABASE_PATH
- SECRET_KEY
- LOG_LEVEL
- ADMIN_PASSWORD

### Kjente Begrensninger
1. Kun én aktiv kamp om gangen
2. Begrenset til predefinerte spillerposisjoner
3. Ingen offline-funksjonalitet
4. Enkelbruker-fokusert

### Vedlikehold
- Regelmessig backup av database
- Loggrotasjon
- Oppdatering av avhengigheter
- Enhetstesting ved endringer

### Kontaktinformasjon
For tekniske spørsmål eller feilrapportering, kontakt utviklingsteamet via GitHub issues.
