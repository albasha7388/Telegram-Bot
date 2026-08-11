# SYSTEM FUNCTIONS & LIFECYCLE SPECIFICATION
This document defines the exact execution lifecycle for every module in the Hybrid Telegram Bot system. The AI must strictly implement these lifecycles without deviation.

## 1. Smart Auto-Reply (Private & Group)
*   **Trigger:** The backend Userbot listens to incoming messages using Pyrogram.
*   **Negative Filter (Pre-condition):** The system first checks the message against a large JSON list of negative/exclusion keywords. If a match is found, the message is instantly ignored to save CPU cycles.
*   **Positive Filter:** If clean, it checks for positive keywords.
*   **Execution:** Applies a random `asyncio.sleep()` (e.g., 5-12s) to mimic human behavior.
*   **DM Privacy Handling:** When replying in private messages (DM), the system MUST wrap the send function in a `try-except` block. If `UserPrivacyRestricted` or `UserIsBlocked` is raised, it silently catches the exception, aborts the reply, and logs the event without crashing.

## 2. UI-Based Multi-Session Switching
*   **Initialization:** The system reads the `sessions/` directory to find all `.session` files. No login happens via the UI.
*   **State Management:** The active session is stored in memory/state. The UI displays the active session clearly (e.g., "🟢 Active: account_1").
*   **Switching:** When the user clicks the switch button, the state updates instantly. Any subsequent MTProto command will execute using the newly selected session client.

## 3. Telegram & Folder Links Validation
*   **Extraction:** Uses precise Regex boundaries to extract `t.me/` and `t.me/addlist/` (Folders) from a specified date range in the chat history.
*   **Validation:** Sends API requests to verify validity.
*   **Anti-Ban Measure:** Strictly enforces a randomized `sleep` (10-20 seconds) between each API validation request to prevent FloodWait bans.

## 4. WhatsApp Links Validation (Web Scraping)
*   **Extraction:** Uses Regex for `chat.whatsapp.com`.
*   **Validation:** Operates entirely outside the Telegram API. Uses `requests` and `BeautifulSoup4` to fetch the HTML and search for the "Join Chat" button.
*   **Anti-Ban Measure:** Enforces sleep timers between HTTP requests to prevent IP blocking by Meta servers.

## 5. TXT File Pagination System
*   **Threshold:** Set a hard limit (e.g., 100 links per file).
*   **Execution:** Opens `links_part1.txt` using a Context Manager (`with open...`). Once 100 lines are written, it safely closes the file and dynamically creates `links_part2.txt`.

## 6. Centralized Logging & Error Handling
*   **Rule:** Every action, exception, or UI interaction MUST be logged to `data/bot_logs.txt` using Python's `logging` module.
*   **Security:** NEVER log sensitive data (Tokens, API Hashes, Phone numbers, or private message content).
