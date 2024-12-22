"""
VIKTIG: Sjekk alltid @avhengigheter.md og @system.md før endringer!

Logger-oppsett og konfigurasjon.
Se spesielt:
- avhengigheter.md -> Logger
- system.md -> Logging
"""

import logging
import threading
import traceback
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

import streamlit as st

# Type aliases
T = TypeVar("T")
EventHandler = Callable[[Dict[str, Any]], None]
LogRecord = logging.LogRecord

# Opprett logger
root_logger = logging.getLogger("kampplanlegger")


class SessionStateHandler(logging.Handler):
    """Handler som legger til session state i log records"""

    def emit(self, record: LogRecord) -> None:
        if hasattr(st, "session_state"):
            setattr(record, "session_state", dict(st.session_state))
        else:
            setattr(record, "session_state", {})


class BaseStateLogger:
    """Felles baseklasse for state logging"""

    def _get_safe_state(self) -> Dict[str, str]:
        """Henter sikker representasjon av session state"""
        if hasattr(st, "session_state"):
            return {
                str(key): f"{str(value)} ({type(value).__name__})"
                for key, value in dict(st.session_state).items()
            }
        return {}


class BytteplanLogger(BaseStateLogger):
    def __init__(self, name: str = "kampplanlegger") -> None:
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        # Opprett logs-struktur
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        for subdir in ["bytteplan", "errors", "performance", "database", "auth"]:
            (log_dir / subdir).mkdir(exist_ok=True)

        # Hovedlogger konfigurasjon
        self.logger.setLevel(logging.DEBUG)
        if self.logger.handlers:
            self.logger.debug("Fjerner eksisterende handlers")
            self.logger.handlers.clear()

        # Deaktiver støy
        for logger_name in ["fsevents", "watchdog", "streamlit"]:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)

        # Spesialiserte handlers med detaljert logging
        handlers = {
            "bytteplan": self._create_handler("bytteplan/bytteplan.log", logging.DEBUG),
            "error": self._create_handler("errors/error.log", logging.ERROR),
            "perf": self._create_handler("performance/performance.log", logging.INFO),
            "db": self._create_handler("database/database.log", logging.DEBUG),
            "auth": self._create_handler("auth/auth.log", logging.INFO),
            "console": logging.StreamHandler(),
        }

        # Legg til session state tracking med mer detaljert logging
        session_handler = SessionStateHandler()
        session_handler.setLevel(logging.DEBUG)
        handlers["session"] = session_handler

        # Konfigurer alle handlers med mer detaljert logging
        for handler_name, handler in handlers.items():
            self.logger.debug("Konfigurerer handler: %s", handler_name)
            if isinstance(handler, (logging.Handler, SessionStateHandler)):
                handler.addFilter(self._create_detailed_filter())
                handler.setFormatter(self._create_detailed_formatter())
                self.logger.addHandler(handler)

    def _create_handler(self, filename: str, level: int) -> RotatingFileHandler:
        handler = RotatingFileHandler(
            filename=f"logs/{filename}",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=20,
            encoding="utf-8",
        )
        handler.setLevel(level)
        return handler

    def _create_detailed_filter(self) -> logging.Filter:
        class DetailedFilter(logging.Filter):
            def filter(self, record: LogRecord) -> bool:
                record.function_name = record.funcName
                record.line_no = record.lineno
                record.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # Legg til mer kontekst for debugging
                if hasattr(st, "session_state"):
                    setattr(
                        record,
                        "session_state",
                        {
                            key: str(value)
                            for key, value in dict(st.session_state).items()
                        },
                    )
                    # Spesifikk logging for perioder
                    if "perioder" in st.session_state:
                        setattr(record, "perioder", str(st.session_state.perioder))

                if record.levelno >= logging.ERROR:
                    record.stack_trace = "".join(traceback.format_stack())

                return True

        return DetailedFilter()

    def _create_detailed_formatter(self) -> logging.Formatter:
        class DetailedFormatter(logging.Formatter):
            def format(self, record: LogRecord) -> str:
                fmt = (
                    "%(timestamp)s [%(name)s] %(levelname)s "
                    "[%(function_name)s:%(line_no)s] "
                    "%(message)s"
                )

                # Legg til session state info hvis tilgjengelig
                if hasattr(record, "session_state"):
                    fmt += "\nSession State: %(session_state)s"
                if hasattr(record, "perioder"):
                    fmt += "\nPerioder: %(perioder)s"
                if hasattr(record, "stack_trace"):
                    fmt += "\n%(stack_trace)s"

                if hasattr(record, "session_state"):
                    # Legg til typeinformasjon i session state logging
                    state_with_types = {
                        str(k): f"{str(v)} ({type(v).__name__})"
                        for k, v in getattr(record, "session_state", {}).items()
                    }
                    setattr(record, "session_state", state_with_types)

                self._style._fmt = fmt
                return super().format(record)

        return DetailedFormatter()


def log_function_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """Dekoratør for å logge funksjonskalll"""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = datetime.now()

        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            root_logger.debug(
                "Funksjon: %s Args: %s Kwargs: %s Returverdi: %s Kjøretid: %.3fs",
                func.__name__,
                args,
                kwargs,
                result,
                execution_time,
            )
            return result

        except Exception as e:
            root_logger.error(
                "Feil i %s: %s Args: %s Kwargs: %s",
                func.__name__,
                str(e),
                args,
                kwargs,
                exc_info=True,
            )
            raise

    return wrapper


def setup_logging() -> logging.Logger:
    """Hovedfunksjon for å sette opp logging"""
    return BytteplanLogger().logger


class StateChangeFilter(logging.Filter):
    """Filter for å spore state-endringer"""

    def __init__(self) -> None:
        super().__init__()
        self.previous_state: Dict[str, Any] = {}

    def filter(self, record: LogRecord) -> bool:
        if hasattr(record, "session_state"):
            current_state = getattr(record, "session_state", {})
            # Finn endringer
            changes = {
                k: (self.previous_state.get(k), v)
                for k, v in current_state.items()
                if k not in self.previous_state or self.previous_state[k] != v
            }
            if changes:
                setattr(record, "state_changes", changes)
            self.previous_state = current_state
        return True


class PeriodeChangeFilter(logging.Filter):
    """Sporer endringer i periodekonfigurasjon"""

    def __init__(self) -> None:
        super().__init__()
        self._last_config: Optional[Dict[str, Any]] = None

    def filter(self, record: LogRecord) -> bool:
        if hasattr(record, "session_state"):
            session_state = getattr(record, "session_state", {})
            current_config = {
                "kamptid": session_state.get("kamptid"),
                "periode_lengde": session_state.get("periode_lengde"),
                "num_perioder": len(session_state.get("perioder", [])),
            }

            if self._last_config and self._last_config != current_config:
                setattr(
                    record,
                    "periode_endring",
                    {
                        "fra": self._last_config,
                        "til": current_config,
                    },
                )

            self._last_config = current_config
        return True


class CheckboxChangeFilter(logging.Filter):
    """Sporer endringer i checkbox-status"""

    def __init__(self) -> None:
        super().__init__()
        self._checkbox_states: Dict[str, Any] = {}

    def filter(self, record: LogRecord) -> bool:
        if hasattr(record, "session_state"):
            session_state = getattr(record, "session_state", {})
            # Finn alle checkbox-relaterte endringer
            changes = {
                k: v
                for k, v in session_state.items()
                if (
                    k.startswith("check_")
                    and k not in self._checkbox_states
                    or self._checkbox_states[k] != v
                )
            }

            if changes:
                setattr(record, "checkbox_changes", changes)
                self._checkbox_states.update(changes)

                if "kamptid" in session_state:
                    self._checkbox_states.clear()

        return True


def logg_session_state(hvor: str) -> None:
    viktige_verdier = {
        "authenticated": st.session_state.get("authenticated"),
        "user_id": st.session_state.get("user_id"),
        "antall_perioder": st.session_state.get("antall_perioder"),
        "kamptid": st.session_state.get("kamptid"),
        "periode_lengde": st.session_state.get("periode_lengde"),
    }
    root_logger.debug("Session state i %s: %s", hvor, viktige_verdier)


def logg_bytteplan_state() -> None:
    viktige_verdier = {
        "antall_perioder": st.session_state.get("antall_perioder"),
        "kamptid": st.session_state.get("kamptid"),
        "periode_lengde": st.session_state.get("periode_lengde"),
        "perioder": st.session_state.get("perioder"),
    }
    root_logger.debug("Bytteplan state: %s", viktige_verdier)


class CustomFilter(BaseStateLogger, logging.Filter):
    _local = threading.local()

    def filter(self, record: LogRecord) -> bool:
        # Unngå rekursiv logging
        if getattr(self._local, "in_filter", False):
            return True

        try:
            self._local.in_filter = True
            stack = traceback.extract_stack()
            # Fjern logging-relaterte frames
            relevant_stack = []
            for frame in stack:
                if "logging" not in frame.filename:
                    relevant_stack.append(frame)
            trace = "".join(traceback.format_list(relevant_stack))
            setattr(record, "stack_trace", trace)
            return True
        finally:
            self._local.in_filter = False


# Global event handlers dictionary
_event_handlers: Dict[str, list[EventHandler]] = {}
_handler_lock = threading.Lock()


def emit(event: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Sender ut et event til alle registrerte handlers.

    Args:
        event: Navnet på eventet
        data: Valgfri data som skal sendes med eventet
    """
    if data is None:
        data = {}

    try:
        with _handler_lock:
            handlers = _event_handlers.get(event, [])
            for handler in handlers:
                try:
                    handler(data)
                except (ValueError, TypeError, KeyError) as e:
                    root_logger.error("Feil i event handler for %s: %s", event, e)
    except (ValueError, TypeError) as e:
        root_logger.error("Feil ved emit av event %s: %s", event, e)


def on(event: str, handler: EventHandler) -> None:
    """
    Registrerer en handler for et event.

    Args:
        event: Navnet på eventet
        handler: Funksjonen som skal håndtere eventet
    """
    with _handler_lock:
        if event not in _event_handlers:
            _event_handlers[event] = []
        _event_handlers[event].append(handler)


def off(event: str, handler: EventHandler) -> None:
    """
    Fjerner en handler for et event.

    Args:
        event: Navnet på eventet
        handler: Funksjonen som skal fjernes
    """
    with _handler_lock:
        if event in _event_handlers:
            try:
                _event_handlers[event].remove(handler)
            except ValueError:
                pass
