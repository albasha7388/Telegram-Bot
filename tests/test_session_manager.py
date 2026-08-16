"""
Unit tests for the MTProto userbot Session Manager module.

Verifies session file discovery, active session global state tracking, safe session file deletion,
and safe session renaming with automatic active session state synchronization and SQLite journal handling.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture

from userbot import session_manager


@pytest.fixture(autouse=True)
def reset_global_active_session() -> None:
    """Reset the global active session variable before and after each test."""
    session_manager.set_active_session(None)
    yield
    session_manager.set_active_session(None)


# --- 1. Available Sessions Discovery Tests ---

def test_get_available_sessions_directory_not_found(mocker: MockerFixture) -> None:
    """Test get_available_sessions returns an empty list if sessions directory does not exist."""
    mocker.patch("os.path.exists", return_value=False)
    assert session_manager.get_available_sessions() == []


def test_get_available_sessions_listing(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test get_available_sessions returns sorted session names ignoring journals."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir",
        return_value=[
            "account_beta.session",
            "account_beta.session-journal",
            "account_alpha.session",
            "notes.txt",
        ],
    )

    sessions = session_manager.get_available_sessions()
    assert sessions == ["account_alpha", "account_beta"]


def test_get_available_sessions_os_error(mocker: MockerFixture) -> None:
    """Test get_available_sessions catches OSError and returns empty list."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", side_effect=OSError("Permission denied"))

    sessions = session_manager.get_available_sessions()
    assert sessions == []


# --- 2. Active Session Tracking Tests ---

def test_get_and_set_active_session() -> None:
    """Test getting and setting the global active session."""
    assert session_manager.get_active_session() is None

    session_manager.set_active_session("marketing_account")
    assert session_manager.get_active_session() == "marketing_account"

    session_manager.set_active_session(None)
    assert session_manager.get_active_session() is None


# --- 3. Session Deletion Tests ---

def test_delete_session_success_non_active(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test deleting an existing session file removes .session and journal."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    sess_file = tmp_path / "test_acc.session"
    journal_file = tmp_path / "test_acc.session-journal"
    sess_file.write_text("dummy session data")
    journal_file.write_text("dummy journal data")

    session_manager.set_active_session("other_account")

    success = session_manager.delete_session("test_acc")
    assert success is True
    assert not sess_file.exists()
    assert not journal_file.exists()
    assert session_manager.get_active_session() == "other_account"


def test_delete_session_success_resets_active(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test deleting the currently active session resets active session to None."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    sess_file = tmp_path / "active_acc.session"
    sess_file.write_text("dummy session data")

    session_manager.set_active_session("active_acc")

    success = session_manager.delete_session("active_acc.session")
    assert success is True
    assert not sess_file.exists()
    assert session_manager.get_active_session() is None


def test_delete_session_non_existent(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test deleting a non-existent session returns False."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    success = session_manager.delete_session("ghost_account")
    assert success is False


def test_delete_session_empty_name() -> None:
    """Test deleting an empty session name returns False."""
    assert session_manager.delete_session("   ") is False


def test_delete_session_os_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test delete_session catches OSError during removal and returns False."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)
    sess_file = tmp_path / "locked_acc.session"
    sess_file.write_text("locked")

    mocker.patch("os.remove", side_effect=OSError("File locked by process"))

    success = session_manager.delete_session("locked_acc")
    assert success is False


# --- 4. Session Renaming Tests ---

def test_rename_session_success_non_active(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test renaming an existing session file and its journal."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    old_file = tmp_path / "old_name.session"
    old_journal = tmp_path / "old_name.session-journal"
    old_file.write_text("session content")
    old_journal.write_text("journal content")

    session_manager.set_active_session("other_account")

    success = session_manager.rename_session("old_name", "new_name")
    assert success is True
    assert not old_file.exists()
    assert (tmp_path / "new_name.session").exists()
    assert (tmp_path / "new_name.session-journal").exists()
    assert session_manager.get_active_session() == "other_account"


def test_rename_session_success_updates_active(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test renaming the currently active session updates _active_session."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    old_file = tmp_path / "active_old.session"
    old_file.write_text("session content")

    session_manager.set_active_session("active_old")

    success = session_manager.rename_session("active_old.session", "active_new.session")
    assert success is True
    assert not old_file.exists()
    assert (tmp_path / "active_new.session").exists()
    assert session_manager.get_active_session() == "active_new"


def test_rename_session_non_existent(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test renaming a non-existent session file returns False."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    success = session_manager.rename_session("missing_old", "new_target")
    assert success is False


def test_rename_session_target_already_exists(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test renaming to an existing target file returns False without overwriting."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)

    (tmp_path / "session_1.session").write_text("data 1")
    (tmp_path / "session_2.session").write_text("data 2")

    success = session_manager.rename_session("session_1", "session_2")
    assert success is False
    assert (tmp_path / "session_1.session").exists()
    assert (tmp_path / "session_2.session").exists()


def test_rename_session_invalid_names() -> None:
    """Test renaming with empty or whitespace names returns False."""
    assert session_manager.rename_session("   ", "valid_target") is False
    assert session_manager.rename_session("valid_source", "") is False


def test_rename_session_os_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test rename_session catches OSError during rename and returns False."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)
    (tmp_path / "src_acc.session").write_text("src")

    mocker.patch("os.rename", side_effect=OSError("Access denied"))

    success = session_manager.rename_session("src_acc", "dst_acc")
    assert success is False


# --- 5. Environment StringSession Tests ---

def test_get_available_sessions_merges_env_and_local(tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_available_sessions discovers and merges environment sessions with local .session files."""
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)
    (tmp_path / "local_account.session").write_text("dummy")

    monkeypatch.setenv("SESSION_ACCOUNT_1", "string_session_val_1")
    monkeypatch.setenv("SESSION_ACCOUNT_2", "string_session_val_2")
    monkeypatch.setenv("OTHER_VAR", "ignored")

    sessions = session_manager.get_available_sessions()
    assert sessions == ["ACCOUNT_1", "ACCOUNT_2", "local_account"]


def test_get_session_string_and_is_env_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_session_string and is_env_session properly resolve environment variables."""
    monkeypatch.setenv("SESSION_PROD_USER", "prod_string_xyz")

    assert session_manager.get_session_string("PROD_USER") == "prod_string_xyz"
    assert session_manager.get_session_string("prod_user") == "prod_string_xyz"
    assert session_manager.get_session_string("SESSION_PROD_USER") == "prod_string_xyz"
    assert session_manager.is_env_session("PROD_USER") is True
    assert session_manager.is_env_session("non_existent") is False


def test_delete_and_rename_env_session_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that deleting or renaming an environment session is handled safely without file errors."""
    monkeypatch.setenv("SESSION_CLOUD_BOT", "cloud_string_123")

    session_manager.set_active_session("CLOUD_BOT")
    assert session_manager.get_active_session() == "CLOUD_BOT"

    # Delete env session: resets active session and returns True gracefully
    deleted = session_manager.delete_session("CLOUD_BOT")
    assert deleted is True
    assert session_manager.get_active_session() is None

    # Rename env session: returns False as env sessions cannot be renamed on disk
    renamed = session_manager.rename_session("CLOUD_BOT", "NEW_CLOUD_BOT")
    assert renamed is False


def test_get_available_sessions_mocker_patch_dict_env(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test that get_available_sessions correctly discovers sessions using mocker.patch.dict on os.environ."""
    import os
    mocker.patch.object(session_manager, "SESSIONS_DIR", tmp_path)
    (tmp_path / "local_sample.session").write_text("local_data")

    mocker.patch.dict(
        os.environ,
        {
            "SESSION_TEST_CLOUD": "1BJWap_cloud_session_string",
            "SESSION_ANOTHER_BOT": "2CKXbq_another_session_string",
            "OTHER_VAR": "123",
        },
        clear=True,
    )

    sessions = session_manager.get_available_sessions()
    assert "TEST_CLOUD" in sessions
    assert "ANOTHER_BOT" in sessions
    assert "local_sample" in sessions
    assert "OTHER_VAR" not in sessions
    assert sessions == ["ANOTHER_BOT", "TEST_CLOUD", "local_sample"]


