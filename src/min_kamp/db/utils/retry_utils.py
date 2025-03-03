"""Retry utilities for database operations."""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Dekoratør som prøver operasjonen på nytt ved feil.

    Args:
        max_retries: Maksimalt antall forsøk
        initial_delay: Initial ventetid mellom forsøk i sekunder
        max_delay: Maksimal ventetid mellom forsøk i sekunder
        backoff_factor: Faktor for eksponentiell økning av ventetid
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if "database is locked" in str(e):
                        logger.warning(
                            "Database låst, forsøk %d/%d. Venter %.1f sek",
                            attempt + 1,
                            max_retries,
                            delay,
                        )
                    else:
                        logger.warning(
                            "Operasjon feilet, forsøk %d/%d: %s",
                            attempt + 1,
                            max_retries,
                            str(e),
                        )

                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)

            if last_exception:
                raise last_exception

            return None  # Should never reach here

        return wrapper

    return decorator
