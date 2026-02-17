"""Central logging configuration.

The project uses the standard-library `logging` module only (no extra dependencies).

Goals:
  - INFO: high-level steps and outcomes (route selection, waypoint iterations, API calls)
  - DEBUG: per-candidate / per-route details for troubleshooting
  - Avoid leaking secrets (API keys) and minimize PII by default.

Usage:
  from logging_config import configure_logging
  configure_logging()  # call once near program start

Environment variables:
  LOG_LEVEL: DEBUG|INFO|WARNING|ERROR (default INFO)
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Root level controls which records are created at all.
# We keep it at DEBUG so handlers can filter differently.
DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LOG_FILE = "logs/bikers_map.log"
DEFAULT_LOG_MAX_BYTES = 2_000_000
DEFAULT_LOG_BACKUP_COUNT = 3


def configure_logging(level: str | None = None) -> None:
    """Configure root logging.

    Safe to call multiple times; subsequent calls are no-ops once handlers exist.
    """

    root = logging.getLogger()
    if root.handlers:
        return

    # Console level defaults to INFO (so Streamlit/CLI output isn't too noisy)
    console_level_name = (level or os.getenv("LOG_LEVEL") or "INFO").upper().strip()
    console_level_value = getattr(logging, console_level_name, logging.INFO)

    # File level defaults to DEBUG so we capture detailed traces to disk
    file_level_name = (os.getenv("LOG_FILE_LEVEL") or "DEBUG").upper().strip()
    file_level_value = getattr(logging, file_level_name, logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level_value)

    # File handler (rotating)
    log_file = os.getenv("LOG_FILE") or DEFAULT_LOG_FILE
    # Start fresh log file on each run by default.
    # Set LOG_APPEND=1 to keep appending across runs.
    append = (os.getenv("LOG_APPEND") or "0").strip().lower() in ("1", "true", "yes", "y")
    max_bytes = int(os.getenv("LOG_MAX_BYTES") or DEFAULT_LOG_MAX_BYTES)
    backup_count = int(os.getenv("LOG_BACKUP_COUNT") or DEFAULT_LOG_BACKUP_COUNT)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        mode=("a" if append else "w"),
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level_value)

    root.setLevel(logging.DEBUG)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Reduce noise from common dependencies (Streamlit uses watchdog).
    # Comma-separated list is configurable via LOG_QUIET_LOGGERS.
    quiet = os.getenv("LOG_QUIET_LOGGERS") or "watchdog,streamlit,urllib3"
    for name in [n.strip() for n in quiet.split(",") if n.strip()]:
        logging.getLogger(name).setLevel(logging.WARNING)


def safe_text(value: object, *, max_len: int = 48) -> str:
    """Return a log-safe, bounded-length representation.

    This intentionally avoids logging full addresses / user input by default.
    """

    s = "" if value is None else str(value)
    s = " ".join(s.split())  # collapse whitespace
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
