"""Logging configuration for annextube.

Provides structured logging with both JSON (for machine parsing) and
human-readable output formats.
"""

import logging
import sys
from pathlib import Path

# Log levels mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace ID if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Formatter that outputs human-readable logs."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    level: str = "info",
    json_format: bool = False,
    log_file: Path | None = None,
    quiet: bool = False,
) -> logging.Logger:
    """Configure logging for annextube.

    Args:
        level: Log level (debug, info, warning, error, critical)
        json_format: Use JSON structured logging format
        log_file: Optional path to log file
        quiet: Suppress console output (only log to file)

    Returns:
        Configured logger instance
    """
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)

    # Get root logger for annextube
    logger = logging.getLogger("annextube")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers = []

    # Choose formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    # Console handler (unless quiet)
    if not quiet:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"annextube.{name}")
