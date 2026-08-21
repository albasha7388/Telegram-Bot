"""
Unit tests for userbot session management and 4-step intent evaluation pipeline.
"""

from typing import Any
import pytest
from pytest_mock import MockerFixture

from userbot.session_manager import get_available_sessions
from userbot.auto_reply import evaluate_message, clear_keywords_cache, load_keywords


# --- Test Fixtures ---

@pytest.fixture(autouse=True)
def reset_keywords_cache() -> None:
    """Ensure keywords cache is wiped clean before each test execution."""
    clear_keywords_cache()


@pytest.fixture
def mock_keywords_dataset() -> dict[str, Any]:
    """Standard intent classification matrix for testing the pipeline."""
    return {
        "filters": {
            "max_words_allowed": 40,
            "max_emojis_allowed": 4,
        },
        "regex_patterns": {
            "phone_numbers": r"(?:\+966|05)[0-9]{8}",
            "whatsapp_links": r"(?:wa\.me|chat\.whatsapp\.com)",
            "telegram_usernames": r"@[a-zA-Z0-9_]{5,}",
        },
        "negative_phrases": [
            "تحويل بعد الانجاز",
            "ارخص سعر في السوق",
            "مسجل في صحتي",
            "للتواصل خاص",
            "تواصل وتساب",
            "تواصل واتساب",
            "نقدم جميع الخدمات الطلابية",
        ],
        "positive_matrix": {
            "intent_words": ["ابي", "ابغى", "احتاج", "مين", "مساعدة", "ضروري", "يدبر", "يسوي", "يعمل"],
            "subject_words": ["واجب", "كويز", "ميد", "فاينل", "مشروع", "مشاريع", "بحث", "بحوث", "عرض"],
        },
    }


# --- 1. Session Manager Tests ---

def test_get_available_sessions_directory_not_found(mocker: MockerFixture) -> None:
    """Test that missing sessions directory gracefully returns an empty list."""
    mocker.patch("os.path.exists", return_value=False)
    sessions = get_available_sessions()
    assert sessions == []


def test_get_available_sessions_discovery(mocker: MockerFixture) -> None:
    """Test discovering and stripping .session extensions from filenames."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir",
        return_value=[
            "student_helper.session",
            "secondary_bot.session",
            "notes.txt",
            ".gitkeep",
            "student_helper.session-journal",
        ],
    )
    sessions = get_available_sessions()
    assert sessions == ["secondary_bot", "student_helper"]


# --- 2. Intent Evaluation Pipeline (4 Steps) Tests ---

def test_evaluate_message_valid_student(mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]) -> None:
    """Test that a genuine student academic request passes all 4 steps successfully."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "السلام عليكم ابي احد فاهم يسوي لي واجب البرمجة ضروري"
    assert evaluate_message(sample_text) is True


def test_evaluate_message_rejected_by_emojis_metadata(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 1 when emoji count exceeds max_emojis_allowed."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "ابي مساعدة في حل واجب 😍🔥🎉🚀👑"  # 5 emojis (> 4 limit)
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_word_count_metadata(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 1 when word count exceeds max_words_allowed."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    long_text = "ابي مساعدة واجب " + ("كلمة " * 45)  # > 40 words
    assert evaluate_message(long_text) is False


def test_evaluate_message_rejected_by_regex_phone(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 2 when contact phone number is present."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "ابي احد يحل لي واجب تواصل معي 0512345678"
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_regex_whatsapp(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 2 when WhatsApp link is present."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "احتاج مشروع تخرج سريع wa.me/966500000000"
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_regex_telegram_username(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 2 when Telegram @username mention is detected."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "ابي حل كويز راسلني على @expert_writer"
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_negative_intent(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 3 when commercial spam phrase is found."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "ابي اسوي واجب مع تحويل بعد الانجاز ومضمون"
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_missing_subject_in_positive_matrix(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 4 when intent word is present but subject word is absent."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "تكفون ابي مساعدة ضروري يا اخوان"  # Has 'ابي', 'مساعدة', but no academic subject
    assert evaluate_message(sample_text) is False


def test_evaluate_message_rejected_by_missing_intent_in_positive_matrix(
    mocker: MockerFixture, mock_keywords_dataset: dict[str, Any]
) -> None:
    """Test rejection at Step 4 when subject word is present but intent word is absent."""
    mocker.patch("userbot.auto_reply.load_keywords", return_value=mock_keywords_dataset)
    sample_text = "كويز الرياضيات النهائي والواجب اليوم"  # Has 'كويز', 'واجب', but no inquiry intent
    assert evaluate_message(sample_text) is False


def test_load_keywords_missing_file_logs_error_and_returns_empty(mocker: MockerFixture) -> None:
    """Test load_keywords logs error with absolute path and returns empty dict when file does not exist."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    mock_logger_error = mocker.patch("userbot.auto_reply.logger.error")

    result = load_keywords(force_reload=True)

    assert result == {}
    mock_logger_error.assert_called_once()
    assert "Keywords file not found at dynamically resolved path:" in mock_logger_error.call_args[0][0]


def test_load_keywords_corrupted_json_returns_empty(mocker: MockerFixture) -> None:
    """Test load_keywords returns empty dict without crashing when JSON is corrupted."""
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="{invalid_json}"))
    mock_logger_error = mocker.patch("userbot.auto_reply.logger.error")

    result = load_keywords(force_reload=True)

    assert result == {}
    mock_logger_error.assert_called_once()
    assert "Corrupted JSON in keywords file" in mock_logger_error.call_args[0][0]
