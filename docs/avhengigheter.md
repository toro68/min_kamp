# Nødvendige filer for feilsøking av bytteplan

## Kjernefiler
- src/pages/bytteplan_page.py (hovedlogikk for bytteplan)
- src/database/db_handler.py (databasehåndtering)
- src/models/bytteplan_model.py (datamodell)
- src/utils/validation.py (valideringslogikk)
- src/utils/spilletid_utils.py (spilletidberegninger)
- src/utils/state_handler.py (Streamlit state håndtering)
- src/utils/spilletid_analyse.py (analyseverktøy)
- src/database/utils/bytteplan_utils.py (bytteplan-verktøy og lagring)

## Støttefiler
- src/models/__init__.py
- src/utils/__init__.py
- src/config/settings.py (logging oppsett)
- src/config/constants.py (konstanter)
- src/utils/logger_utils.py (logging)
- src/utils/export.py (eksport)

## Database
- data/kampdata.db (SQLite database)
- src/database/db_config.py (databasekonfigurasjon)
- src/database/queries/bytteplan_queries.sql
- src/database/queries/lagrede_bytteplan_queries.sql

## Logger
- logs/bytteplan/bytteplan.log (hovedlogg)
  - Session state tracking med typeinfo
  - Periodetilstand
  - Funksjonskall med argumenter
  - Kjøretidsstatistikk
  - Autentiseringsflyt-logging
  - State initialiserings-sekvenser
- logs/errors/error.log (feillogg med stack trace)
- logs/auth/auth.log (autentiseringslogg)
- logs/database/db.log (databasespørringer)
- logs/performance/perf.log (ytelsesmålinger)

## Logging Utils
- src/utils/logger_utils.py
  - BytteplanLogger (hovedlogger)
  - SessionStateHandler (state tracking)
  - log_function_call (dekoratør)
  - Detaljert formattering
  - Roterende loggfiler

## Tester
- tests/test_bytteplan.py
- tests/test_db_handler.py
- tests/test_validation.py
- tests/test_auth.py
- tests/test_config.py
- tests/test_database.py
- tests/test_pages.py
- tests/conftest.py

## Frontend
- src/main.py (hovedapplikasjon)
- streamlit_app.py (oppstartsscript)

## Dokumentasjon
- system.md (systemdokumentasjon)
- README.md (prosjektdokumentasjon)

## State Management
- src/utils/state_handler.py (sentral state håndtering)
  - Håndterer session state
  - Synkroniserer med database
  - Validerer state endringer
  - Logger state oppdateringer
  - Typevalidering og konvertering
  - Post-autentisering datahåndtering

## Konfigurasjonshåndtering
- src/config/state_config.py (state konfigurasjon)
- src/config/validation_rules.py (valideringsregler)

tree \
    -I "*.pyc|__pycache__|*.dist-info|*.egg-info|node_modules|build|dist|*.so|*.whl|*.zip|*.tar.gz" \
    --dirsfirst \
    -P "*.py|*.md|*.txt|*.ini|*.yaml|*.json" \
    -L 4
.
├── data
├── docs
│   ├── avhengigheter.md
│   └── system.md
├── eksport
├── logs
│   ├── auth
│   ├── bytteplan
│   ├── database
│   ├── errors
│   └── performance
├── src
│   ├── auth
│   │   ├── __init__.py
│   │   ├── auth_handler.py
│   │   └── auth_views.py
│   ├── config
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   └── settings.py
│   ���── database
│   │   ├── handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth_db_handler.py
│   │   │   ├── base_handler.py
│   │   │   ├── bytteplan_handler.py
│   │   │   ├── kamp_handler.py
│   │   │   └── spiller_handler.py
│   │   ├── migrations
│   │   │   └── migrations_handler.py
│   │   ├── queries
│   │   ├── __init__.py
│   │   ├── base_handler.py
│   │   ├── db_config.py
│   │   └── db_handler.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── bytteplan_model.py
│   │   ├── kamp_model.py
│   │   └── spiller_model.py
│   ├── pages
│   │   ├── components
│   │   │   ├── bytteplan_table.py
│   │   │   └── bytteplan_view.py
│   │   ├── __init__.py
│   │   ├── bytteplan_page.py
│   │   ├── kamp_page.py
│   │   ├── kamptropp_page.py
│   │   └── oppsett_page.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── bytteplan_utils.py
│   │   ├── export.py
│   │   ├── logger_utils.py
│   │   ├── periode_utils.py
│   │   ├── spilletid_analyse.py
│   │   ├── spilletid_utils.py
│   │   ├── state_handler.py
│   │   └── validation.py
│   ├── __init__.py
│   └── main.py
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_basic.py
│   ├── test_bytteplan.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_db_handler.py
│   └── test_pages.py
├── venv
│   ├── bin
│   ├── etc
│   │   └── jupyter
│   │       └── nbconfig
│   ├── include
│   ├── lib
│   │   └── python3.9
│   │       └── site-packages
│   └── share
│       ├── jupyter
│       │   ├── labextensions
│       │   └── nbextensions
│       └── man
│           └── man1
├── README.md
├── mypy.ini
├── pytest.ini
├── requirements-dev.txt
├── requirements.txt
└── streamlit_app.py

37 directories, 56 files
(venv) tor.inge.jossang@aftenbladet.no@A121779-NO min_kamp %
