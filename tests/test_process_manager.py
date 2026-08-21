"""
Unit tests for background process manager and non-blocking task supervisor.
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
from pytest_mock import MockerFixture

from core import process_manager


@pytest.fixture(autouse=True)
def cleanup_active_tasks() -> None:
    """Ensure process manager task registries and client pools are wiped clean before each test."""
    for task in list(process_manager.active_tasks.values()):
        if not task.done():
            task.cancel()
    process_manager.active_tasks.clear()

    for task in list(process_manager.active_extractions.values()):
        if not task.done():
            task.cancel()
    for task in list(process_manager.active_joiners.values()):
        if not task.done():
            task.cancel()
    process_manager.active_joiners.clear()
    process_manager.joiner_sleep_state.clear()

    from userbot.client import active_userbot_clients
    active_userbot_clients.clear()


# --- 1. Joiner Sleep State Tests ---

def test_joiner_sleep_state_set_and_get() -> None:
    """Test getting and setting the sleep state for the Auto-Joiner."""
    assert process_manager.get_joiner_sleep_state("acc1") is None
    
    process_manager.set_joiner_sleep_state("acc1", 1234567.8, conflict=True)
    state = process_manager.get_joiner_sleep_state("acc1")
    assert state == {"until": 1234567.8, "conflict": True}
    
    process_manager.set_joiner_sleep_state("acc1", 0)
    assert process_manager.get_joiner_sleep_state("acc1") is None


# --- 1. Userbot Task Tests ---

@pytest.mark.asyncio
async def test_is_userbot_running_detects_connected_client() -> None:
    """Test is_userbot_running returns True if Pyrogram client is connected in active_userbot_clients."""
    from unittest.mock import MagicMock
    from userbot.client import active_userbot_clients
    mock_client = MagicMock()
    mock_client.is_connected = True
    active_userbot_clients["connected_acc"] = mock_client

    assert process_manager.is_userbot_running("connected_acc") is True
    active_userbot_clients.clear()

@pytest.mark.asyncio
async def test_start_userbot_task_creates_asyncio_task(mocker: MockerFixture) -> None:
    """Test launching a new background userbot engine using non-blocking asyncio.create_task."""
    mock_run = mocker.patch("core.process_manager.run_userbot", new_callable=AsyncMock)

    started = await process_manager.start_userbot_task("session_alpha")

    assert started is True
    assert process_manager.is_userbot_running("session_alpha") is True
    assert "session_alpha" in process_manager.active_tasks

    task = process_manager.active_tasks["session_alpha"]
    assert isinstance(task, asyncio.Task)
    task.cancel()


@pytest.mark.asyncio
async def test_start_userbot_task_already_running_rejected(mocker: MockerFixture) -> None:
    """Test that attempting to start an already running session task returns False."""
    mocker.patch("core.process_manager.run_userbot", new_callable=AsyncMock)

    started_first = await process_manager.start_userbot_task("session_alpha")
    assert started_first is True

    started_second = await process_manager.start_userbot_task("session_alpha")
    assert started_second is False


@pytest.mark.asyncio
async def test_stop_userbot_task_cancels_and_removes(mocker: MockerFixture) -> None:
    """Test stopping an active background task properly cancels and removes it from registry."""
    mocker.patch("core.process_manager.run_userbot", new_callable=AsyncMock)

    await process_manager.start_userbot_task("session_beta")
    assert process_manager.is_userbot_running("session_beta") is True

    stopped = await process_manager.stop_userbot_task("session_beta")
    assert stopped is True
    assert process_manager.is_userbot_running("session_beta") is False
    assert "session_beta" not in process_manager.active_tasks


@pytest.mark.asyncio
async def test_stop_userbot_task_non_existent() -> None:
    """Test stopping a session that is not running gracefully returns False."""
    stopped = await process_manager.stop_userbot_task("unregistered_session")
    assert stopped is False


@pytest.mark.asyncio
async def test_get_all_active_sessions_listing(mocker: MockerFixture) -> None:
    """Test listing all active session identifiers in alphabetical order."""
    mocker.patch("core.process_manager.run_userbot", new_callable=AsyncMock)

    await process_manager.start_userbot_task("gamma_session")
    await process_manager.start_userbot_task("alpha_session")

    active_list = process_manager.get_all_active_sessions()
    assert active_list == ["alpha_session", "gamma_session"]


# --- 2. Global Extraction Task Tests ---

@pytest.mark.asyncio
async def test_start_extraction_task_creates_asyncio_task(mocker: MockerFixture) -> None:
    """Test launching a background global group link extraction task using non-blocking asyncio.create_task."""
    mocker.patch("core.process_manager.run_extraction_task", new_callable=AsyncMock)

    started = await process_manager.start_extraction_task("extract_session")

    assert started is True
    assert process_manager.is_extraction_running("extract_session") is True
    assert "extract_session" in process_manager.active_extractions

    task = process_manager.active_extractions["extract_session"]
    assert isinstance(task, asyncio.Task)
    task.cancel()


@pytest.mark.asyncio
async def test_start_extraction_task_already_running_rejected(mocker: MockerFixture) -> None:
    """Test duplicate extraction task initiation is rejected with False."""
    mocker.patch("core.process_manager.run_extraction_task", new_callable=AsyncMock)

    await process_manager.start_extraction_task("extract_session")
    duplicate = await process_manager.start_extraction_task("extract_session")
    assert duplicate is False


@pytest.mark.asyncio
async def test_stop_extraction_task_cancels_and_removes(mocker: MockerFixture) -> None:
    """Test cancelling and removing an active extraction task."""
    mocker.patch("core.process_manager.run_extraction_task", new_callable=AsyncMock)

    await process_manager.start_extraction_task("extract_session")
    assert process_manager.is_extraction_running("extract_session") is True

    stopped = await process_manager.stop_extraction_task("extract_session")
    assert stopped is True
    assert process_manager.is_extraction_running("extract_session") is False
    assert "extract_session" not in process_manager.active_extractions


@pytest.mark.asyncio
async def test_stop_extraction_task_non_existent() -> None:
    """Test stopping an extraction session that is not running returns False."""
    stopped = await process_manager.stop_extraction_task("unregistered_extractor")
    assert stopped is False


@pytest.mark.asyncio
async def test_get_all_active_extractions_listing(mocker: MockerFixture) -> None:
    """Test listing all active extraction identifiers in sorted order."""
    mocker.patch("core.process_manager.run_extraction_task", new_callable=AsyncMock)

    await process_manager.start_extraction_task("zeta_session")
    await process_manager.start_extraction_task("beta_session")

    extractions_list = process_manager.get_all_active_extractions()
    assert extractions_list == ["beta_session", "zeta_session"]


# --- 3. Auto-Joiner Task Tests ---

@pytest.mark.asyncio
async def test_is_joiner_running_and_stop_joiner_task() -> None:
    """Test is_joiner_running detects active task and stop_joiner_task cancels and removes it."""
    mock_task = asyncio.create_task(asyncio.sleep(10))
    process_manager.active_joiners["join_sess"] = mock_task

    assert process_manager.is_joiner_running("join_sess") is True
    assert process_manager.is_joiner_running("non_existent") is False
    assert process_manager.is_joiner_running(None) is False

    stopped = process_manager.stop_joiner_task("join_sess")
    assert stopped is True
    assert mock_task.cancelled() or mock_task.cancelling()
    assert "join_sess" not in process_manager.active_joiners
    assert process_manager.is_joiner_running("join_sess") is False


@pytest.mark.asyncio
async def test_stop_joiner_task_non_existent() -> None:
    """Test stopping an auto-joiner session that is not running returns False."""
    stopped = process_manager.stop_joiner_task("unregistered_joiner")
    assert stopped is False
