"""
Unit tests for the centralized logging setup module and Windows-safe daily date-stamped file logging.
"""

from datetime import datetime
import logging
from pathlib import Path
from core import logger_setup
from core.logger_setup import (
    ERRORS_DIR,
    OPERATIONS_DIR,
    get_current_date_str,
    get_errors_log_path,
    get_operations_log_path,
    setup_logger,
)


def test_setup_logger_directory_creation(tmp_path: Path, monkeypatch) -> None:
    """Test that setup_logger dynamically creates logs/operations/ and logs/errors/ sub-directories."""
    test_logs_dir = tmp_path / "logs"
    test_ops_dir = test_logs_dir / "operations"
    test_err_dir = test_logs_dir / "errors"

    monkeypatch.setattr(logger_setup, "LOGS_DIR", test_logs_dir)
    monkeypatch.setattr(logger_setup, "OPERATIONS_DIR", test_ops_dir)
    monkeypatch.setattr(logger_setup, "ERRORS_DIR", test_err_dir)

    assert not test_ops_dir.exists()
    assert not test_err_dir.exists()

    logger = setup_logger("test_dir_creation")
    assert test_ops_dir.exists()
    assert test_err_dir.exists()
    assert logger is not None


def test_get_log_paths_date_injection(tmp_path: Path, monkeypatch) -> None:
    """Test get_operations_log_path and get_errors_log_path generate correct date-based filenames."""
    test_logs_dir = tmp_path / "logs"
    test_ops_dir = test_logs_dir / "operations"
    test_err_dir = test_logs_dir / "errors"

    monkeypatch.setattr(logger_setup, "OPERATIONS_DIR", test_ops_dir)
    monkeypatch.setattr(logger_setup, "ERRORS_DIR", test_err_dir)

    current_date = get_current_date_str()
    ops_path = get_operations_log_path()
    err_path = get_errors_log_path()

    assert ops_path == test_ops_dir / f"operations_{current_date}.log"
    assert err_path == test_err_dir / f"errors_{current_date}.log"

    custom_date = "2026-12-31"
    assert get_operations_log_path(custom_date) == test_ops_dir / f"operations_{custom_date}.log"
    assert get_errors_log_path(custom_date) == test_err_dir / f"errors_{custom_date}.log"


def test_setup_logger_handler_targets(tmp_path: Path, monkeypatch) -> None:
    """Test logger initialization configures standard FileHandlers pointing to date-injected paths."""
    test_logs_dir = tmp_path / "logs"
    test_ops_dir = test_logs_dir / "operations"
    test_err_dir = test_logs_dir / "errors"

    monkeypatch.setattr(logger_setup, "LOGS_DIR", test_logs_dir)
    monkeypatch.setattr(logger_setup, "OPERATIONS_DIR", test_ops_dir)
    monkeypatch.setattr(logger_setup, "ERRORS_DIR", test_err_dir)

    current_date = datetime.now().strftime("%Y-%m-%d")
    expected_ops_log = test_ops_dir / f"operations_{current_date}.log"
    expected_err_log = test_err_dir / f"errors_{current_date}.log"

    logger_name = "test_handler_targets"
    logger = setup_logger(logger_name, level=logging.DEBUG)

    assert logger.name == logger_name
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 3

    # Check for stream handler and standard FileHandlers (no rotating handlers)
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]

    assert len(stream_handlers) == 1
    assert len(file_handlers) == 2

    # Assert that TimedRotatingFileHandler or any Rotating handler is NOT used
    for handler in logger.handlers:
        assert "Rotating" not in handler.__class__.__name__

    # Verify target file destinations
    handler_files = [Path(h.baseFilename).resolve() for h in file_handlers]
    assert expected_ops_log.resolve() in handler_files
    assert expected_err_log.resolve() in handler_files


def test_setup_logger_no_duplicate_handlers() -> None:
    """Test that repeatedly setting up the same logger does not duplicate handlers (singleton-like behavior)."""
    logger_name = "test_duplicate_check"
    logger1 = setup_logger(logger_name)
    initial_handler_count = len(logger1.handlers)

    logger2 = setup_logger(logger_name)
    assert len(logger2.handlers) == initial_handler_count
    assert logger1 is logger2


def test_logger_file_output_separation(tmp_path: Path, monkeypatch) -> None:
    """Test that info logs write to operations_{date}.log while error logs write to both operations and errors log."""
    test_logs_dir = tmp_path / "logs"
    test_ops_dir = test_logs_dir / "operations"
    test_err_dir = test_logs_dir / "errors"

    monkeypatch.setattr(logger_setup, "LOGS_DIR", test_logs_dir)
    monkeypatch.setattr(logger_setup, "OPERATIONS_DIR", test_ops_dir)
    monkeypatch.setattr(logger_setup, "ERRORS_DIR", test_err_dir)

    current_date = datetime.now().strftime("%Y-%m-%d")
    test_ops_log = test_ops_dir / f"operations_{current_date}.log"
    test_err_log = test_err_dir / f"errors_{current_date}.log"

    logger = setup_logger("test_separation_writer")
    info_msg = "TEST_INFO_LOG_MESSAGE"
    error_msg = "TEST_ERROR_CRITICAL_FAILURE"

    logger.info(info_msg)
    logger.error(error_msg)

    # Flush all handlers to disk
    for handler in logger.handlers:
        handler.flush()

    # Operations log contains both INFO and ERROR records
    assert test_ops_log.exists()
    with open(test_ops_log, "r", encoding="utf-8") as f:
        ops_content = f.read()
    assert info_msg in ops_content
    assert error_msg in ops_content

    # Error log contains strictly ERROR and CRITICAL records
    assert test_err_log.exists()
    with open(test_err_log, "r", encoding="utf-8") as f:
        err_content = f.read()
    assert error_msg in err_content
    assert info_msg not in err_content
