# AI STRICT DEVELOPMENT RULES & CONSTRAINTS (MASTER PROTOCOL)

## 1. Architectural Compliance (SOLID)
*   **SRP (Single Responsibility):** Do NOT create God Classes. Keep UI logic in `bot_ui/`, MTProto logic in `userbot/`, and validation in `validators/`.
*   **DIP (Dependency Inversion):** High-level modules (like the UI scheduler) must not depend on low-level scraping scripts directly.

## 2. Anti-Ban & Rate Limiting Protocols (CRITICAL)
*   **Global Sleep Rule:** NEVER execute bulk actions (joining, validating, messaging) without `asyncio.sleep()`.
*   **DM Daily Limit:** Implement a counter for outbound DMs to non-contacts. If the daily limit (e.g., 20 messages) is reached, suspend the DM function until the next day.
*   **Exception Catching:** Every Telegram API call MUST be wrapped in a `try-except` block specifically catching Pyrogram's RPC errors (e.g., `FloodWait`, `UserPrivacyRestricted`).

## 3. Code Quality & Formatting
*   **Type Hints:** Every function signature MUST use static type hints (e.g., `def parse_links(text: str) -> list[str]:`).
*   **Docstrings:** Every class and function MUST have a PEP 257 compliant docstring explaining parameters, return types, and exceptions.
*   **Resource Management:** ALWAYS use Context Managers (`with`) for file operations and session handling to prevent memory leaks.

## 4. Testing First (TDD & Mocking)
*   All code generated must be accompanied by a `pytest` unit test in the `tests/` directory.
*   NEVER make real network requests in tests. ALWAYS use `pytest-mock` to mock Telegram API calls and HTML requests.

## 5. Development Workflow (Vibe Coding Constraint)
*   The AI will receive prompts for ONE module/file at a time.
*   Do NOT generate the entire project at once.
*   Do NOT modify the established directory structure.
*   Only apply concepts from the reference markdown files (`01` to `12`) that are strictly necessary for the current task. Over-engineering simple functions is strictly prohibited.
## 6. Intelligent Filtering Logic (STRICT CONSTRAINT FOR `auto_reply.py`)
When implementing the `userbot_core` or `auto_reply.py`, the AI MUST enforce the following intent classification logic sequentially to differentiate between actual students and advertisers. Read from `data/keywords.json`:

1.  **Metadata Check (Immediate Ignore):** If the message exceeds `max_words_allowed` OR contains more than `max_emojis_allowed`, ignore it instantly.
2.  **Regex Contact Check (Immediate Ignore):** If the message matches ANY pattern in `regex_patterns` (phone numbers, WhatsApp links, Telegram mentions), ignore it instantly.
3.  **Negative Intent Check (Immediate Ignore):** Check the message string against the `negative_phrases` list. If any phrase exists, ignore it.
4.  **Positive Intent Check (Action):** ONLY after passing all the above checks, if the message contains ANY phrase from `positive_phrases`, trigger the auto-reply mechanism.
Do NOT use basic single-word matching. Enforce this 4-step pipeline strictly.


