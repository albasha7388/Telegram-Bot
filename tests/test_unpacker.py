"""
Tests for the Folder Unpacker module.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram import Bot
from pyrogram.raw.types.chatlists import ChatlistInvite
from pyrogram.raw.types import Channel, Chat

from core.file_manager import LINKS_DIR
from userbot.unpacker import run_folder_unpacker_task

@pytest.mark.asyncio
async def test_run_folder_unpacker_task_filters_and_chunks(tmp_path) -> None:
    """Test that unpacker correctly filters public groups and chunks them."""
    session_name = "test_unpacker_session"
    admin_id = 12345
    message_id = 99
    
    bot_mock = AsyncMock(spec=Bot)
    
    # Create 150 dummy channels (50 without username, 100 with username)
    dummy_chats = []
    for i in range(50):
        # Private groups
        c = Channel(id=i, title=f"Private {i}", date=0, photo=None)
        dummy_chats.append(c)
        
    for i in range(150):
        # Public groups
        c = Channel(id=i+100, title=f"Public {i}", username=f"public_group_{i}", date=0, photo=None)
        dummy_chats.append(c)
        
    # Duplicate username to test deduplication
    c = Channel(id=999, title="Dup", username="public_group_0", date=0, photo=None)
    dummy_chats.append(c)

    invite_mock = ChatlistInvite(title="Test Folder", peers=[], chats=dummy_chats, users=[])
    
    client_mock = AsyncMock()
    client_mock.invoke.return_value = invite_mock
    
    with patch("userbot.unpacker.Client", return_value=client_mock), \
         patch("core.process_manager.is_unpacker_running", return_value=True), \
         patch("userbot.unpacker.LINKS_DIR", tmp_path), \
         patch("userbot.unpacker.get_session_string", return_value="dummy_session_string"), \
         patch("userbot.unpacker.API_ID", 12345), \
         patch("userbot.unpacker.API_HASH", "dummy_hash"):
        
        await run_folder_unpacker_task(
            session_name=session_name,
            folder_links=["https://t.me/addlist/testslug"],
            bot=bot_mock,
            admin_chat_id=admin_id,
            message_id=message_id
        )
        
    # Should have generated 2 files (100 links in first, 50 in second due to 1 deduplicated)
    unpacked_dir = tmp_path / session_name / "unpacked"
    assert unpacked_dir.exists()
    files = list(unpacked_dir.iterdir())
    assert len(files) == 2
    
    # Sort files by creation or name
    files.sort(key=lambda x: x.name)
    
    with open(files[0], "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 100
        assert "https://t.me/public_group_0\n" in lines
        
    with open(files[1], "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 50
        
    # Verify bot sent the documents
    assert bot_mock.send_document.call_count == 2
    
    # Verify bot edited message with success
    bot_mock.edit_message_text.assert_called_once()
    call_args = bot_mock.edit_message_text.call_args[1]
    assert "150" in call_args["text"]  # Total Public Groups Extracted
