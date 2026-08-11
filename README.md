## 🤖 AI Model Instructions (Vibe Coding)
This repository contains **MyTelegramSystem**, a Python Telegram bot project, along with a technical reference set (see the index below) prepared specifically for it. When working on this project, apply only the concepts, patterns, or reference material that you actually need for the specific part of the project you're working on right now — don't force patterns, abstractions, or unrelated techniques onto code that doesn't need them.

---

# MyTelegramSystem - Hybrid Userbot & Control Panel

## 📖 Project Overview
This project is an advanced hybrid software system built with Python, designed to automate and professionally manage Telegram tasks. The system relies on integrating two different technologies to ensure efficiency and security:

1. **Backend Engine (Userbot):** Operates silently in the background using the (Pyrogram) library to control personal Telegram accounts, enabling reading group messages, searching, and data extraction without the limitations of standard bots.
2. **Control Interface (Control Bot):** An interactive official Telegram bot built with the (aiogram) library, providing a control panel with (Inline Keyboards) to manage the backend engine, send commands, and receive reports and files directly on your phone.

The project is designed using clean software engineering principles (SOLID Principles) and a Modular Architecture to ensure maintainability, scalability, and testability.

---

## 🚀 Core Features

### 1. Smart Auto-Reply & Monitoring
The backend engine continuously monitors (24/7) specific messages within groups or private chats. The system relies on keyword-matching algorithms for auto-replying. It also features "exclusion filters" that prevent the bot from replying if the message contains pre-defined negative words or phrases, ensuring the accuracy and contextual relevance of the replies.

### 2. Telegram Links Validation
The system searches targeted groups for Telegram invite links (starting with `t.me`). Once collected, it verifies their validity (whether the link is active and joinable or expired) via the official Telegram API, applying carefully calculated Time Sleeps to avoid server bans (FloodWait).

### 3. WhatsApp Links Validation
An independent system to search for WhatsApp group links (starting with `chat.whatsapp.com`) within Telegram messages. Since Telegram doesn't support validating cross-platform links, the system performs background Web Scraping using `requests` and `BeautifulSoup` to open the link's page and check for the presence of the "Join Chat" button to ensure the group's validity.

### 4. Chat Folders Extraction
A specialized function to recognize links for Shareable Chat Folders (starting with `t.me/addlist/`). This allows aggregating massive group repositories and categorizing them independently of individual links.

### 5. Smart File Pagination System
Instead of saving thousands of links in a single, hard-to-read file, the system creates automatically paginated text (`.txt`) files. When a file reaches the programmed maximum limit (e.g., 100 links), the system closes it and starts a new one (e.g., `links_part1.txt` then `links_part2.txt`), protecting data from corruption and making it easier to manage.

### 6. Automated Task Scheduling
The system supports task scheduling to operate without human intervention. The bot can be configured to initiate search and validation tasks daily at a specific hour, automatically sending the results to the control interface upon completion.

### 7. Multi-Session Management
The system is not restricted to a single Telegram account. It allows you to run the backend engine on multiple accounts using different session (`.session`) files. You can select the target account for tasks directly through the control panel buttons.

### 8. Centralized Logging System
To track the system's performance 24/7, the bot logs all its activities (errors, successful validations, hosting downtime) in a `bot_logs.txt` file. This file can be requested daily from the control interface for review.

---

## 📂 Project Architecture

```text
MyTelegramSystem/
│
├── main.py                    # The main entry point to run the official bot and the backend engine together
├── requirements.txt           # List of libraries and dependencies to install
├── README.md                  # External project documentation and run instructions
│
├── config/                    # ⚙️ Settings Directory
│   ├── __init__.py
│   └── settings.py            # Contains static variables (API Keys, Tokens, Admin IDs)
│
├── bot_ui/                    # 📱 Control Interface Directory (Official Bot)
│   ├── __init__.py
│   ├── keyboards.py           # Strictly responsible for drawing and designing interactive buttons
│   └── handlers.py            # Responsible for receiving button clicks and executing commands
│
├── userbot/                   # 🤖 Backend Engine Directory (Personal Accounts)
│   ├── __init__.py
│   ├── listener.py            # Responsible for monitoring groups and reading new messages
│   ├── auto_reply.py          # Contains the keyword matching and auto-reply algorithm
│   └── session_manager.py     # Responsible for managing and switching between multiple session accounts
│
├── validators/                # 🔍 Data Validation and Extraction Directory
│   ├── __init__.py
│   ├── telegram_validator.py  # Extracts and validates regular group links (t.me)
│   ├── whatsapp_validator.py  # Extracts and validates WhatsApp links via (Scraping)
│   └── folder_validator.py    # Extracts and categorizes folder links (t.me/addlist/)
│
├── core/                      # 🛠️ Shared Core Functions Directory (Services)
│   ├── __init__.py
│   ├── file_manager.py        # Creates TXT files, paginates links, and manages storage
│   ├── scheduler.py           # Schedules tasks to run at specific times daily
│   └── logger_setup.py        # Configures the centralized Logging system
│
├── tests/                     # 🧪 Comprehensive Tests Directory (Unit Tests)
│   ├── __init__.py
│   ├── test_validators.py     # Tests link extraction and validation functions isolated from the network
│   ├── test_file_manager.py   # Tests text file creation and pagination functions
│   └── test_userbot.py        # Tests keyword matching and filtering algorithms
│
├── data/                      # 📂 Data and Outputs Storage Directory (Programmatically Created)
│   ├── keywords.json          # Mini-database for keywords, replies, and exclusions
│   ├── bot_logs.txt           # Daily logs file (automatically generated)
│   └── links/                 # Sub-directory to store links files (links_part1.txt, etc.)
│
└── sessions/                  # 🔐 Encrypted login sessions storage directory (.session)
```

---

## 📚 Reference Files Index
Each file below covers one independent topic. Apply only what's actually needed for the stage of the project being worked on.

| File | Topic |
|---|---|
| `01-solid-srp-single-responsibility.md` | Single Responsibility Principle (SRP) |
| `02-solid-ocp-open-closed.md` | Open/Closed Principle (OCP) |
| `03-solid-lsp-liskov-substitution.md` | Liskov Substitution Principle (LSP) |
| `04-solid-isp-interface-segregation.md` | Interface Segregation Principle (ISP) |
| `05-solid-dip-dependency-inversion.md` | Dependency Inversion Principle (DIP) |
| `06-advanced-oop-mixins-metaclasses.md` | Advanced OOP: Mixins, Metaclasses, Type Checking, Duck Typing |
| `07-context-managers.md` | Context Managers (`with`, `contextlib`, nested managers) |
| `08-testing-unittest-pytest.md` | Testing: unittest, pytest, TDD, and Mocking |
| `09-logging.md` | Logging in Python |
| `10-refactoring-code-review.md` | Refactoring, Code Review, and the Application Development Life Cycle |
| `11-documentation-docstrings-typehints.md` | Documenting code: Docstrings, Type Hints, and README |
| `12-regex.md` | Regular Expressions |
| `13-threading.md` | Threading, GIL, Locks, Thread Pooling |
| `14-multiprocessing.md` | Multiprocessing, IPC, Synchronisation, Process Pooling |
| `15-asyncio.md` | Asyncio: Coroutines, Event Loop, Task Scheduling |

*(All reference files have been cleaned of Table of Contents/Quiz/Homework sections and adapted strictly for this Telegram bot project's context.)*
