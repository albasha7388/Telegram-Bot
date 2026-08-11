"""
Telegram link extraction and validation module.

Extracts standard Telegram channel, group, and invite links while strictly
filtering out shareable folder links.
"""

import re
from typing import Final
from core.logger_setup import setup_logger

logger = setup_logger(__name__)

# Matches standard Telegram links (t.me/... or telegram.me/...) excluding /addlist
# Captures standard usernames, joinchat invites, and plus-prefixed (+hash) private invites.
TELEGRAM_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?!addlist(?:/|\b|\?))([a-zA-Z0-9_+/]+)",
    re.IGNORECASE,
)


def extract_telegram_links(text: str) -> list[str]:
    """Extract standard Telegram invite and channel links from raw text.

    Excludes folder share links (t.me/addlist/...). Links are normalized to full
    https://t.me/<identifier> URLs without trailing punctuation and deduplicated.

    Args:
        text: The raw input string containing potential Telegram links.

    Returns:
        list[str]: Deduplicated list of valid standard Telegram URLs in order of appearance.
    """
    if not text or not isinstance(text, str):
        logger.debug("Received empty or invalid text input for Telegram link extraction.")
        return []

    found_links: list[str] = []
    seen: set[str] = set()

    for match in TELEGRAM_LINK_PATTERN.finditer(text):
        identifier = match.group(1).rstrip(".,!?:;)]}\"'")
        if not identifier:
            continue

        normalized_url = f"https://t.me/{identifier}"
        if normalized_url not in seen:
            seen.add(normalized_url)
            found_links.append(normalized_url)

    logger.debug("Extracted %d Telegram link(s) from text input.", len(found_links))
    return found_links
