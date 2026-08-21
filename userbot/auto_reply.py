"""
Intelligent intent evaluation and spam classification module for userbot auto-replies.

Implements the strict 4-step classification pipeline to distinguish genuine student
academic inquiries from commercial spam and promotional advertisements.
"""

import json
from pathlib import Path
import re
from typing import Any, Final
from core.logger_setup import setup_logger

logger = setup_logger(__name__)

# Dynamic project root resolution and centralized keywords configuration path
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
KEYWORDS_FILE_PATH: Final[Path] = BASE_DIR / "data" / "keywords.json"

# In-memory cached rules dictionary to avoid repeated disk reads
_KEYWORDS_CACHE: dict[str, Any] | None = None

# Comprehensive Unicode Emoji character pattern
EMOJI_REGEX: Final[re.Pattern[str]] = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Enclosed Characters
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess & Symbols
    "\U0001FA70-\U0001FAFF"  # Extended Pictographs
    "\U00002600-\U000026FF"  # Miscellaneous Symbols
    "]",
    flags=re.UNICODE,
)


def load_keywords(force_reload: bool = False) -> dict[str, Any]:
    """Load and cache the intent classification rules from data/keywords.json.

    Args:
        force_reload: If True, bypasses memory cache and reloads from disk.

    Returns:
        dict[str, Any]: Dictionary containing filters, regex patterns, negative phrases, and positive matrix.
    """
    global _KEYWORDS_CACHE
    if _KEYWORDS_CACHE is None or force_reload:
        if not KEYWORDS_FILE_PATH.exists():
            logger.error(
                "Keywords file not found at dynamically resolved path: %s",
                KEYWORDS_FILE_PATH.absolute(),
            )
            return {}

        try:
            with open(KEYWORDS_FILE_PATH, "r", encoding="utf-8") as file_handle:
                _KEYWORDS_CACHE = json.load(file_handle)
            logger.debug("Successfully loaded intent keywords configuration into memory.")
        except OSError as exc:
            logger.error(
                "Failed to read keywords file at '%s': %s",
                KEYWORDS_FILE_PATH.absolute(),
                exc,
                exc_info=True,
            )
            return {}
        except json.JSONDecodeError as exc:
            logger.error(
                "Corrupted JSON in keywords file '%s': %s",
                KEYWORDS_FILE_PATH.absolute(),
                exc,
                exc_info=True,
            )
            return {}

    return _KEYWORDS_CACHE or {}


def clear_keywords_cache() -> None:
    """Clear the in-memory keywords cache (primarily for unit testing)."""
    global _KEYWORDS_CACHE
    _KEYWORDS_CACHE = None


def count_emojis(text: str) -> int:
    """Count the total number of emoji symbols present in the text string.

    Args:
        text: Input string to inspect.

    Returns:
        int: Number of individual emoji characters found.
    """
    return len(EMOJI_REGEX.findall(text))


def evaluate_message(text: str) -> bool:
    """Evaluate an incoming message against the 4-step intent classification pipeline.

    Sequential Steps:
        1. Metadata Check: Word count <= max_words AND emoji count <= max_emojis.
        2. Regex Contacts Check: Must not contain phone numbers, WhatsApp links, or @usernames.
        3. Negative Intent Check: Must not contain any commercial spam phrases.
        4. Positive Matrix Check: Must contain at least one intent word AND one subject word.

    Args:
        text: The raw incoming message string from a Telegram group or channel.

    Returns:
        bool: True if the message represents a genuine student help inquiry; False otherwise.
    """
    if not text or not isinstance(text, str):
        logger.debug("Evaluator received empty or non-string input.")
        return False

    cleaned_text = text.strip()
    if not cleaned_text:
        return False

    rules = load_keywords()
    if not rules:
        logger.warning("Keywords configuration is empty; rejecting message by default.")
        return False

    # --- STEP 1: Metadata Check ---
    filters = rules.get("filters", {})
    max_words = filters.get("max_words_allowed", 40)
    max_emojis = filters.get("max_emojis_allowed", 4)

    words = cleaned_text.split()
    word_count = len(words)
    emoji_count = count_emojis(cleaned_text)

    if word_count > max_words or emoji_count > max_emojis:
        logger.info(
            "Step 1 (Metadata) Rejected: words=%d (max %d), emojis=%d (max %d)",
            word_count,
            max_words,
            emoji_count,
            max_emojis,
        )
        return False

    # --- STEP 2: Regex Contacts Check ---
    regex_patterns = rules.get("regex_patterns", {})
    for pattern_name, pattern_str in regex_patterns.items():
        if pattern_str and re.search(pattern_str, cleaned_text, re.IGNORECASE):
            logger.info("Step 2 (Regex Contacts) Rejected: matched pattern '%s'", pattern_name)
            return False

    # --- STEP 3: Negative Intent Check ---
    negative_phrases = rules.get("negative_phrases", [])
    for phrase in negative_phrases:
        if phrase and phrase in cleaned_text:
            logger.info("Step 3 (Negative Intent) Rejected: matched spam phrase '%s'", phrase)
            return False

    # --- STEP 4: Positive Matrix Check ---
    positive_matrix = rules.get("positive_matrix", {})
    intent_words = positive_matrix.get("intent_words", [])
    subject_words = positive_matrix.get("subject_words", [])

    has_intent = any(intent_word in cleaned_text for intent_word in intent_words if intent_word)
    has_subject = any(subject_word in cleaned_text for subject_word in subject_words if subject_word)

    if has_intent and has_subject:
        logger.info("Step 4 (Positive Matrix) Approved: genuine student academic request detected.")
        return True

    logger.info(
        "Step 4 (Positive Matrix) Rejected: has_intent=%s, has_subject=%s",
        has_intent,
        has_subject,
    )
    return False
