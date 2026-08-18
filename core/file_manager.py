"""
Categorized link storage and file management system with strict pagination.

Handles safe file I/O using context managers and sequential thread locking,
segregates links into structured date-stamped category directories:
`data/links/YYYY-MM-DD/<category_name>/part_X.txt` (whatsapp, telegram_groups, telegram_folders),
enforces strict 100-link pagination per part file, and provides granular category counting.
"""

import asyncio
from datetime import datetime
from pathlib import Path
import re
import threading
from typing import Final, Optional

from config.settings import LINKS_PER_FILE
from core.logger_setup import setup_logger

# Initialize module logger
logger = setup_logger(__name__)

# Base directory for categorized link storage
LINKS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "data" / "links"

# Valid category names mapping to standard directory names
CATEGORY_MAP: Final[dict[str, str]] = {
    "whatsapp": "whatsapp",
    "whatsapp_links": "whatsapp",
    "telegram_folder": "telegram_folders",
    "telegram_folders": "telegram_folders",
    "folder": "telegram_folders",
    "tg_folders": "telegram_folders",
    "telegram_group": "telegram_groups",
    "telegram_groups": "telegram_groups",
    "tg_groups": "telegram_groups",
    "telegram": "telegram_groups",
    "default": "telegram_groups",
}

VALID_CATEGORIES: Final[tuple[str, ...]] = (
    "whatsapp",
    "telegram_groups",
    "telegram_folders",
)

# Global lock for thread-safe sequential file writes and pagination calculation
_file_write_lock: Final[threading.Lock] = threading.Lock()


def _normalize_category(category: str) -> str:
    """Normalize input category string to standard category folder name.

    Args:
        category: Raw category identifier.

    Returns:
        str: Normalized category folder name ('whatsapp', 'telegram_groups', 'telegram_folders').
    """
    return CATEGORY_MAP.get(category.strip().lower(), "telegram_groups")


def _get_target_part_file(category_dir: Path, run_timestamp: Optional[str] = None) -> Path:
    """Determine the active paginated part file within a specific category directory.

    Inspects existing part files, identifies the highest index part file for the given
    run_timestamp (or legacy index if run_timestamp is None), and checks if it has reached
    the `LINKS_PER_FILE` limit (100 lines). If full, advances to a new paginated part file.

    Args:
        category_dir: Target directory path `data/links/<session_name>/YYYY-MM-DD/<category>/`.
        run_timestamp: Optional unique timestamp identifier for run isolation (e.g. '20260816_143000').

    Returns:
        Path: Target part file path ready for appending.
    """
    category_dir.mkdir(parents=True, exist_ok=True)

    if run_timestamp:
        # Matches part_<run_timestamp>.txt, part_<idx>_<run_timestamp>.txt, or part_<run_timestamp>_<idx>.txt
        part_pattern = re.compile(
            rf"^part_(?:(\d+)_)?{re.escape(run_timestamp)}(?:_(\d+))?\.txt$"
        )
    else:
        part_pattern = re.compile(r"^part_(\d+)\.txt$")

    existing_parts: list[tuple[int, Path]] = []

    for file_path in category_dir.iterdir():
        if file_path.is_file():
            match = part_pattern.match(file_path.name)
            if match:
                if run_timestamp:
                    idx_str = match.group(1) or match.group(2)
                    part_idx = int(idx_str) if idx_str else 1
                else:
                    part_idx = int(match.group(1))
                existing_parts.append((part_idx, file_path))

    if not existing_parts:
        if run_timestamp:
            return category_dir / f"part_{run_timestamp}.txt"
        return category_dir / "part_1.txt"

    existing_parts.sort(key=lambda item: item[0])
    latest_idx, latest_path = existing_parts[-1]

    # Count existing non-empty lines in the latest part file
    line_count = 0
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    line_count += 1
    except OSError as exc:
        logger.error("Failed reading '%s' for pagination calculation: %s", latest_path, exc)

    if line_count >= LINKS_PER_FILE:
        new_idx = latest_idx + 1
        if run_timestamp:
            new_part_path = category_dir / f"part_{run_timestamp}_{new_idx}.txt"
        else:
            new_part_path = category_dir / f"part_{new_idx}.txt"
        logger.debug("Part %d full (%d lines). Rolling over to %s", latest_idx, line_count, new_part_path.name)
        return new_part_path

    return latest_path


def save_link(
    link: str,
    category: str = "telegram_groups",
    session_name: str = "default",
    run_timestamp: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Append a link to its session-isolated categorized date-stamped paginated text file.

    Follows directory schema `data/links/<session_name>/YYYY-MM-DD/<category>/part_X.txt` (or
    `part_<run_timestamp>.txt` when isolated per run) and enforces strict 100-link pagination per file.

    Args:
        link: The URL or invite link string to persist.
        category: Link category ('whatsapp', 'telegram_groups', 'telegram_folders').
        session_name: Target session identifier for multi-tenant data isolation (default 'default').
        run_timestamp: Optional unique timestamp identifier for run isolation (e.g. '20260816_143000').
        run_id: Optional alias for run_timestamp.

    Returns:
        str: Absolute path to the destination part file.

    Raises:
        ValueError: If the link is empty or whitespace-only.
        OSError: If a filesystem error occurs during file write.
    """
    cleaned_link = link.strip()
    if not cleaned_link:
        logger.error("Attempted to save an empty or whitespace-only link.")
        raise ValueError("Cannot save an empty or whitespace-only link.")

    effective_run_id = run_timestamp or run_id
    normalized_cat = _normalize_category(category)
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    target_dir = LINKS_DIR / session_name / date_stamp / normalized_cat

    with _file_write_lock:
        try:
            target_file = _get_target_part_file(target_dir, run_timestamp=effective_run_id)
            with open(target_file, "a", encoding="utf-8") as file_handle:
                file_handle.write(f"{cleaned_link}\n")

            logger.info("Saved [%s] link '%s' for session '%s' to '%s'", normalized_cat, cleaned_link, session_name, target_file)
            return str(target_file.resolve())
        except OSError as exc:
            logger.error("Error writing link '%s' to storage: %s", cleaned_link, exc, exc_info=True)
            raise


def save_whatsapp_link(
    link: str,
    session_name: str = "default",
    run_timestamp: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Save an extracted WhatsApp group invite link into `<session_name>/<date>/whatsapp/part_X.txt`.

    Args:
        link: WhatsApp invite link URL.
        session_name: Target session identifier.
        run_timestamp: Optional unique timestamp identifier for run isolation.
        run_id: Optional alias for run_timestamp.

    Returns:
        str: Absolute file path.
    """
    return save_link(link, category="whatsapp", session_name=session_name, run_timestamp=run_timestamp, run_id=run_id)


def save_folder_link(
    link: str,
    session_name: str = "default",
    run_timestamp: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Save an extracted Telegram folder share link into `<session_name>/<date>/telegram_folders/part_X.txt`.

    Args:
        link: Telegram folder addlist link URL.
        session_name: Target session identifier.
        run_timestamp: Optional unique timestamp identifier for run isolation.
        run_id: Optional alias for run_timestamp.

    Returns:
        str: Absolute file path.
    """
    return save_link(link, category="telegram_folders", session_name=session_name, run_timestamp=run_timestamp, run_id=run_id)


def save_telegram_link(
    link: str,
    session_name: str = "default",
    run_timestamp: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Save an extracted Telegram group/channel link into `<session_name>/<date>/telegram_groups/part_X.txt`.

    Args:
        link: Telegram channel or group link URL.
        session_name: Target session identifier.
        run_timestamp: Optional unique timestamp identifier for run isolation.
        run_id: Optional alias for run_timestamp.

    Returns:
        str: Absolute file path.
    """
    return save_link(link, category="telegram_groups", session_name=session_name, run_timestamp=run_timestamp, run_id=run_id)


def get_files_by_category(category: str, session_name: Optional[str] = None) -> list[Path]:
    """Retrieve all paginated link text files for a specific category across all dates.

    Searches across date directories for the designated category subdirectory,
    optionally isolated to a specific session name, returning an ordered list of `part_X.txt` paths.

    Args:
        category: Target category ('whatsapp', 'telegram_groups', or 'telegram_folders').
        session_name: Optional session identifier to isolate the search.

    Returns:
        list[Path]: Ordered list of Path objects for all matching files.
    """
    if not LINKS_DIR.exists():
        logger.debug("Links directory '%s' does not exist yet.", LINKS_DIR)
        return []

    normalized_cat = _normalize_category(category)
    matching_files: list[Path] = []
    part_pattern = re.compile(r"^part_(\d+)\.txt$")
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    session_dirs: list[Path] = []
    if session_name:
        target_sess = LINKS_DIR / session_name
        if target_sess.exists() and target_sess.is_dir():
            session_dirs.append(target_sess)
    else:
        for item in sorted(LINKS_DIR.iterdir(), key=lambda d: d.name):
            if item.is_dir():
                if date_pattern.match(item.name):
                    # Legacy flat date directory
                    cat_dir = item / normalized_cat
                    if cat_dir.exists() and cat_dir.is_dir():
                        cat_files: list[tuple[int, Path]] = []
                        for file_path in cat_dir.iterdir():
                            if file_path.is_file() and file_path.suffix == ".txt":
                                match = part_pattern.match(file_path.name)
                                part_num = int(match.group(1)) if match else 0
                                cat_files.append((part_num, file_path))
                        cat_files.sort(key=lambda x: x[0])
                        matching_files.extend([x[1] for x in cat_files])
                else:
                    session_dirs.append(item)

    for sess_dir in session_dirs:
        date_dirs = [d for d in sess_dir.iterdir() if d.is_dir() and date_pattern.match(d.name)]
        date_dirs.sort(key=lambda d: d.name)
        for date_dir in date_dirs:
            cat_dir = date_dir / normalized_cat
            if cat_dir.exists() and cat_dir.is_dir():
                cat_files = []
                for file_path in cat_dir.iterdir():
                    if file_path.is_file() and file_path.suffix == ".txt":
                        match = part_pattern.match(file_path.name)
                        part_num = int(match.group(1)) if match else 0
                        cat_files.append((part_num, file_path))
                cat_files.sort(key=lambda x: x[0])
                matching_files.extend([x[1] for x in cat_files])

    logger.debug("Found %d file(s) for category '%s'", len(matching_files), normalized_cat)
    return matching_files


def get_available_dates_for_category(category: str, session_name: Optional[str] = None) -> list[str]:
    """Scan data/links/[{session_name}/] for date directories containing .txt files for a given category.

    Args:
        category: Raw or normalized category name ('whatsapp', 'telegram_groups', 'telegram_folders').
        session_name: Optional session identifier to isolate scanned date directories.

    Returns:
        list[str]: Sorted list of date folder names (e.g. ['2026-08-11', '2026-08-10']).
    """
    if not LINKS_DIR.exists():
        return []

    normalized_cat = _normalize_category(category)
    date_folders: set[str] = set()
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    if session_name:
        session_dir = LINKS_DIR / session_name
        if not session_dir.exists() or not session_dir.is_dir():
            return []
        for item in session_dir.iterdir():
            if item.is_dir() and date_pattern.match(item.name):
                cat_dir = item / normalized_cat
                if cat_dir.exists() and cat_dir.is_dir():
                    txt_files = [f for f in cat_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                    if txt_files:
                        date_folders.add(item.name)
    else:
        # Scan across all session subdirectories and legacy date directories
        for sess_or_date in LINKS_DIR.iterdir():
            if not sess_or_date.is_dir():
                continue
            if date_pattern.match(sess_or_date.name):
                cat_dir = sess_or_date / normalized_cat
                if cat_dir.exists() and cat_dir.is_dir():
                    txt_files = [f for f in cat_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                    if txt_files:
                        date_folders.add(sess_or_date.name)
            else:
                for date_item in sess_or_date.iterdir():
                    if date_item.is_dir() and date_pattern.match(date_item.name):
                        cat_dir = date_item / normalized_cat
                        if cat_dir.exists() and cat_dir.is_dir():
                            txt_files = [f for f in cat_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                            if txt_files:
                                date_folders.add(date_item.name)

    result = sorted(date_folders, reverse=True)
    return result


def get_files_for_category_and_date(
    category: str, date_str: str, session_name: Optional[str] = None
) -> list[str]:
    """Scan data/links/[{session_name}/]{date_str}/{category}/ for available .txt part files.

    Args:
        category: Raw or normalized category name.
        date_str: Date folder name (e.g. '2026-08-11').
        session_name: Optional session identifier for isolated lookup.

    Returns:
        list[str]: Sorted list of part filenames (e.g. ['part_1.txt', 'part_2.txt']).
    """
    normalized_cat = _normalize_category(category)
    if session_name:
        cat_dir = LINKS_DIR / session_name / date_str / normalized_cat
    else:
        cat_dir = LINKS_DIR / date_str / normalized_cat

    if not cat_dir.exists() or not cat_dir.is_dir():
        return []

    part_pattern = re.compile(r"^part_(\d+)\.txt$")
    files: list[tuple[int, str]] = []

    for item in cat_dir.iterdir():
        if item.is_file() and item.suffix == ".txt":
            match = part_pattern.match(item.name)
            part_num = int(match.group(1)) if match else 9999
            files.append((part_num, item.name))

    files.sort(key=lambda item: item[0])
    return [f[1] for f in files]


def get_all_link_files(session_name: Optional[str] = None) -> list[str]:
    """Retrieve an ordered list of all paginated link storage text files across all categories and dates.

    Args:
        session_name: Optional session identifier to isolate file paths.

    Returns:
        list[str]: Sorted list of absolute file paths to all matching link files.
    """
    if not LINKS_DIR.exists():
        logger.debug("Links directory '%s' does not exist yet.", LINKS_DIR)
        return []

    all_files: list[Path] = []
    for cat in VALID_CATEGORIES:
        all_files.extend(get_files_by_category(cat, session_name=session_name))

    all_files.sort(key=lambda p: str(p.resolve()))
    file_paths = [str(p.resolve()) for p in all_files]
    logger.debug("Found %d total categorized link file(s)", len(file_paths))
    return file_paths


def _count_lines_in_file(file_path_str: str) -> int:
    """Fast counting of non-empty lines in a file using a binary stream generator.

    Args:
        file_path_str: Target file path string.

    Returns:
        int: Number of non-empty lines in the file.
    """
    try:
        with open(file_path_str, "rb") as f:
            return sum(1 for line in f if line.strip())
    except OSError as exc:
        logger.error("Failed reading link file '%s' for stats count: %s", file_path_str, exc)
        return 0


def get_total_links_count(session_name: Optional[str] = None) -> dict[str, int]:
    """Calculate the total number of extracted links categorized by type and cumulative total.

    Args:
        session_name: Optional session identifier to isolate counts.

    Returns:
        dict[str, int]: Dictionary containing link counts per category and the cumulative total.
    """
    stats: dict[str, int] = {
        "whatsapp": 0,
        "telegram_groups": 0,
        "telegram_folders": 0,
        "total": 0,
    }

    if not LINKS_DIR.exists():
        logger.debug("Links directory '%s' does not exist yet.", LINKS_DIR)
        return stats

    for cat in VALID_CATEGORIES:
        cat_files = get_files_by_category(cat, session_name=session_name)
        cat_count = sum(_count_lines_in_file(str(p.resolve())) for p in cat_files)
        stats[cat] = cat_count

    stats["total"] = sum(stats[cat] for cat in VALID_CATEGORIES)
    logger.debug("Calculated granular link stats: %s", stats)
    return stats


async def get_total_links_count_async(session_name: Optional[str] = None) -> dict[str, int]:
    """Calculate granular link stats asynchronously in a background thread to prevent blocking.

    Args:
        session_name: Optional session identifier.

    Returns:
        dict[str, int]: Granular category counts and overall total.
    """
    return await asyncio.to_thread(get_total_links_count, session_name)
