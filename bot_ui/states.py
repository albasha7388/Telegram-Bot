"""
FSM (Finite State Machine) states for Aiogram Control UI conversation flows.
"""

from aiogram.fsm.state import State, StatesGroup


class ExtractionState(StatesGroup):
    """FSM states governing the global group link extraction workflow."""

    waiting_for_date_range = State()


class LoginState(StatesGroup):
    """FSM states governing the in-bot Pyrogram session creation workflow."""

    waiting_for_session_name = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()


class SessionState(StatesGroup):
    """FSM states governing session management workflows (e.g. rename)."""

    waiting_for_new_session_name = State()


class JoinerState(StatesGroup):
    """FSM states governing granular Auto-Joiner target selection workflow."""

    selecting_date = State()
    selecting_file = State()


class DownloadState(StatesGroup):
    """FSM states governing granular link file download workflow."""

    selecting_date = State()
    selecting_file = State()




