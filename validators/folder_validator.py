"""
Telegram folder link extraction and validation module.

Strictly identifies and extracts shareable folder invite links (t.me/addlist/...).
"""

import re
from typing import Final
from core.logger_setup import setup_logger

logger = setup_logger(__name__)

# Matches shareable folder links from t.me/addlist/... or tg://addlist?slug=...
FOLDER_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/addlist/([a-zA-Z0-9_\-]+))"
    r"|(?:tg://addlist\?slug=([a-zA-Z0-9_\-]+))",
    re.IGNORECASE,
)


def extract_folder_links(text: str) -> list[str]:
    """Extract strictly shareable Telegram folder links (t.me/addlist/...) from raw text.

    Normalizes detected folder links to standard https://t.me/addlist/<slug> URLs,
    strips trailing punctuation, and preserves discovery order while deduplicating.

    Args:
        text: The raw input string containing potential folder links.

    Returns:
        list[str]: Deduplicated list of normalized folder invite URLs.
    """
    if not text or not isinstance(text, str):
        logger.debug("Received empty or invalid text input for folder link extraction.")
        return []

    found_links: list[str] = []
    seen: set[str] = set()

    for match in FOLDER_LINK_PATTERN.finditer(text):
        slug = match.group(1) or match.group(2)
        if not slug:
            continue

        slug = slug.rstrip(".,!?:;)]}\"'")
        if not slug:
            continue

        normalized_url = f"https://t.me/addlist/{slug}"
        if normalized_url not in seen:
            seen.add(normalized_url)
            found_links.append(normalized_url)

    logger.debug("Extracted %d folder link(s) from text input.", len(found_links))
    return found_links
