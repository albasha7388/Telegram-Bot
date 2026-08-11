"""
Unit tests for global group chat link extraction, exact date bounds, granular target filtering, and live progress updates.
"""

from datetime import datetime, timezone
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
