"""
Aiogram 3.x router and FSM handlers for In-Bot Session Creation.

Enables administrators to create and authorize new Pyrogram MTProto sessions
directly via the Control Bot UI, with full Two-Step Verification (2FA) support,
Single Message UI paradigm, and safe lifecycle management of temporary MTProto clients.
"""

import re
from pathlib import Path
from typing import Final, Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
    RPCError,
    SessionPasswordNeeded,
)

from bot_ui.handlers import (
    build_dashboard_text,
    get_user_active_session,
    safe_callback_answer,
    set_user_active_session,
)
from bot_ui.keyboards import get_cancel_keyboard, get_main_menu
from bot_ui.states import LoginState
from config.settings import API_HASH, API_ID
from core.logger_setup import setup_logger
from core.process_manager import is_extraction_running, is_userbot_running
from userbot.session_manager import SESSIONS_DIR, get_available_sessions

logger = setup_logger(__name__)

# Dedicated Router instance for session login flows
router: Router = Router(name="login_router")

# In-memory registry of active temporary Pyrogram Client instances during login
_active_login_clients: dict[int, Client] = {}

# Session name validation regex (alphanumeric, underscores, hyphens, 2-32 chars)
SESSION_NAME_REGEX: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]{2,32}$")


async def cleanup_user_login_client(user_id: int) -> None:
    """Disconnect and deregister any active temporary login client for the specified user.

    Args:
        user_id: Telegram user ID whose temporary client should be cleaned up.
    """
    client: Optional[Client] = _active_login_clients.pop(user_id, None)
    if client is not None:
        try:
            if getattr(client, "is_connected", False):
                await client.disconnect()
            logger.info("Safely disconnected temporary login client for user %d.", user_id)
        except Exception as exc:
            logger.warning("Error disconnecting temporary login client for user %d: %s", user_id, exc)


async def _safe_delete_message(message: Message) -> None:
    """Delete an incoming user message to maintain the Single Message UI paradigm.

    Args:
        message: The incoming Telegram message to remove.
    """
    try:
        await message.delete()
    except Exception as exc:
        logger.debug("Failed deleting user input message in login flow: %s", exc)


async def _update_prompt_ui(
    message: Message,
    prompt_message_id: Optional[int],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Edit the existing UI prompt message or fallback to a new answer message.

    Args:
        message: Incoming trigger message.
        prompt_message_id: Target message ID to edit.
        text: HTML text content to display.
        reply_markup: Optional inline keyboard to attach.
    """
    user_id = message.from_user.id if message.from_user else 0
    if prompt_message_id and message.bot:
        try:
            await message.bot.edit_message_text(
                chat_id=user_id,
                message_id=prompt_message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest as exc:
            logger.debug("TelegramBadRequest while updating login prompt UI: %s", exc)
        except Exception as exc:
            logger.warning("Failed editing login prompt message: %s", exc)

    await message.answer(text=text, parse_mode="HTML", reply_markup=reply_markup)


# --- Step 1: Trigger Add Session ---

@router.callback_query(F.data == "menu_add_session")
async def start_add_session_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle request to initiate a new Pyrogram session authorization workflow.

    Args:
        callback: The incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    # Clean up any leftover temporary client
    await cleanup_user_login_client(user_id)

    await state.set_state(LoginState.waiting_for_session_name)
    if callback.message:
        await state.update_data(prompt_message_id=callback.message.message_id)

    prompt_text = (
        "➕ <b>Add New Session (Step 1/3)</b>\n\n"
        "Please enter a <b>name</b> for this new session (account):\n"
        "<i>(e.g., <code>account_marketing</code>, <code>tg_personal_2</code>)</i>\n\n"
        "Only alphanumeric characters, dashes, and underscores (2-32 characters) are allowed."
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on start add session: %s", exc)

    await safe_callback_answer(callback)
    logger.info("User %d started in-bot session creation workflow.", user_id)


# --- Step 2: Receive Session Name ---

@router.message(LoginState.waiting_for_session_name)
async def process_session_name_handler(message: Message, state: FSMContext) -> None:
    """Validate the provided session name and prompt the user for their phone number.

    Args:
        message: The incoming message containing the desired session name.
        state: FSM execution context.
    """
    await _safe_delete_message(message)

    user_id = message.from_user.id if message.from_user else 0
    raw_name = message.text.strip() if message.text else ""
    if raw_name.endswith(".session"):
        raw_name = raw_name[:-8]

    state_data = await state.get_data()
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")

    # Validate session name format
    if not SESSION_NAME_REGEX.match(raw_name):
        error_text = (
            "⚠️ <b>Invalid Session Name!</b>\n\n"
            "Session name must be 2 to 32 characters long and contain only "
            "letters, numbers, underscores (<code>_</code>), or dashes (<code>-</code>).\n\n"
            "Please enter a valid session name:"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Check for duplicate session name
    existing_sessions = get_available_sessions()
    if raw_name in existing_sessions:
        error_text = (
            "⚠️ <b>Session Already Exists!</b>\n\n"
            f"A session named <code>{raw_name}</code> already exists in your sessions folder.\n\n"
            "Please enter a different unique session name:"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Valid name -> Save and transition to waiting_for_phone
    await state.update_data(session_name=raw_name)
    await state.set_state(LoginState.waiting_for_phone)

    prompt_text = (
        "📱 <b>Add New Session (Step 2/3)</b>\n\n"
        f"Session Name: <code>{raw_name}</code>\n\n"
        "Please send the <b>phone number</b> associated with this Telegram account in international format:\n"
        "Example: <code>+1234567890</code> or <code>+201234567890</code>"
    )
    await _update_prompt_ui(
        message=message,
        prompt_message_id=prompt_message_id,
        text=prompt_text,
        reply_markup=get_cancel_keyboard(),
    )
    logger.info("User %d submitted valid session name: %s", user_id, raw_name)


# --- Step 3: Receive Phone Number, Initialize Client, and Send Code ---

@router.message(LoginState.waiting_for_phone)
async def process_phone_number_handler(message: Message, state: FSMContext) -> None:
    """Validate phone number, initialize temporary Pyrogram Client, and send OTP code.

    Args:
        message: The incoming message containing the international phone number.
        state: FSM execution context.
    """
    await _safe_delete_message(message)

    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")
    session_name: Optional[str] = state_data.get("session_name")

    if not session_name:
        await state.clear()
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text="⚠️ <b>Session creation flow lost.</b> Please restart from the main menu.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    raw_phone = message.text.strip() if message.text else ""
    cleaned_phone = re.sub(r"[\s\-\(\)]", "", raw_phone)
    if not cleaned_phone.startswith("+") and cleaned_phone.isdigit():
        cleaned_phone = f"+{cleaned_phone}"

    # Basic international phone regex validation (+ followed by 7-15 digits)
    if not re.match(r"^\+[1-9]\d{6,14}$", cleaned_phone):
        error_text = (
            "⚠️ <b>Invalid Phone Number Format!</b>\n\n"
            "Please send a valid international phone number starting with '+' and the country code.\n"
            "Example: <code>+1234567890</code> or <code>+201234567890</code>"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Initialize temporary Pyrogram client in sessions/
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    client = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=str(SESSIONS_DIR),
    )
    _active_login_clients[user_id] = client

    # Inform user that the code is being requested
    connecting_text = (
        "⏳ <b>Connecting to Telegram...</b>\n\n"
        "Requesting authentication code, please wait..."
    )
    await _update_prompt_ui(
        message=message,
        prompt_message_id=prompt_message_id,
        text=connecting_text,
        reply_markup=get_cancel_keyboard(),
    )

    try:
        await client.connect()
        sent_code = await client.send_code(cleaned_phone)
        phone_code_hash = sent_code.phone_code_hash
    except FloodWait as exc:
        logger.warning("FloodWait of %d seconds when sending code to user %d.", exc.value, user_id)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        flood_text = (
            f"⏳ <b>Telegram Rate Limit (FloodWait)</b>\n\n"
            f"Telegram requires a wait of <b>{exc.value}</b> seconds before sending another code.\n"
            "Please try again later."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=flood_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
        return
    except (PhoneNumberInvalid, PhoneNumberUnoccupied, PhoneNumberBanned) as exc:
        logger.warning("Invalid/unoccupied phone number provided by user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>Invalid or Unoccupied Phone Number</b>\n\n"
            "Telegram reported that this phone number is not registered, banned, or invalid.\n"
            "Please verify the number and try again."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
        return
    except (RPCError, Exception) as exc:
        logger.error("Failed sending Telegram code for user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>Authentication Error</b>\n\n"
            f"Failed to request code from Telegram: <code>{type(exc).__name__}</code>\n"
            "Please verify your credentials and try again."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
        return

    # Update state data with phone & hash and transition to waiting_for_code
    await state.update_data(
        phone=cleaned_phone,
        phone_code_hash=phone_code_hash,
    )
    await state.set_state(LoginState.waiting_for_code)

    code_prompt_text = (
        "📩 <b>Enter Telegram OTP Code (Step 3/3)</b>\n\n"
        f"A login code has been sent to your Telegram app / SMS for <code>{cleaned_phone}</code>.\n\n"
        "Please enter the login code:\n"
        "<i>(You can enter it with or without spaces, e.g. <code>1 2 3 4 5</code> or <code>12345</code>)</i>"
    )
    await _update_prompt_ui(
        message=message,
        prompt_message_id=prompt_message_id,
        text=code_prompt_text,
        reply_markup=get_cancel_keyboard(),
    )
    logger.info("Successfully dispatched OTP code for session '%s'.", session_name)


# --- Step 4: Receive OTP Code & Sign In (Handle 2FA Transition) ---

@router.message(LoginState.waiting_for_code)
async def process_otp_code_handler(message: Message, state: FSMContext) -> None:
    """Validate OTP code and sign in via Pyrogram client, handling 2FA if required.

    Args:
        message: The incoming message containing the OTP code.
        state: FSM execution context.
    """
    await _safe_delete_message(message)

    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")
    session_name: Optional[str] = state_data.get("session_name")
    phone: Optional[str] = state_data.get("phone")
    phone_code_hash: Optional[str] = state_data.get("phone_code_hash")

    client = _active_login_clients.get(user_id)
    if not client or not phone or not phone_code_hash or not session_name:
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        lost_text = "⚠️ <b>Login session expired or lost.</b> Please restart from the main menu."
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=lost_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
        return

    raw_code = message.text.strip() if message.text else ""
    cleaned_code = re.sub(r"[\s\-]", "", raw_code)

    if not cleaned_code:
        error_text = (
            "⚠️ <b>Invalid Code!</b>\n\n"
            "Please enter the numeric login code you received from Telegram:"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_cancel_keyboard(),
        )
        return

    try:
        await client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=cleaned_code,
        )
        # Sign in successful without 2FA!
        await cleanup_user_login_client(user_id)
        set_user_active_session(user_id, session_name)
        await state.clear()

        userbot_on = is_userbot_running(session_name)
        extractor_on = is_extraction_running(session_name)
        success_text = (
            "✅ <b>Session Created Successfully!</b>\n\n"
            f"Account <code>{session_name}</code> has been authorized and set as your active session.\n\n"
            + build_dashboard_text(session_name)
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=success_text,
            reply_markup=get_main_menu(
                active_session=session_name,
                is_userbot_on=userbot_on,
                is_extractor_on=extractor_on,
            ),
        )
        logger.info("Session '%s' created and authorized successfully for user %d.", session_name, user_id)

    except SessionPasswordNeeded:
        # 2FA (Two-Step Verification) is enabled on this account
        logger.info("Session '%s' requires 2FA password. Transitioning to waiting_for_password.", session_name)
        await state.set_state(LoginState.waiting_for_password)

        prompt_2fa_text = (
            "🔐 <b>Two-Step Verification (2FA) Required</b>\n\n"
            "This Telegram account is protected by Two-Step Verification.\n\n"
            "Please enter your <b>Cloud Password</b> to complete authorization:"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=prompt_2fa_text,
            reply_markup=get_cancel_keyboard(),
        )

    except (PhoneCodeInvalid, PhoneCodeExpired) as exc:
        logger.warning("Invalid/expired OTP code entered for user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>Invalid or Expired Code</b>\n\n"
            "The login code you entered is invalid or has expired.\n"
            "Please restart the session creation process to obtain a fresh code."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )

    except FloodWait as exc:
        logger.warning("FloodWait of %d seconds on sign_in for user %d.", exc.value, user_id)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        flood_text = (
            f"⏳ <b>Telegram Rate Limit (FloodWait)</b>\n\n"
            f"Telegram requires a wait of <b>{exc.value}</b> seconds.\n"
            "Please try again later."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=flood_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )

    except (RPCError, Exception) as exc:
        logger.error("Failed sign_in for user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>Sign-In Failed</b>\n\n"
            f"An error occurred during authentication: <code>{type(exc).__name__}</code>\n"
            "Please restart session creation."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )


# --- Step 5: Receive 2FA Password & Complete Sign In ---

@router.message(LoginState.waiting_for_password)
async def process_2fa_password_handler(message: Message, state: FSMContext) -> None:
    """Verify the 2FA cloud password and finalize Pyrogram session creation.

    Args:
        message: The incoming message containing the 2FA password.
        state: FSM execution context.
    """
    await _safe_delete_message(message)

    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")
    session_name: Optional[str] = state_data.get("session_name")

    client = _active_login_clients.get(user_id)
    if not client or not session_name:
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        lost_text = "⚠️ <b>Login session expired or lost.</b> Please restart from the main menu."
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=lost_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
        return

    password = message.text.strip() if message.text else ""
    if not password:
        error_text = (
            "⚠️ <b>Password cannot be empty!</b>\n\n"
            "Please enter your 2FA Cloud Password:"
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_cancel_keyboard(),
        )
        return

    try:
        await client.check_password(password=password)
        # 2FA authorization succeeded!
        await cleanup_user_login_client(user_id)
        set_user_active_session(user_id, session_name)
        await state.clear()

        userbot_on = is_userbot_running(session_name)
        extractor_on = is_extraction_running(session_name)
        success_text = (
            "✅ <b>Session Created Successfully! (2FA Verified)</b>\n\n"
            f"Account <code>{session_name}</code> has been authorized and set as your active session.\n\n"
            + build_dashboard_text(session_name)
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=success_text,
            reply_markup=get_main_menu(
                active_session=session_name,
                is_userbot_on=userbot_on,
                is_extractor_on=extractor_on,
            ),
        )
        logger.info("Session '%s' 2FA authorized successfully for user %d.", session_name, user_id)

    except PasswordHashInvalid as exc:
        logger.warning("Invalid 2FA password entered by user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>Invalid 2FA Password</b>\n\n"
            "The Two-Step Verification password you entered is incorrect.\n"
            "Session creation aborted. Please try again."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )

    except FloodWait as exc:
        logger.warning("FloodWait of %d seconds on check_password for user %d.", exc.value, user_id)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        flood_text = (
            f"⏳ <b>Telegram Rate Limit (FloodWait)</b>\n\n"
            f"Telegram requires a wait of <b>{exc.value}</b> seconds.\n"
            "Please try again later."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=flood_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )

    except (RPCError, Exception) as exc:
        logger.error("Failed check_password for user %d: %s", user_id, exc)
        await cleanup_user_login_client(user_id)
        await state.clear()
        active_session = get_user_active_session(user_id)
        error_text = (
            "❌ <b>2FA Verification Failed</b>\n\n"
            f"An error occurred during 2FA verification: <code>{type(exc).__name__}</code>\n"
            "Please restart session creation."
        )
        await _update_prompt_ui(
            message=message,
            prompt_message_id=prompt_message_id,
            text=error_text,
            reply_markup=get_main_menu(
                active_session=active_session,
                is_userbot_on=is_userbot_running(active_session),
                is_extractor_on=is_extraction_running(active_session),
            ),
        )
