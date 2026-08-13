"""
Unit tests for global group chat link extraction, exact date bounds, granular target filtering, and live progress updates.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture
from pyrogram.enums import ChatType
from pyrogram.errors import ChatAdminRequired, UsernameInvalid

from userbot import extractor


class AsyncCustomIterator:
    """Helper asynchronous iterator simulating Pyrogram generator streams."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> "AsyncCustomIterator":
        return self

    async def __anext__(self) -> Any:
        if self._index < len(self._items):
            item = self._items[self._index]
            self._index += 1
            return item
        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_run_global_extraction_task_filters_groups_and_dates(mocker: MockerFixture) -> None:
    """Test global extraction iterates dialogs, skips private chats, and enforces date bounds."""
    mock_save = mocker.patch("userbot.extractor.save_link", return_value="/path/part_1.txt")
    mocker.patch("userbot.extractor.validate_whatsapp_link", return_value=True)

    start_date = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2026, 8, 5, 23, 59, 59, tzinfo=timezone.utc)

    # 1. Dialog 1: Private User Chat (Must be skipped)
    dialog_private = MagicMock()
    dialog_private.chat.type = ChatType.PRIVATE
    dialog_private.chat.id = 11111

    # 2. Dialog 2: Standard Group Chat (Must be scanned)
    dialog_group = MagicMock()
    dialog_group.chat.type = ChatType.GROUP
    dialog_group.chat.id = -10022222
    dialog_group.chat.title = "MathStudyGroup"

    # Messages in Group
    msg_new = MagicMock()
    msg_new.date = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)
    msg_new.text = "Newer link https://t.me/SkipNewer"
    msg_new.caption = None

    msg_valid = MagicMock()
    msg_valid.date = datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc)
    msg_valid.text = (
        "Telegram: https://t.me/ValidChannel "
        "Folder: https://t.me/addlist/StudyGroup "
        "WhatsApp: https://chat.whatsapp.com/ValidInvite123"
    )
    msg_valid.caption = None

    msg_old = MagicMock()
    msg_old.date = datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc)
    msg_old.text = "Old link https://t.me/OldGroupNeverReached"
    msg_old.caption = None

    # 3. Dialog 3: Supergroup Chat (Must be scanned)
    dialog_supergroup = MagicMock()
    dialog_supergroup.chat.type = ChatType.SUPERGROUP
    dialog_supergroup.chat.id = -10033333
    dialog_supergroup.chat.title = "EngineeringSupergroup"

    msg_super = MagicMock()
    msg_super.date = datetime(2026, 8, 2, 14, 0, 0, tzinfo=timezone.utc)
    msg_super.text = "Join supergroup link https://t.me/EngLink"
    msg_super.caption = None

    # Configure Pyrogram Client mock
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_dialogs.return_value = AsyncCustomIterator([dialog_private, dialog_group, dialog_supergroup])

    def get_history_side_effect(chat_id: int, limit: int = 10000) -> AsyncCustomIterator:
        if chat_id == -10022222:
            return AsyncCustomIterator([msg_new, msg_valid, msg_old])
        elif chat_id == -10033333:
            return AsyncCustomIterator([msg_super])
        return AsyncCustomIterator([])

    mock_client.get_chat_history.side_effect = get_history_side_effect
    mocker.patch("userbot.extractor.Client", return_value=mock_client)

    # Mock Aiogram Bot for live feedback
    mock_bot = MagicMock()
    mock_progress_msg = MagicMock()
    mock_progress_msg.message_id = 999
    mock_bot.send_message = AsyncMock(return_value=mock_progress_msg)
    mock_bot.edit_message_text = AsyncMock()

    saved_count = await extractor.run_extraction_task(
        session_name="test_session",
        start_date=start_date,
        end_date=end_date,
        target_type="all",
        bot=mock_bot,
        admin_chat_id=123456,
        limit_per_group=100,
    )

    # 1 tg + 1 folder + 1 wa + 1 supergroup tg = 4
    assert saved_count == 4
    assert mock_save.call_count == 4

    # Verify category mappings passed to save_link
    calls = mock_save.call_args_list
    assert calls[0].args[0] == "https://t.me/ValidChannel"
    assert calls[0].kwargs["category"] == "telegram_groups"

    assert calls[1].args[0] == "https://t.me/addlist/StudyGroup"
    assert calls[1].kwargs["category"] == "telegram_folders"

    assert calls[2].args[0] == "https://chat.whatsapp.com/ValidInvite123"
    assert calls[2].kwargs["category"] == "whatsapp"

    assert calls[3].args[0] == "https://t.me/EngLink"
    assert calls[3].kwargs["category"] == "telegram_groups"

    # Bot sent initial notification and final completion summary
    mock_bot.send_message.assert_awaited_once_with(chat_id=123456, text="🔍 Fetching your group list...")
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Global Extraction Complete!" in kwargs["text"]
    assert "Scanned Groups: <b>2</b>" in kwargs["text"]
    assert "WhatsApp: <b>1</b>" in kwargs["text"]
    assert "TG Groups: <b>2</b>" in kwargs["text"]
    assert "TG Folders: <b>1</b>" in kwargs["text"]
    assert "Total Links Saved:</b> <b>4</b>" in kwargs["text"]


@pytest.mark.asyncio
async def test_run_global_extraction_task_target_filtering(mocker: MockerFixture) -> None:
    """Test that target_type='whatsapp' selectively extracts WhatsApp links and ignores Telegram links."""
    mock_save = mocker.patch("userbot.extractor.save_link", return_value="/path/part_1.txt")
    mocker.patch("userbot.extractor.validate_whatsapp_link", return_value=True)

    dialog_group = MagicMock()
    dialog_group.chat.type = ChatType.GROUP
    dialog_group.chat.id = -10055555
    dialog_group.chat.title = "TargetFilteringGroup"

    msg = MagicMock()
    msg.date = None
    msg.text = (
        "Telegram channel: https://t.me/IgnoreMe "
        "WhatsApp group: https://chat.whatsapp.com/ExtractMeOnly123 "
        "Folder: https://t.me/addlist/IgnoreFolder"
    )
    msg.caption = None

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_dialogs.return_value = AsyncCustomIterator([dialog_group])
    mock_client.get_chat_history.return_value = AsyncCustomIterator([msg])
    mocker.patch("userbot.extractor.Client", return_value=mock_client)

    saved_count = await extractor.run_extraction_task(
        session_name="test_session",
        target_type="whatsapp",
    )

    assert saved_count == 1
    mock_save.assert_called_once_with("https://chat.whatsapp.com/ExtractMeOnly123", category="whatsapp")


@pytest.mark.asyncio
async def test_run_extraction_task_catches_group_level_errors(mocker: MockerFixture) -> None:
    """Test that group-level exceptions do not crash global iteration."""
    dialog_error = MagicMock()
    dialog_error.chat.type = ChatType.GROUP
    dialog_error.chat.id = -100999
    dialog_error.chat.title = "RestrictedGroup"

    dialog_ok = MagicMock()
    dialog_ok.chat.type = ChatType.GROUP
    dialog_ok.chat.id = -100888
    dialog_ok.chat.title = "OpenGroup"

    msg_ok = MagicMock()
    msg_ok.date = None
    msg_ok.text = "https://t.me/OpenLink"
    msg_ok.caption = None

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_dialogs.return_value = AsyncCustomIterator([dialog_error, dialog_ok])

    def get_history_side_effect(chat_id: int, limit: int = 10000) -> AsyncCustomIterator:
        if chat_id == -100999:
            raise ChatAdminRequired()
        return AsyncCustomIterator([msg_ok])

    mock_client.get_chat_history.side_effect = get_history_side_effect
    mocker.patch("userbot.extractor.Client", return_value=mock_client)
    mocker.patch("userbot.extractor.save_link", return_value="/path/part_1.txt")

    saved_count = await extractor.run_extraction_task("test_session")
    assert saved_count == 1


def test_extract_and_segregate_telegram_links() -> None:
    """Test extract_and_segregate_telegram_links correctly segregates standard and folder links."""
    sample_text = (
        "Check group https://t.me/PythonGroup, private invite https://t.me/+InviteHash123! "
        "Also folder https://t.me/addlist/DevFolder and tg://addlist?slug=DesignFolder."
    )
    group_links, folder_links = extractor.extract_and_segregate_telegram_links(sample_text)

    assert group_links == ["https://t.me/PythonGroup", "https://t.me/+InviteHash123"]
    assert folder_links == ["https://t.me/addlist/DevFolder", "https://t.me/addlist/DesignFolder"]


def test_extract_and_segregate_telegram_links_empty_or_none() -> None:
    """Test extract_and_segregate_telegram_links handles empty or non-string inputs safely."""
    assert extractor.extract_and_segregate_telegram_links("") == ([], [])
    assert extractor.extract_and_segregate_telegram_links(None) == ([], [])  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_run_extraction_task_mixed_links_segregated_saving(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test processing a batch of mixed links results in separate files in separate category directories."""
    # Point LINKS_DIR to tmp_path for real disk assertion
    mocker.patch("core.file_manager.LINKS_DIR", tmp_path)
    mocker.patch("userbot.extractor.validate_whatsapp_link", return_value=True)

    dialog_group = MagicMock()
    dialog_group.chat.type = ChatType.GROUP
    dialog_group.chat.id = -10077777
    dialog_group.chat.title = "MixedLinksGroup"

    msg1 = MagicMock()
    msg1.date = None
    msg1.text = (
        "Here are groups: https://t.me/TradingGroup and https://t.me/+PrivateInviteKey. "
        "And folder: https://t.me/addlist/TradingFolder."
    )
    msg1.caption = None

    msg2 = MagicMock()
    msg2.date = None
    msg2.text = (
        "Another folder tg://addlist?slug=FinanceFolder and WhatsApp "
        "https://chat.whatsapp.com/FinanceWaChat123"
    )
    msg2.caption = None

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_dialogs.return_value = AsyncCustomIterator([dialog_group])
    mock_client.get_chat_history.return_value = AsyncCustomIterator([msg1, msg2])
    mocker.patch("userbot.extractor.Client", return_value=mock_client)

    saved_count = await extractor.run_extraction_task(
        session_name="test_session",
        target_type="all",
    )

    # 2 groups + 2 folders + 1 whatsapp = 5
    assert saved_count == 5

    date_stamp = datetime.now().strftime("%Y-%m-%d")
    groups_file = tmp_path / date_stamp / "telegram_groups" / "part_1.txt"
    folders_file = tmp_path / date_stamp / "telegram_folders" / "part_1.txt"
    whatsapp_file = tmp_path / date_stamp / "whatsapp" / "part_1.txt"

    # Assert physical directory segregation
    assert groups_file.exists(), "telegram_groups/part_1.txt must exist"
    assert folders_file.exists(), "telegram_folders/part_1.txt must exist"
    assert whatsapp_file.exists(), "whatsapp/part_1.txt must exist"

    groups_content = groups_file.read_text(encoding="utf-8").strip().splitlines()
    folders_content = folders_file.read_text(encoding="utf-8").strip().splitlines()
    whatsapp_content = whatsapp_file.read_text(encoding="utf-8").strip().splitlines()

    assert groups_content == [
        "https://t.me/TradingGroup",
        "https://t.me/+PrivateInviteKey",
    ]
    # Ensure NO addlist in groups file
    for link in groups_content:
        assert "addlist" not in link.lower()

    assert folders_content == [
        "https://t.me/addlist/TradingFolder",
        "https://t.me/addlist/FinanceFolder",
    ]
    # Ensure ALL entries in folders file contain addlist
    for link in folders_content:
        assert "addlist" in link.lower()

    assert whatsapp_content == [
        "https://chat.whatsapp.com/FinanceWaChat123",
    ]

