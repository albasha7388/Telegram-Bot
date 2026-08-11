"""
Centralized logging configuration module for the Hybrid Telegram System.

Configures logger instances with standardized formatting, console streaming,
and Windows-safe daily date-stamped file logging for operations
('logs/operations/operations_{current_date}.log') and isolated error-level logging
in 'logs/errors/errors_{current_date}.log'.
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Final, Optional

# Format specification: timestamp, module name, severity level, message
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Resolve directories ensuring strict separation between data/ and logs/
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
LOGS_DIR: Final[Path] = BASE_DIR / "logs"
OPERATIONS_DIR: Final[Path] = LOGS_DIR / "operations"
ERRORS_DIR: Final[Path] = LOGS_DIR / "errors"


def get_current_date_str() -> str:
    """Return the current local date formatted as YYYY-MM-DD.

    Returns:
        str: The formatted date string (e.g., '2026-08-10').
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_operations_log_path(date_str: Optional[str] = None) -> Path:
    """Return the absolute path for the operations log file with the given or current date.

    Args:
        date_str: Optional date string formatted as YYYY-MM-DD. Defaults to current date.

    Returns:
        Path: The operations log file path.
    """
    target_date: str = date_str if date_str is not None else get_current_date_str()
    return OPERATIONS_DIR / f"operations_{target_date}.log"


def get_errors_log_path(date_str: Optional[str] = None) -> Path:
    """Return the absolute path for the errors log file with the given or current date.

    Args:
        date_str: Optional date string formatted as YYYY-MM-DD. Defaults to current date.

    Returns:
        Path: The errors log file path.
    """
    target_date: str = date_str if date_str is not None else get_current_date_str()
    return ERRORS_DIR / f"errors_{target_date}.log"


# Module-level default log paths for backward compatibility
OPERATIONS_LOG_PATH: Final[Path] = get_operations_log_path()
ERRORS_LOG_PATH: Final[Path] = get_errors_log_path()
LOG_FILE_PATH: Final[Path] = OPERATIONS_LOG_PATH


def _ensure_log_directories() -> None:
    """Dynamically create required log sub-directories if they do not exist."""
    OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(module_name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a modular logger instance with console, operations, and error handlers.

    Ensures strict architectural separation and Windows-safe daily logging without file locking conflicts:
    1. Standard Console Output (StreamHandler).
    2. Standard FileHandler for general operations logs saved to 'logs/operations/operations_{current_date}.log'.
    3. Dedicated FileHandler for ERROR and CRITICAL levels saved to 'logs/errors/errors_{current_date}.log'.

    Args:
        module_name: The name identifier for the logger (usually __name__).
        level: The minimum logging severity level (defaults to logging.INFO).

    Returns:
        logging.Logger: Fully configured logger instance.
    """
    _ensure_log_directories()

    logger: logging.Logger = logging.getLogger(module_name)
    logger.setLevel(level)

    # Prevent duplicate handlers if the logger has already been initialized (critical fix for Windows file lock)
    if not logger.handlers:
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        # 1. Console Stream Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. Standard Operations File Handler (Windows-safe daily date injected)
        ops_path = get_operations_log_path()
        operations_handler = logging.FileHandler(
            filename=str(ops_path),
            mode="a",
            encoding="utf-8",
        )
        operations_handler.setLevel(level)
        operations_handler.setFormatter(formatter)
        logger.addHandler(operations_handler)

        # 3. Dedicated Error File Handler (Strictly ERROR and CRITICAL, Windows-safe daily date injected)
        err_path = get_errors_log_path()
        error_handler = logging.FileHandler(
            filename=str(err_path),
            mode="a",
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    return logger


# Alias for backward compatibility or alternate invocation styles
logger_setup = setup_logger
