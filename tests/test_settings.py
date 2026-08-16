"""
Unit tests for configuration settings and keywords structure.
"""

import json
from pathlib import Path
import pytest
from config import settings


def test_system_constants() -> None:
    """Test that system constants match architectural safety specifications."""
    assert settings.MAX_DAILY_DMS == 20
    assert settings.LINKS_PER_FILE == 100
    assert settings.TIME_SLEEP_MIN == 5
    assert settings.TIME_SLEEP_MAX == 12


def test_missing_env_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing environment variables raise explicit ValueError."""
    monkeypatch.delenv("API_ID", raising=False)
    monkeypatch.delenv("API_HASH", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    with pytest.raises(ValueError, match="API_ID"):
        settings.get_api_id()

    with pytest.raises(ValueError, match="API_HASH"):
        settings.get_api_hash()

    with pytest.raises(ValueError, match="BOT_TOKEN"):
        settings.get_bot_token()


def test_invalid_api_id_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that non-integer API_ID raises ValueError."""
    monkeypatch.setenv("API_ID", "not_a_number")
    with pytest.raises(ValueError, match="must be a valid integer"):
        settings.get_api_id()


def test_valid_env_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that valid environment variables are returned correctly."""
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "mock_hash_abc")
    monkeypatch.setenv("BOT_TOKEN", "123456:mock_token_xyz")

    assert settings.get_api_id() == 123456
    assert settings.get_api_hash() == "mock_hash_abc"
    assert settings.get_bot_token() == "123456:mock_token_xyz"

    # Test dynamic module attributes
    assert settings.API_ID == 123456
    assert settings.API_HASH == "mock_hash_abc"
    assert settings.BOT_TOKEN == "123456:mock_token_xyz"


def test_archive_channel_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ARCHIVE_CHANNEL_ID parsing as integer and handling when missing or invalid."""
    monkeypatch.setenv("ARCHIVE_CHANNEL_ID", "-1001234567890")
    assert settings.get_archive_channel_id() == -1001234567890
    assert getattr(settings, "ARCHIVE_CHANNEL_ID") == -1001234567890

    monkeypatch.delenv("ARCHIVE_CHANNEL_ID", raising=False)
    assert settings.get_archive_channel_id() is None

    monkeypatch.setenv("ARCHIVE_CHANNEL_ID", "invalid_id")
    assert settings.get_archive_channel_id() is None


def test_undefined_module_attribute() -> None:
    """Test that accessing undefined module attributes raises AttributeError."""
    with pytest.raises(AttributeError):
        _ = getattr(settings, "NON_EXISTENT_VAR")


def test_keywords_json_structure() -> None:
    """Test that data/keywords.json exists and conforms to intent classification schema."""
    keywords_path = Path(__file__).resolve().parent.parent / "data" / "keywords.json"
    assert keywords_path.exists(), "data/keywords.json must exist"

    with open(keywords_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "filters" in data
    assert data["filters"]["max_words_allowed"] == 40
    assert data["filters"]["max_emojis_allowed"] == 4

    assert "regex_patterns" in data
    assert "phone_numbers" in data["regex_patterns"]
    assert "whatsapp_links" in data["regex_patterns"]
    assert "telegram_usernames" in data["regex_patterns"]

    assert "negative_phrases" in data
    assert isinstance(data["negative_phrases"], list)
    assert "تحويل بعد الانجاز" in data["negative_phrases"]
    assert "مركز الخليج" in data["negative_phrases"]

    assert "positive_matrix" in data
    assert "intent_words" in data["positive_matrix"]
    assert "subject_words" in data["positive_matrix"]
    assert "واجب" in data["positive_matrix"]["subject_words"]
