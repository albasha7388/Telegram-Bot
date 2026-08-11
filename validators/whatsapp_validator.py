"""
WhatsApp group invite extraction and live validation module.

Extracts chat.whatsapp.com links from text and verifies their validity
by parsing the remote invite page HTML, checking for join action metadata,
and strictly rejecting reset, revoked, or invalid invite links.
"""

import re
from typing import Final
from bs4 import BeautifulSoup
import requests

from core.logger_setup import setup_logger

logger = setup_logger(__name__)

# Matches WhatsApp group invite links
WHATSAPP_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:https?://)?(?:www\.)?chat\.whatsapp\.com/([a-zA-Z0-9_-]{10,30})",
    re.IGNORECASE,
)

# Standard browser User-Agent to retrieve the standard group preview HTML
HTTP_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# Explicit phrases indicating revoked, reset, or defunct invite links
RESET_OR_REVOKED_PHRASES: Final[tuple[str, ...]] = (
    "invite link was reset",
    "invite link has been reset",
    "link was reset",
    "this invite link was revoked",
    "invite link was revoked",
    "revoked",
    "link is invalid",
    "invalid link",
    "you can't join this group",
    "this group no longer exists",
)


def extract_whatsapp_links(text: str) -> list[str]:
    """Extract WhatsApp group invite links from raw text.

    Normalizes detected invites to full https://chat.whatsapp.com/<invite_code> URLs,
    strips trailing punctuation, and preserves discovery order while deduplicating.

    Args:
        text: The raw input string containing potential WhatsApp links.

    Returns:
        list[str]: Deduplicated list of normalized WhatsApp group invite URLs.
    """
    if not text or not isinstance(text, str):
        logger.debug("Received empty or invalid text input for WhatsApp link extraction.")
        return []

    found_links: list[str] = []
    seen: set[str] = set()

    for match in WHATSAPP_LINK_PATTERN.finditer(text):
        invite_code = match.group(1).rstrip(".,!?:;)]}\"'")
        if not invite_code:
            continue

        normalized_url = f"https://chat.whatsapp.com/{invite_code}"
        if normalized_url not in seen:
            seen.add(normalized_url)
            found_links.append(normalized_url)

    logger.debug("Extracted %d WhatsApp link(s) from text input.", len(found_links))
    return found_links


def validate_whatsapp_link(link: str, timeout: float = 5.0) -> bool:
    """Verify if a WhatsApp group invite link is active and valid via HTTP inspection.

    Fetches the invite landing page with an explicit timeout, parses the HTML,
    checks for group metadata and 'Join Chat' action properties, and rejects
    any links returning reset/revoked/invalid notices despite HTTP 200 status.

    Args:
        link: The WhatsApp group invite URL to validate.
        timeout: Maximum seconds to wait for network response (defaults to 5.0s).

    Returns:
        bool: True if the group link is active and valid, False otherwise.
    """
    if not link or not isinstance(link, str) or "chat.whatsapp.com" not in link:
        logger.warning("Invalid link format provided for WhatsApp validation: '%s'", link)
        return False

    try:
        logger.info("Validating WhatsApp invite link: %s", link)
        response = requests.get(link, headers=HTTP_HEADERS, timeout=timeout)

        if response.status_code != 200:
            logger.warning(
                "WhatsApp validation returned non-200 status (%d) for '%s'",
                response.status_code,
                link,
            )
            return False

        raw_html = response.text
        raw_html_lower = raw_html.lower()

        # 1. Strict Negative Check: Detect reset, revoked, or invalid notices in HTML
        for phrase in RESET_OR_REVOKED_PHRASES:
            if phrase in raw_html_lower:
                logger.warning(
                    "WhatsApp invite '%s' rejected: HTML contains reset/revoked indicator ('%s').",
                    link,
                    phrase,
                )
                return False

        soup = BeautifulSoup(raw_html, "html.parser")

        # 2. Check for the canonical 'Join Chat' action button or container
        action_btn = soup.find(id="action-button") or soup.find("a", class_="_9vcv")
        if action_btn:
            btn_text = action_btn.get_text(strip=True).lower()
            if "join chat" in btn_text or "join" in btn_text or action_btn.get("id") == "action-button":
                logger.info("WhatsApp invite '%s' validated successfully via action button.", link)
                return True

        # 3. Check for OpenGraph group title & description metadata
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title_content = str(og_title.get("content")).strip()
            # Verify title exists and is not a generic error or empty fallback
            if title_content and "WhatsApp Group Invite" not in title_content:
                logger.info(
                    "WhatsApp invite '%s' validated successfully via metadata title: %s",
                    link,
                    title_content,
                )
                return True

        # 4. Check for specific group name container elements
        group_title_div = soup.find("h3", class_="_9vd5") or soup.find("div", class_="_9vx6")
        if group_title_div and group_title_div.get_text(strip=True):
            logger.info("WhatsApp invite '%s' validated successfully via group container.", link)
            return True

        # 5. Check for join_chat metadata properties in scripts or attributes
        if "join_chat" in raw_html_lower or "join chat" in raw_html_lower:
            logger.info("WhatsApp invite '%s' validated successfully via join_chat keyword.", link)
            return True

        logger.warning("WhatsApp invite '%s' does not contain valid group elements.", link)
        return False

    except requests.Timeout:
        logger.warning("Timeout occurred while validating WhatsApp invite '%s' (limit: %ss).", link, timeout)
        return False
    except requests.RequestException as exc:
        logger.warning("Network error during WhatsApp link validation for '%s': %s", link, exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error validating WhatsApp link '%s': %s", link, exc, exc_info=True)
        return False
