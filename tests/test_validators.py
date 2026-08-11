"""
Unit tests for link extraction and live HTML validation modules.
"""

from typing import Any
import pytest
from pytest_mock import MockerFixture
import requests

from validators.telegram_validator import extract_telegram_links
from validators.folder_validator import extract_folder_links
from validators.whatsapp_validator import extract_whatsapp_links, validate_whatsapp_link


# --- 1. Telegram Link Extraction Tests ---

def test_extract_telegram_links_standard() -> None:
    """Test extracting standard Telegram channels, usernames, and private invite links."""
    sample_text = (
        "Join our main channel: https://t.me/python_devs and discussion t.me/joinchat/AbCdEf123. "
        "Also private invite: https://t.me/+PrivateInviteHash! Contact us."
    )
    links = extract_telegram_links(sample_text)
    assert len(links) == 3
    assert "https://t.me/python_devs" in links
    assert "https://t.me/joinchat/AbCdEf123" in links
    assert "https://t.me/+PrivateInviteHash" in links


def test_extract_telegram_links_ignores_folder_addlists() -> None:
    """Test that standard extractor strictly ignores shareable folder addlist links."""
    sample_text = (
        "Check this folder: https://t.me/addlist/ExamFolder123 and this group https://t.me/ValidGroup."
    )
    links = extract_telegram_links(sample_text)
    assert len(links) == 1
    assert links == ["https://t.me/ValidGroup"]


def test_extract_telegram_links_empty_and_deduplication() -> None:
    """Test empty string and deduplication handling."""
    assert extract_telegram_links("") == []
    text = "Link once: https://t.me/my_channel, link twice: t.me/my_channel."
    links = extract_telegram_links(text)
    assert len(links) == 1
    assert links[0] == "https://t.me/my_channel"


# --- 2. Telegram Folder Link Extraction Tests ---

def test_extract_folder_links_standard() -> None:
    """Test extracting shareable folder links using various formats."""
    sample_text = (
        "Here is the study folder: https://t.me/addlist/StudyPack2026, "
        "and another t.me/addlist/MathResources. Also deep link tg://addlist?slug=ScienceClub!"
    )
    links = extract_folder_links(sample_text)
    assert len(links) == 3
    assert "https://t.me/addlist/StudyPack2026" in links
    assert "https://t.me/addlist/MathResources" in links
    assert "https://t.me/addlist/ScienceClub" in links


def test_extract_folder_links_ignores_standard_invites() -> None:
    """Test that folder extractor strictly ignores non-addlist Telegram links."""
    sample_text = "Standard link: https://t.me/joinchat/xyz and https://t.me/channel"
    assert extract_folder_links(sample_text) == []


# --- 3. WhatsApp Link Extraction Tests ---

def test_extract_whatsapp_links_standard() -> None:
    """Test extracting WhatsApp group invite links from text."""
    sample_text = (
        "Join WhatsApp group: https://chat.whatsapp.com/ABCdefGHIjk1234567890. "
        "Or without protocol: chat.whatsapp.com/XYZ9876543210zyxwvu."
    )
    links = extract_whatsapp_links(sample_text)
    assert len(links) == 2
    assert "https://chat.whatsapp.com/ABCdefGHIjk1234567890" in links
    assert "https://chat.whatsapp.com/XYZ9876543210zyxwvu" in links


def test_extract_whatsapp_links_empty_and_punctuation() -> None:
    """Test empty input and trailing punctuation sanitization."""
    assert extract_whatsapp_links("") == []
    sample_text = "Group invite (https://chat.whatsapp.com/InviteCode12345)!"
    links = extract_whatsapp_links(sample_text)
    assert links == ["https://chat.whatsapp.com/InviteCode12345"]


# --- 4. WhatsApp HTML Validation Tests (Mocked) ---

def test_validate_whatsapp_link_valid_with_action_button(mocker: MockerFixture) -> None:
    """Test successful WhatsApp validation when Join Chat action button is present in HTML."""
    mock_html = """
    <html>
      <head><title>WhatsApp Group</title></head>
      <body>
        <div class="group-info"><h3>Computer Science 101</h3></div>
        <a id="action-button" href="#">Join Chat</a>
      </body>
    </html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mocker.patch("requests.get", return_value=mock_response)

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/ValidInvite123")
    assert is_valid is True


def test_validate_whatsapp_link_valid_with_og_title(mocker: MockerFixture) -> None:
    """Test successful WhatsApp validation when OpenGraph metadata contains a valid title."""
    mock_html = """
    <html>
      <head>
        <meta property="og:title" content="Data Structures & Algorithms Batch" />
      </head>
      <body></body>
    </html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mocker.patch("requests.get", return_value=mock_response)

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/ValidInvite456")
    assert is_valid is True


def test_validate_whatsapp_link_reset(mocker: MockerFixture) -> None:
    """Test that an HTTP 200 response with 'invite link was reset' is strictly rejected."""
    mock_html = """
    <html>
      <head><title>WhatsApp Group</title></head>
      <body>
        <div class="_9vcd">You can't join this group because this invite link was reset.</div>
        <a id="action-button" href="#">Join Chat</a>
      </body>
    </html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mocker.patch("requests.get", return_value=mock_response)

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/ResetInvite789")
    assert is_valid is False


def test_validate_whatsapp_link_revoked(mocker: MockerFixture) -> None:
    """Test that an HTTP 200 response containing 'revoked' notice is strictly rejected."""
    mock_html = """
    <html>
      <head><title>WhatsApp Group</title></head>
      <body>
        <div class="main_msg">This invite link was revoked.</div>
      </body>
    </html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mocker.patch("requests.get", return_value=mock_response)

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/RevokedInvite999")
    assert is_valid is False


def test_validate_whatsapp_link_invalid_page(mocker: MockerFixture) -> None:
    """Test failed WhatsApp validation on 404 or broken group HTML."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 404
    mock_response.text = "<html><body>404 Not Found</body></html>"
    mocker.patch("requests.get", return_value=mock_response)

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/InvalidInvite")
    assert is_valid is False


def test_validate_whatsapp_link_network_timeout(mocker: MockerFixture) -> None:
    """Test graceful handling of network timeout without uncaught exceptions."""
    mocker.patch("requests.get", side_effect=requests.Timeout("Connection timed out"))

    is_valid = validate_whatsapp_link("https://chat.whatsapp.com/TimeoutInvite")
    assert is_valid is False


def test_validate_whatsapp_link_invalid_url_format(mocker: MockerFixture) -> None:
    """Test immediate rejection for non-WhatsApp URLs without invoking network requests."""
    spy_get = mocker.patch("requests.get")
    is_valid = validate_whatsapp_link("https://example.com/not-whatsapp")

    assert is_valid is False
    spy_get.assert_not_called()
