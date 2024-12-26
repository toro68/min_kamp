"""Logging configuration."""

import logging
import os


def configure_logging() -> None:
    """Configure logging for the application."""
    # Get log level from environment variable
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set log level for specific loggers
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
