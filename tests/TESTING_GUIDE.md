# Hybrid Telegram System - Testing & Verification Guide

This document is the centralized guide for running unit tests across the codebase. Following Test-Driven Development (TDD) principles, all new modules must be accompanied by unit tests and documented in this guide.

---

## General Test Runner Commands

Run all tests in the repository:
```bash
pytest -v
```

Run tests with short summary:
```bash
pytest -q
```

---

## 1. Centralized Settings & Configuration Tests

* **File:** [`tests/test_settings.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_settings.py)
* **Command:**
  ```bash
  pytest tests/test_settings.py -v
  ```
* **Purpose:**
  Verifies system constants (`MAX_DAILY_DMS`, `LINKS_PER_FILE`, `TIME_SLEEP_MIN`, `TIME_SLEEP_MAX`), environment variable validation (`API_ID`, `API_HASH`, `BOT_TOKEN`, `ARCHIVE_CHANNEL_ID`), type casting, error states, dynamic module attribute resolution, and `data/keywords.json` schema integrity.
* **Expected Output:**
  ```text
  tests/test_settings.py::test_system_constants PASSED                       [ 14%]
  tests/test_settings.py::test_missing_env_raises_value_error PASSED         [ 28%]
  tests/test_settings.py::test_invalid_api_id_type PASSED                    [ 42%]
  tests/test_settings.py::test_valid_env_variables PASSED                    [ 57%]
  tests/test_settings.py::test_archive_channel_id PASSED                     [ 71%]
  tests/test_settings.py::test_undefined_module_attribute PASSED            [ 85%]
  tests/test_settings.py::test_keywords_json_structure PASSED                [100%]

  ============================== 7 passed in 0.05s ==============================
  ```

---

## 2. Centralized Logger Setup Tests

* **File:** [`tests/test_logger_setup.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_logger_setup.py)
* **Command:**
  ```bash
  pytest tests/test_logger_setup.py -v
  ```
* **Purpose:**
  Verifies standard logger initialization, dynamic creation of `logs/operations/` and `logs/errors/` sub-directories, dynamic date-stamped log file path generation (`operations_{current_date}.log`, `errors_{current_date}.log`), configuration of console (`StreamHandler`), standard Windows-safe `FileHandler` attachment without rotation conflicts, singleton handler preservation (`if not logger.handlers:`), and isolated ERROR-level file logging.
* **Expected Output:**
  ```text
  tests/test_logger_setup.py::test_setup_logger_directory_creation PASSED       [ 20%]
  tests/test_logger_setup.py::test_get_log_paths_date_injection PASSED          [ 40%]
  tests/test_logger_setup.py::test_setup_logger_handler_targets PASSED          [ 60%]
  tests/test_logger_setup.py::test_setup_logger_no_duplicate_handlers PASSED   [ 80%]
  tests/test_logger_setup.py::test_logger_file_output_separation PASSED        [100%]

  ============================== 5 passed in 0.05s ==============================
  ```

---

## 3. File Manager, Multi-Tenant Isolation & Strict Pagination Tests

* **File:** [`tests/test_file_manager.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_file_manager.py)
* **Command:**
  ```bash
  pytest tests/test_file_manager.py -v
  ```
* **Purpose:**
  Verifies input sanitization for links, creation of nested date-stamped category directories under dynamic session folders (`data/links/<session_name>/YYYY-MM-DD/<category>/part_X.txt`), strict 100-link pagination roll-over (`part_1.txt` -> `part_2.txt` -> `part_3.txt`), chronological and numerical ordering in `get_files_by_category()` scoped per session, granular category breakdown counting in `get_total_links_count()` returning a dictionary (`whatsapp`, `telegram_groups`, `telegram_folders`, `total`), non-blocking asynchronous counting via `get_total_links_count_async()`, date discovery via `get_available_dates_for_category()`, part file discovery via `get_files_for_category_and_date()`, and **run isolation** where `save_link(..., run_timestamp=...)` creates isolated files per run (`part_{run_timestamp}.txt`) with dedicated rollover pagination (`part_{run_timestamp}_2.txt`).
* **Expected Output:**
  ```text
  tests/test_file_manager.py::test_save_link_empty_validation PASSED                   [ 11%]
  tests/test_file_manager.py::test_save_link_nested_directory_structure PASSED         [ 22%]
  tests/test_file_manager.py::test_save_link_strict_100_pagination PASSED              [ 33%]
  tests/test_file_manager.py::test_get_files_by_category_ordering PASSED               [ 44%]
  tests/test_file_manager.py::test_get_all_link_files_and_total_count PASSED           [ 55%]
  tests/test_file_manager.py::test_get_available_dates_for_category PASSED            [ 66%]
  tests/test_file_manager.py::test_get_files_for_category_and_date PASSED              [ 77%]
  tests/test_file_manager.py::test_save_link_run_timestamp_isolation PASSED          [ 88%]
  tests/test_file_manager.py::test_save_link_run_timestamp_pagination PASSED         [100%]

  ============================== 9 passed in 0.07s ==============================
  ```

---

## 4. Link Extraction & Validator Tests

* **File:** [`tests/test_validators.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_validators.py)
* **Command:**
  ```bash
  pytest tests/test_validators.py -v
  ```
* **Purpose:**
  Verifies regex extraction for standard Telegram invite and channel links (with strict exclusion of `addlist`), shareable folder link extraction (`t.me/addlist/...`), WhatsApp group invite extraction, and fast structural regular expression validation of WhatsApp invite links with zero network requests.
* **Expected Output:**
  ```text
  tests/test_validators.py::test_extract_telegram_links_standard PASSED              [ 11%]
  tests/test_validators.py::test_extract_telegram_links_ignores_folder_addlists PASSED [ 22%]
  tests/test_validators.py::test_extract_telegram_links_empty_and_deduplication PASSED [ 33%]
  tests/test_validators.py::test_extract_folder_links_standard PASSED                [ 44%]
  tests/test_validators.py::test_extract_folder_links_ignores_standard_invites PASSED [ 55%]
  tests/test_validators.py::test_extract_whatsapp_links_standard PASSED              [ 66%]
  tests/test_validators.py::test_extract_whatsapp_links_empty_and_punctuation PASSED [ 77%]
  tests/test_validators.py::test_validate_whatsapp_link_valid PASSED                 [ 88%]
  tests/test_validators.py::test_validate_whatsapp_link_invalid PASSED               [100%]

  ============================== 9 passed in 0.05s ==============================
  ```

---

## 5. Userbot Session & Intent Evaluation Tests

* **File:** [`tests/test_userbot.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_userbot.py)
* **Command:**
  ```bash
  pytest tests/test_userbot.py -v
  ```
* **Purpose:**
  Verifies Pyrogram session discovery in `sessions/` and the 4-step intent evaluation pipeline in `userbot/auto_reply.py` (Step 1 metadata limits on words and emojis, Step 2 regex contact filtering, Step 3 negative commercial phrase rejection, and Step 4 positive matrix verification of intent and subject words).
* **Expected Output:**
  ```text
  tests/test_userbot.py::test_get_available_sessions_directory_not_found PASSED            [ 11%]
  tests/test_userbot.py::test_get_available_sessions_discovery PASSED                      [ 22%]
  tests/test_userbot.py::test_evaluate_message_valid_student PASSED                         [ 33%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_emojis_metadata PASSED          [ 44%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_word_count_metadata PASSED      [ 55%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_regex_phone PASSED              [ 66%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_regex_whatsapp PASSED           [ 77%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_regex_telegram_username PASSED  [ 88%]
  tests/test_userbot.py::test_evaluate_message_rejected_by_negative_intent PASSED          [100%]

  ============================== 9 passed in 0.06s ==============================
  ```

---

## 6. Pyrogram Userbot Client & Handlers Tests

* **File:** [`tests/test_userbot_client.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_userbot_client.py)
* **Command:**
  ```bash
  pytest tests/test_userbot_client.py -v
  ```
* **Purpose:**
  Verifies asynchronous Pyrogram message listeners using `pytest-mock` and `pytest-asyncio`. Checks that genuine student inquiries trigger private message replies after a simulated sleep delay, enforces early daily DM limit checks (`MAX_DAILY_DMS = 20`) before intent processing, verifies bulletproof error handling for `UserPrivacyRestricted`, `UserIsBlocked`, `PeerIdInvalid`, and fallback exceptions ensuring the daily counter is NOT incremented on failed sends, validates multi-source link extraction routing, and verifies graceful `stop_userbot_client` disconnects.
* **Expected Output:**
  ```text
  tests/test_userbot_client.py::test_handle_auto_reply_successful_dm PASSED                 [ 11%]
  tests/test_userbot_client.py::test_handle_auto_reply_catches_privacy_restricted_no_counter_increment PASSED [ 22%]
  tests/test_userbot_client.py::test_handle_auto_reply_catches_user_is_blocked_no_counter_increment PASSED [ 33%]
  tests/test_userbot_client.py::test_handle_auto_reply_catches_peer_id_invalid_no_counter_increment PASSED [ 44%]
  tests/test_userbot_client.py::test_handle_auto_reply_catches_generic_exception_fallback PASSED [ 55%]
  tests/test_userbot_client.py::test_handle_auto_reply_aborts_early_when_daily_limit_exceeded PASSED [ 66%]
  tests/test_userbot_client.py::test_can_send_dm_enforces_max_daily_limit PASSED           [ 77%]
  tests/test_userbot_client.py::test_handle_link_extraction_end_to_end PASSED              [ 88%]
  tests/test_userbot_client.py::test_stop_userbot_client_graceful_shutdown PASSED          [100%]
  tests/test_userbot_client.py::test_stop_userbot_client_graceful_shutdown PASSED          [ 100%]

  ============================== 9 passed in 0.08s ==============================
  ```

---

## 7. Aiogram Control UI, Keyboards & Download Sub-menu Tests

* **File:** [`tests/test_bot_ui.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_bot_ui.py)
* **Command:**
  ```bash
  pytest tests/test_bot_ui.py -v
  ```
* **Purpose:**
  Verifies Aiogram 3.x Single Message UI dynamic inline keyboard generation (`get_main_menu` (1, 1, 1, 2, 1) layout toggle states for Start/Stop Auto-Reply, Start/Stop Extraction, Auto-Join Groups `menu_auto_join`, and Sessions Manager `menu_session_mgr`), Sessions Manager sub-menu (`get_session_mgr_menu` for Switch Active, Add New, Rename, Delete, Back), granular extraction target sub-menu (`get_extraction_target_menu`), granular download FSM sub-menus (`get_download_menu`, `get_download_dates_keyboard`, `get_download_files_keyboard`), 10-item-per-page file list UI pagination with interactive `[ ⬅️ Prev ]` and `[ Next ➡️ ]` navigation buttons (`dl_page_{category}_{date}_{page}`), dynamic `edit_reply_markup` refresh upon task toggles, cancellation via `get_cancel_keyboard` and `cancel_fsm`, safe handling of expired callback queries (`TelegramBadRequest`) via `safe_callback_answer`, explicit active session logical validation with center-screen modal pop-up alerts (`show_alert=True`) before starting workers, extraction, or download browsing, multi-tenant session isolation ensuring Downloads UI only displays and delivers files belonging to the active session (`data/links/{active_session}/...`), strict concurrency safety locks (`is_userbot_running`) blocking simultaneous Joiner or Extractor execution on the same account, non-blocking asynchronous system statistics dashboard (`menu_system_stats`) displaying link counts isolated to the active session, back navigation (`get_back_keyboard`, `menu_back`), session checkmark indicators (`✅`), session rename FSM flow (`SessionState.waiting_for_new_session_name`), session deletion with automatic background worker termination, Push-Down UX for link file downloads (delivering document, deleting displaced menu, and resending fresh menu at chat bottom), immediate user message deletion (`message.delete()`) during FSM text input, in-place editing of prompt messages, and centralized Main Menu dispatching via `send_main_menu` with dynamic session resolution, worker status inquiries, and exception safety.
* **Expected Output:**
  ```text
  tests/test_bot_ui.py::test_get_main_menu_all_idle PASSED                                    [  1%]
  tests/test_bot_ui.py::test_get_main_menu_userbot_running PASSED                            [  3%]
  tests/test_bot_ui.py::test_get_main_menu_extractor_running PASSED                          [  4%]
  tests/test_bot_ui.py::test_get_main_menu_both_running PASSED                               [  6%]
  tests/test_bot_ui.py::test_get_extraction_target_menu_structure PASSED                      [  7%]
  tests/test_bot_ui.py::test_get_download_menu_structure PASSED                               [  9%]
  tests/test_bot_ui.py::test_get_download_dates_keyboard_structure PASSED                     [ 10%]
  tests/test_bot_ui.py::test_get_download_files_keyboard_structure PASSED                     [ 12%]
  tests/test_bot_ui.py::test_get_download_files_keyboard_pagination PASSED                    [ 14%]
  tests/test_bot_ui.py::test_get_back_keyboard PASSED                                         [ 15%]
  tests/test_bot_ui.py::test_get_cancel_keyboard PASSED                                       [ 17%]
  tests/test_bot_ui.py::test_get_sessions_keyboard_with_active_indicator PASSED              [ 18%]
  tests/test_bot_ui.py::test_get_sessions_keyboard_empty_list PASSED                          [ 20%]
  tests/test_bot_ui.py::test_get_session_mgr_menu_structure PASSED                            [ 21%]
  tests/test_bot_ui.py::test_get_rename_sessions_keyboard_structure PASSED                   [ 23%]
  tests/test_bot_ui.py::test_get_delete_sessions_keyboard_structure PASSED                   [ 25%]
  tests/test_bot_ui.py::test_safe_callback_answer_handles_telegram_bad_request PASSED         [ 26%]
  tests/test_bot_ui.py::test_start_command_handler PASSED                                     [ 28%]
  tests/test_bot_ui.py::test_start_reply_callback_handler_triggers_process_manager PASSED     [ 29%]
  tests/test_bot_ui.py::test_start_reply_callback_handler_no_session_validation PASSED        [ 31%]
  tests/test_bot_ui.py::test_start_reply_callback_handler_already_running_concurrency PASSED  [ 32%]
  tests/test_bot_ui.py::test_stop_reply_callback_handler_triggers_process_manager PASSED      [ 34%]
  tests/test_bot_ui.py::test_stop_reply_callback_handler_already_stopped PASSED               [ 35%]
  tests/test_bot_ui.py::test_extract_links_callback_handler_shows_target_menu PASSED          [ 37%]
  tests/test_bot_ui.py::test_extract_links_callback_handler_no_session_validation PASSED      [ 39%]
  tests/test_bot_ui.py::test_extract_links_callback_handler_userbot_running_blocks_extraction PASSED [ 40%]
  tests/test_bot_ui.py::test_extract_target_callback_handler_transitions_to_date_prompt PASSED [ 42%]
  tests/test_bot_ui.py::test_extract_target_callback_handler_no_session_validation PASSED    [ 43%]
  tests/test_bot_ui.py::test_stop_extraction_callback_handler PASSED                          [ 45%]
  tests/test_bot_ui.py::test_stop_extraction_callback_handler_already_stopped PASSED          [ 46%]
  tests/test_bot_ui.py::test_cancel_fsm_callback_handler PASSED                               [ 48%]
  tests/test_bot_ui.py::test_process_date_range_extraction_handler_invalid_format PASSED      [ 50%]
  tests/test_bot_ui.py::test_process_date_range_extraction_handler_userbot_running_blocks_extraction PASSED [ 51%]
  tests/test_bot_ui.py::test_process_date_range_extraction_handler_success PASSED             [ 53%]
  tests/test_bot_ui.py::test_system_stats_callback_handler PASSED                             [ 54%]
  tests/test_bot_ui.py::test_open_downloads_menu_callback_handler PASSED                      [ 56%]
  tests/test_bot_ui.py::test_download_category_callback_handler_empty_soft_alert PASSED        [ 57%]
  tests/test_bot_ui.py::test_download_category_callback_handler_renders_dates PASSED         [ 59%]
  tests/test_bot_ui.py::test_download_date_callback_handler_renders_files PASSED             [ 60%]
  tests/test_bot_ui.py::test_download_back_to_dates_callback_handler PASSED                  [ 62%]
  tests/test_bot_ui.py::test_download_file_callback_handler_delivers_single_file PASSED      [ 64%]
  tests/test_bot_ui.py::test_switch_session_callback_handler PASSED                           [ 65%]
  tests/test_bot_ui.py::test_select_session_callback_handler PASSED                           [ 67%]
  tests/test_bot_ui.py::test_back_to_main_menu_callback_handler PASSED                        [ 68%]
  tests/test_bot_ui.py::test_session_mgr_callback_handler PASSED                             [ 70%]
  tests/test_bot_ui.py::test_rename_session_list_callback_handler_empty PASSED                [ 71%]
  tests/test_bot_ui.py::test_rename_session_list_callback_handler_has_sessions PASSED         [ 73%]
  tests/test_bot_ui.py::test_rename_sess_select_callback_handler PASSED                       [ 75%]
  tests/test_bot_ui.py::test_process_new_session_name_handler_invalid_format PASSED          [ 76%]
  tests/test_bot_ui.py::test_process_new_session_name_handler_duplicate PASSED               [ 78%]
  tests/test_bot_ui.py::test_process_new_session_name_handler_success PASSED                 [ 79%]
  tests/test_bot_ui.py::test_delete_session_list_callback_handler_empty PASSED                [ 81%]
  tests/test_bot_ui.py::test_delete_session_list_callback_handler_has_sessions PASSED         [ 82%]
  tests/test_bot_ui.py::test_del_sess_select_callback_handler_success PASSED                 [ 84%]
  tests/test_bot_ui.py::test_system_stats_callback_handler_active_session PASSED              [ 85%]
  tests/test_bot_ui.py::test_download_category_callback_handler_no_active_session PASSED     [ 87%]
  tests/test_bot_ui.py::test_download_category_callback_handler_success PASSED               [ 89%]
  tests/test_download_date_callback_handler_success PASSED                   [ 90%]
  tests/test_bot_ui.py::test_download_page_callback_handler_success PASSED                   [ 92%]
  tests/test_bot_ui.py::test_download_file_callback_handler_sends_isolated_file PASSED       [ 93%]
  tests/test_bot_ui.py::test_send_main_menu_dispatches_with_resolved_session PASSED          [ 95%]
  tests/test_bot_ui.py::test_send_main_menu_explicit_session_overrides_lookup PASSED          [ 96%]
  tests/test_bot_ui.py::test_send_main_menu_handles_exception_gracefully PASSED              [ 98%]
  tests/test_bot_ui.py::test_send_main_menu_invalid_bot_or_chat_id PASSED                    [100%]
  ============================== 64 passed in 0.38s ==============================
  ```

---

## 8. Background Process Manager & Non-Blocking Tasks Tests

* **File:** [`tests/test_process_manager.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_process_manager.py)
* **Command:**
  ```bash
  pytest tests/test_process_manager.py -v
  ```
* **Purpose:**
  Verifies non-blocking task creation via `asyncio.create_task` for userbots, link extraction workers, and auto-joiners, active task registries (`active_tasks`, `active_extractions`, `active_joiners`), dynamic detection of connected clients (`active_userbot_clients`), duplicate task prevention, graceful cancellation with `stop_userbot_client` before task `.cancel()`, `stop_joiner_task` cancellation, and alphabetical listing of running userbot sessions and extractions.
* **Expected Output:**
  ```text
  tests/test_process_manager.py::test_is_userbot_running_detects_connected_client PASSED     [  8%]
  tests/test_process_manager.py::test_start_userbot_task_creates_asyncio_task PASSED        [ 16%]
  tests/test_process_manager.py::test_start_userbot_task_already_running_rejected PASSED     [ 25%]
  tests/test_process_manager.py::test_stop_userbot_task_cancels_and_removes PASSED          [ 33%]
  tests/test_process_manager.py::test_stop_userbot_task_non_existent PASSED                 [ 41%]
  tests/test_process_manager.py::test_get_all_active_sessions_listing PASSED                [ 50%]
  tests/test_process_manager.py::test_start_extraction_task_creates_asyncio_task PASSED     [ 58%]
  tests/test_process_manager.py::test_start_extraction_task_already_running_rejected PASSED [ 66%]
  tests/test_process_manager.py::test_stop_extraction_task_cancels_and_removes PASSED       [ 75%]
  tests/test_process_manager.py::test_stop_extraction_task_non_existent PASSED              [ 83%]
  tests/test_process_manager.py::test_is_joiner_running_and_stop_joiner_task PASSED         [ 91%]
  tests/test_process_manager.py::test_stop_joiner_task_non_existent PASSED                  [100%]

  ============================== 12 passed in 0.08s ==============================
  ```

---

## 9. System Entry Point, Dispatcher & CLI Tools Tests

* **File:** [`tests/test_main.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_main.py)
* **Command:**
  ```bash
  pytest tests/test_main.py -v
  ```
* **Purpose:**
  Verifies the main application dispatcher configuration in `main.py`, registration of the UI and Login routers, initialization of the Aiogram polling lifecycle alongside the background scheduler, and testing of `tools/create_session.py` session name sanitization rules and interactive Pyrogram client authorization context flow.
* **Expected Output:**
  ```text
  tests/test_main.py::test_create_dispatcher_includes_ui_and_login_routers PASSED [ 20%]
  tests/test_main.py::test_create_bot_custom_token PASSED                         [ 40%]
  tests/test_main.py::test_main_polling_loop_invocation PASSED                    [ 60%]
  tests/test_main.py::test_sanitize_session_name_rules PASSED                     [ 80%]
  tests/test_main.py::test_create_new_session_flow PASSED                         [100%]

  ============================== 5 passed in 0.05s ==============================
  ```

---

## 10. Historical Chat Link Extractor Tests

* **File:** [`tests/test_extractor.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_extractor.py)
* **Command:**
  ```bash
  pytest tests/test_extractor.py -v
  ```
* **Purpose:**
  Verifies asynchronous global group scanning across all user dialogs, exclusion of private chats, exact date bounds (`start_date`, `end_date`), dual extraction and segregation of standard Telegram group links vs folder (`addlist`) links into separate category directories (`telegram_groups` vs `telegram_folders`), multi-tenant session isolation ensuring all extracted files are saved with run timestamp isolation (`part_{run_timestamp}.txt`), granular target filtering (`target_type="whatsapp"`, `"tg_groups"`, `"tg_folders"`, `"all"`), live progress message updates via Aiogram, targeted automated cloud archiving via `bot.send_document()` to `ARCHIVE_CHANNEL_ID` that **only uploads files generated in the active run** (preventing duplicate uploads of earlier files from the same date), dynamic document renaming with Aiogram's `FSInputFile` using the exact `{session_name}_{category}_{date}_{time}.txt` format, categorized persistence for Telegram, folder, and WhatsApp formats, graceful error recovery on Telegram access restrictions (`ChatAdminRequired`), and guaranteed **UI Auto-Refresh** on natural completion, manual cancellation (`asyncio.CancelledError`), or fatal errors resetting `ProcessManager.active_extractions` and dispatching a fresh Main Menu dashboard.
* **Expected Output:**
  ```text
  tests/test_extractor.py::test_run_global_extraction_task_filters_groups_and_dates PASSED [ 10%]
  tests/test_extractor.py::test_run_global_extraction_task_target_filtering PASSED         [ 20%]
  tests/test_extractor.py::test_run_extraction_task_catches_group_level_errors PASSED      [ 30%]
  tests/test_extractor.py::test_extract_and_segregate_telegram_links PASSED                [ 40%]
  tests/test_extractor.py::test_extract_and_segregate_telegram_links_empty_or_none PASSED  [ 50%]
  tests/test_extractor.py::test_run_extraction_task_mixed_links_segregated_saving PASSED   [ 60%]
  tests/test_extractor.py::test_run_extraction_task_cancelled_refreshes_ui PASSED          [ 70%]
  tests/test_extractor.py::test_run_extraction_task_fatal_error_refreshes_ui PASSED        [ 80%]
  tests/test_extractor.py::test_run_extraction_task_archives_only_generated_files_with_custom_name PASSED [ 90%]
  tests/test_extractor.py::test_run_extraction_task_no_archive_when_no_files_generated PASSED [100%]

  ============================== 10 passed in 0.12s ==============================
  ```

---

## 11. Background Scheduler, Midnight Reset & Hourly Feedback Tests

* **File:** [`tests/test_scheduler.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_scheduler.py)
* **Command:**
  ```bash
  pytest tests/test_scheduler.py -v
  ```
* **Purpose:**
  Verifies APScheduler background initialization, registration of the 00:00 UTC midnight daily DM quota reset CronTrigger, registration of the hourly feedback report CronTrigger (minute=0), verifies execution of `send_hourly_report` bounded by active userbot process states with metric compilation and resets, and verifies silent omission when userbots are inactive.
* **Expected Output:**
  ```text
  tests/test_scheduler.py::test_reset_daily_limits_clears_userbot_tracking PASSED          [ 25%]
  tests/test_scheduler.py::test_send_hourly_report_active_userbot PASSED                   [ 50%]
  tests/test_scheduler.py::test_send_hourly_report_idle_userbot PASSED                     [ 75%]
  tests/test_scheduler.py::test_start_scheduler_registers_both_cron_jobs PASSED           [100%]

  ============================== 4 passed in 0.05s ==============================
  ```

---

## 12. In-Bot Session Creation (Login FSM & 2FA) Tests

* **File:** [`tests/test_login_handlers.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_login_handlers.py)
* **Command:**
  ```bash
  pytest tests/test_login_handlers.py -v
  ```
* **Purpose:**
  Verifies the complete lifecycle and state transitions of the In-Bot Session Creation (Login FSM) module, including:
  - MTProto Client lifecycle management and guaranteed socket disconnection upon completion, failure, or cancellation (`cleanup_user_login_client`).
  - Session name validation enforcing character constraints (alphanumeric, underscores, hyphens) and rejecting duplicate session names.
  - Normal login flow: international phone number parsing, cleaning, OTP code dispatch via `client.send_code()`, direct sign-in verification via `client.sign_in()`, and automatic active session registration.
  - Two-Step Verification (2FA) login flow: detection of `SessionPasswordNeeded`, transition to `LoginState.waiting_for_password`, cloud password verification via `client.check_password()`, and active session assignment.
  - Robust exception handling for invalid/expired OTP codes (`PhoneCodeInvalid`, `PhoneCodeExpired`), invalid 2FA passwords (`PasswordHashInvalid`), unoccupied/banned numbers (`PhoneNumberUnoccupied`, `PhoneNumberBanned`, `PhoneNumberInvalid`), rate limits (`FloodWait`), and generic MTProto RPC errors (`RPCError`).
  - Single Message UI paradigm compliance: automatic deletion of sensitive user inputs (phone numbers, OTP codes, 2FA passwords) and dynamic editing of prompt messages.
  - Safe FSM workflow cancellation via `cancel_fsm` callback with immediate MTProto client cleanup and return to the main dashboard.
* **Expected Output:**
  ```text
  tests/test_login_handlers.py::test_cleanup_user_login_client_connected PASSED              [  5%]
  tests/test_login_handlers.py::test_cleanup_user_login_client_disconnected PASSED           [ 10%]
  tests/test_login_handlers.py::test_cleanup_user_login_client_handles_exception PASSED      [ 15%]
  tests/test_login_handlers.py::test_start_add_session_handler PASSED                         [ 21%]
  tests/test_login_handlers.py::test_process_session_name_valid PASSED                        [ 26%]
  tests/test_login_handlers.py::test_process_session_name_invalid_characters PASSED         [ 31%]
  tests/test_login_handlers.py::test_process_session_name_duplicate_rejected PASSED          [ 36%]
  tests/test_login_handlers.py::test_process_phone_number_success PASSED                     [ 42%]
  tests/test_login_handlers.py::test_process_phone_number_invalid_format PASSED              [ 47%]
  tests/test_login_handlers.py::test_process_phone_number_flood_wait_handled PASSED          [ 52%]
  tests/test_login_handlers.py::test_process_phone_number_unoccupied_phone PASSED          [ 57%]
  tests/test_login_handlers.py::test_process_phone_number_phone_number_invalid_error PASSED   [ 63%]
  tests/test_login_handlers.py::test_process_otp_code_invalid_format PASSED                   [ 68%]
  tests/test_login_handlers.py::test_process_otp_code_success_no_2fa PASSED                  [ 73%]
  tests/test_login_handlers.py::test_process_otp_code_requires_2fa PASSED                     [ 78%]
  tests/test_login_handlers.py::test_process_otp_code_invalid_code_error PASSED             [ 84%]
  tests/test_login_handlers.py::test_process_2fa_password_success PASSED                     [ 89%]
  tests/test_login_handlers.py::test_process_2fa_password_invalid PASSED                     [ 94%]
  tests/test_login_handlers.py::test_cancel_fsm_cleans_up_login_client PASSED                [100%]

  ============================== 19 passed in 0.14s ==============================
  ```

---

## 13. MTProto Userbot Session Manager (Delete, Rename & StringSession) Tests

* **File:** [`tests/test_session_manager.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_session_manager.py)
* **Command:**
  ```bash
  pytest tests/test_session_manager.py -v
  ```
* **Purpose:**
  Verifies backend Pyrogram session management lifecycle, environment-based StringSession loading, and atomic file operations in `userbot/session_manager.py`:
  - `get_available_sessions()`: scans environment variables for `SESSION_*` keys, merges with filesystem `.session` files without duplicates, directory existence verification, file filtering (ignoring `.session-journal`), alphanumeric sorting, and `OSError` resilience.
  - Global active session tracking: `get_active_session()` and `set_active_session()`.
  - `get_session_string()` & `is_env_session()`: accurate detection and retrieval of environment variable StringSessions (`SESSION_{NAME}`).
  - `delete_session()`: atomic deletion of `.session` file and associated SQLite journal files, safe handling of environment-based sessions without raising filesystem errors, automatic reset of global `_active_session` to `None` if the active account is deleted, non-existent target handling, and `OSError` safety.
  - `rename_session()`: atomic renaming of `.session` and journal files, safe rejection of environment sessions which cannot be renamed on disk, automatic update of global `_active_session` to the new name, duplicate target prevention, empty/invalid name rejection, and `OSError` handling.
* **Expected Output:**
  ```text
  tests/test_session_manager.py::test_get_available_sessions_directory_not_found PASSED      [  5%]
  tests/test_session_manager.py::test_get_available_sessions_listing PASSED                  [ 11%]
  tests/test_session_manager.py::test_get_available_sessions_os_error PASSED                 [ 16%]
  tests/test_session_manager.py::test_get_and_set_active_session PASSED                     [ 22%]
  tests/test_session_manager.py::test_delete_session_success_non_active PASSED               [ 27%]
  tests/test_session_manager.py::test_delete_session_success_resets_active PASSED            [ 33%]
  tests/test_session_manager.py::test_delete_session_non_existent PASSED                    [ 38%]
  tests/test_session_manager.py::test_delete_session_empty_name PASSED                      [ 44%]
  tests/test_session_manager.py::test_delete_session_os_error PASSED                         [ 50%]
  tests/test_session_manager.py::test_rename_session_success_non_active PASSED               [ 55%]
  tests/test_session_manager.py::test_rename_session_success_updates_active PASSED            [ 61%]
  tests/test_session_manager.py::test_rename_session_non_existent PASSED                     [ 66%]
  tests/test_session_manager.py::test_rename_session_target_already_exists PASSED           [ 72%]
  tests/test_session_manager.py::test_rename_session_invalid_names PASSED                    [ 77%]
  tests/test_session_manager.py::test_rename_session_os_error PASSED                         [ 83%]
  tests/test_session_manager.py::test_get_available_sessions_merges_env_and_local PASSED    [ 84%]
  tests/test_session_manager.py::test_get_session_string_and_is_env_session PASSED          [ 89%]
  tests/test_session_manager.py::test_delete_and_rename_env_session_graceful PASSED         [ 94%]
  tests/test_session_manager.py::test_get_available_sessions_mocker_patch_dict_env PASSED   [100%]

  ============================== 19 passed in 0.12s ==============================
  ```

---

## 14. Auto-Joiner Core Engine Tests

* **File:** [`tests/test_joiner.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_joiner.py)
* **Command:**
  ```bash
  pytest tests/test_joiner.py -v
  ```
* **Purpose:**
  Verifies the core MTProto Auto-Joiner engine (`userbot/joiner.py`):
  - Link extraction and deduplication from categorized `.txt` part files (`extract_links_from_file`).
  - Target link sanitization (`sanitize_chat_target`): preserving private invite hashes (`+hash` or `joinchat/hash`) while stripping public URL prefixes and `@` symbols to raw usernames.
  - Safe joining via `client.join_chat(target_chat)` with enforced 7-second anti-spam spacing (`JOIN_ANTI_SPAM_SLEEP_SECONDS`).
  - Instant skipping on `UserAlreadyParticipant` exceptions without adding delay.
  - Join request handling on `InviteRequestSent`: incrementing `sent_request` metric, anti-spam spacing, and live UI reporting.
  - Rate limit resilience: catching `FloodWait`, updating the UI message, sleeping for `exc.value + 5` seconds, and retrying the exact same link before moving forward.
  - Verbose error logging: logging `logger.warning` for ALL join failures with the exact Telegram API error message.
  - Kill switch handling: catching `asyncio.CancelledError`, stopping client, appending `🛑 ABORTED BY ADMIN`, and updating UI.
  - Live progress reporting every 3 processed links and final summary reporting at completion.
  - Guaranteed **UI Auto-Refresh**: updating `ProcessManager.active_joiners` and immediately dispatching a fresh Main Menu dashboard upon natural completion, manual abort, empty target link files, or unexpected runtime exceptions.
  - Pyrogram MTProto client lifecycle management (`start()`, `stop()`).
* **Expected Output:**
  ```text
  tests/test_joiner.py::test_extract_links_from_file_valid PASSED                              [  5%]
  tests/test_joiner.py::test_extract_links_from_file_non_existent PASSED                       [ 11%]
  tests/test_joiner.py::test_sanitize_chat_target_private_invite_links PASSED                  [ 17%]
  tests/test_joiner.py::test_sanitize_chat_target_public_links_and_handles PASSED             [ 23%]
  tests/test_joiner.py::test_run_auto_join_task_empty_links PASSED                            [ 29%]
  tests/test_joiner.py::test_run_auto_join_task_successful_joins PASSED                       [ 35%]
  tests/test_joiner.py::test_run_auto_join_task_user_already_participant PASSED               [ 41%]
  tests/test_joiner.py::test_run_auto_join_task_flood_wait_retries_and_succeeds PASSED        [ 47%]
  tests/test_joiner.py::test_run_auto_join_task_expired_and_invalid_links PASSED               [ 52%]
  tests/test_joiner.py::test_run_auto_join_task_failure_logs_verbose_warning PASSED          [ 58%]
  tests/test_joiner.py::test_run_auto_join_task_unexpected_error_logs_warning PASSED          [ 64%]
  tests/test_joiner.py::test_run_auto_join_task_invite_request_sent PASSED                    [ 70%]
  tests/test_joiner.py::test_run_auto_join_task_admin_cancellation PASSED                     [ 76%]
  tests/test_joiner.py::test_run_auto_join_task_completion_refreshes_main_menu PASSED        [ 82%]
  tests/test_joiner.py::test_run_auto_join_task_cancellation_refreshes_main_menu PASSED      [ 88%]
  tests/test_joiner.py::test_run_auto_join_task_empty_links_refreshes_main_menu PASSED        [ 94%]
  tests/test_joiner.py::test_run_auto_join_task_error_refreshes_main_menu PASSED              [100%]

  ============================== 17 passed in 0.15s ==============================
  ```

---

## 15. Auto-Joiner UI & FSM Handlers Tests

* **File:** [`tests/test_joiner_handlers.py`](file:///c:/Users/Lenovo/Desktop/Telegram/tests/test_joiner_handlers.py)
* **Command:**
  ```bash
  pytest tests/test_joiner_handlers.py -v
  ```
* **Purpose:**
  Verifies the multi-step Aiogram 3.x FSM Auto-Joiner workflow (`bot_ui/joiner_handlers.py`):
  - Step 1: Active session validation with modal alert (`show_alert=True`) and discovery of valid date folders strictly within the active session directory `data/links/{active_session}/` (`get_available_group_dates`).
  - Step 2: Date selection (`jdate_{date}`), FSM state transition to `JoinerState.selecting_file`, and retrieval of available `.txt` part files from `data/links/{active_session}/{date}/telegram_groups/` (`get_group_files_for_date`).
  - Step 3: Concurrency safety check ensuring Auto-Joiner cannot start if Auto-Reply userbot is currently active on the same session (`is_userbot_running`), returning modal alert (`show_alert=True`).
  - Step 3 execution: Granular file selection (`jfile_{filename}`), FSM state clearing, in-place prompt message editing with `get_joiner_progress_keyboard`, task registration in `active_joiners`, and launching of the background `run_auto_join_task` for the chosen file strictly verified under `data/links/{active_session}/...`.
  - Kill Switch UX: `[ ⏹️ Stop Auto-Joiner ]` button (`stop_joiner_{session_name}`) triggering `stop_joiner_callback_handler` and `stop_joiner_task(session_name)`.
  - Exception handling for missing active sessions, empty storage directories, and deleted files with modal pop-up alerts.
* **Expected Output:**
  ```text
  tests/test_joiner_handlers.py::test_get_available_group_dates_scanning PASSED               [  8%]
  tests/test_joiner_handlers.py::test_get_group_files_for_date_scanning PASSED               [ 15%]
  tests/test_joiner_handlers.py::test_start_auto_join_handler_no_active_session PASSED       [ 23%]
  tests/test_joiner_handlers.py::test_start_auto_join_handler_no_dates_found PASSED         [ 31%]
  tests/test_joiner_handlers.py::test_start_auto_join_handler_success_renders_dates PASSED   [ 38%]
  tests/test_joiner_handlers.py::test_start_auto_join_handler_userbot_running_blocks_joiner PASSED [ 46%]
  tests/test_joiner_handlers.py::test_select_joiner_date_handler_no_files PASSED             [ 54%]
  tests/test_joiner_handlers.py::test_select_joiner_date_handler_success_renders_files PASSED [ 62%]
  tests/test_joiner_handlers.py::test_select_joiner_file_handler_file_not_found PASSED       [ 69%]
  tests/test_joiner_handlers.py::test_select_joiner_file_handler_success_spawns_task PASSED  [ 77%]
  tests/test_joiner_handlers.py::test_select_joiner_file_handler_userbot_running_blocks_joiner PASSED [ 85%]
  tests/test_joiner_handlers.py::test_stop_joiner_callback_handler_triggers_stop_joiner_task PASSED [ 92%]
  tests/test_joiner_handlers.py::test_get_joiner_progress_keyboard_structure PASSED          [ 100%]

  ============================== 13 passed in 0.12s ==============================
  ```

---

## 16. System-Wide UI Auto-Refresh Verification Suite

* **Components:** [`bot_ui/handlers.py`](file:///c:/Users/Lenovo/Desktop/Telegram/bot_ui/handlers.py), [`userbot/extractor.py`](file:///c:/Users/Lenovo/Desktop/Telegram/userbot/extractor.py), [`userbot/joiner.py`](file:///c:/Users/Lenovo/Desktop/Telegram/userbot/joiner.py), [`core/process_manager.py`](file:///c:/Users/Lenovo/Desktop/Telegram/core/process_manager.py)
* **Command:**
  ```bash
  pytest tests/test_bot_ui.py tests/test_extractor.py tests/test_joiner.py -k "refreshes or send_main_menu" -v
  ```
* **Purpose:**
  Verifies the unified system-wide UX standard across all background processes:
  - Centralized Main Menu Dispatcher (`send_main_menu`): dynamically inspects active user state, checks live task statuses (`is_userbot_running`, `is_extraction_running`), formats HTML dashboard guidance, and dispatches fresh menu with active toggle buttons.
  - Link Extractor Auto-Refresh: ensures natural completion, manual cancellation (`asyncio.CancelledError`), and fatal error recovery explicitly clean `active_extractions` and dispatch fresh Main Menu.
  - Auto-Joiner Auto-Refresh: ensures natural completion, manual abort, empty targets abort, and fatal exceptions explicitly clean `active_joiners` and dispatch fresh Main Menu.
  - Concurrency synchronization: verifies `ProcessManager` status inquiry functions immediately reflect `is_running = False` upon task termination.
* **Expected Output:**
  ```text
  tests/test_bot_ui.py::test_send_main_menu_dispatches_with_resolved_session PASSED          [ 12%]
  tests/test_bot_ui.py::test_send_main_menu_explicit_session_overrides_lookup PASSED          [ 25%]
  tests/test_bot_ui.py::test_send_main_menu_handles_exception_gracefully PASSED              [ 37%]
  tests/test_bot_ui.py::test_send_main_menu_invalid_bot_or_chat_id PASSED                    [ 50%]
  tests/test_extractor.py::test_run_extraction_task_cancelled_refreshes_ui PASSED          [ 62%]
  tests/test_extractor.py::test_run_extraction_task_fatal_error_refreshes_ui PASSED        [ 75%]
  tests/test_joiner.py::test_run_auto_join_task_completion_refreshes_main_menu PASSED        [ 81%]
  tests/test_joiner.py::test_run_auto_join_task_cancellation_refreshes_main_menu PASSED      [ 87%]
  tests/test_joiner.py::test_run_auto_join_task_empty_links_refreshes_main_menu PASSED        [ 93%]
  tests/test_joiner.py::test_run_auto_join_task_error_refreshes_main_menu PASSED              [100%]

  ============================== 10 passed in 0.12s ==============================
  ```

---

## Standard Operating Procedure (SOP) for Developers & Agents

1. Every newly created module must have a corresponding test suite located under `tests/test_<module_name>.py`.
2. Every test must be mocked to prevent real network or MTProto/Telegram API traffic during CI/testing.
3. Every new test module must be immediately documented in this guide with its CLI execution command, purpose, and expected terminal output.


