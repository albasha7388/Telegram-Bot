"""
Unit tests for core/file_manager.py categorized storage, 100-link pagination, and optimized line counting.
"""

from datetime import datetime
from pathlib import Path
import pytest
from core import file_manager


def test_save_link_empty_validation() -> None:
    """Test that saving empty or whitespace links raises ValueError."""
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        file_manager.save_link("")

    with pytest.raises(ValueError, match="empty or whitespace-only"):
        file_manager.save_link("   \n\t  ")


def test_save_link_nested_directory_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test saving links generates data/links/<session_name>/YYYY-MM-DD/<category>/part_1.txt structure."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # 1. WhatsApp Link with custom session
    wa_path = file_manager.save_whatsapp_link("https://chat.whatsapp.com/Code123", session_name="session_alpha")
    assert str(Path(f"session_alpha/{date_str}/whatsapp/part_1.txt")) in wa_path
    wa_file = temp_links_dir / "session_alpha" / date_str / "whatsapp" / "part_1.txt"
    assert wa_file.exists()
    assert "https://chat.whatsapp.com/Code123" in wa_file.read_text(encoding="utf-8")

    # 2. Telegram Folder Link with default session
    folder_path = file_manager.save_folder_link("https://t.me/addlist/StudyFolder")
    assert str(Path(f"default/{date_str}/telegram_folders/part_1.txt")) in folder_path
    folder_file = temp_links_dir / "default" / date_str / "telegram_folders" / "part_1.txt"
    assert folder_file.exists()
    assert "https://t.me/addlist/StudyFolder" in folder_file.read_text(encoding="utf-8")

    # 3. Telegram Group Link with custom session
    group_path = file_manager.save_telegram_link("https://t.me/DevGroup", session_name="session_beta")
    assert str(Path(f"session_beta/{date_str}/telegram_groups/part_1.txt")) in group_path
    group_file = temp_links_dir / "session_beta" / date_str / "telegram_groups" / "part_1.txt"
    assert group_file.exists()
    assert "https://t.me/DevGroup" in group_file.read_text(encoding="utf-8")


def test_save_link_strict_100_pagination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test strict 100-link pagination: exactly 100 links per file, overflowing to part_2.txt and part_3.txt."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    date_str = datetime.now().strftime("%Y-%m-%d")
    wa_dir = temp_links_dir / "session_test" / date_str / "whatsapp"

    # Save exactly 100 links
    for i in range(1, 101):
        file_manager.save_link(f"https://chat.whatsapp.com/link_{i}", category="whatsapp", session_name="session_test")

    part1_file = wa_dir / "part_1.txt"
    assert part1_file.exists()
    part1_lines = [line.strip() for line in part1_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(part1_lines) == 100
    assert not (wa_dir / "part_2.txt").exists()

    # Save 101st link -> must trigger part_2.txt creation
    p2_path = file_manager.save_link("https://chat.whatsapp.com/link_101", category="whatsapp", session_name="session_test")
    assert "part_2.txt" in p2_path
    part2_file = wa_dir / "part_2.txt"
    assert part2_file.exists()
    part2_lines = [line.strip() for line in part2_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(part2_lines) == 1
    assert part2_lines[0] == "https://chat.whatsapp.com/link_101"

    # Fill part_2.txt to 100 lines (99 more links)
    for i in range(102, 201):
        file_manager.save_link(f"https://chat.whatsapp.com/link_{i}", category="whatsapp", session_name="session_test")

    part2_lines_full = [line.strip() for line in part2_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(part2_lines_full) == 100
    assert not (wa_dir / "part_3.txt").exists()

    # Save 201st link -> must trigger part_3.txt creation
    p3_path = file_manager.save_link("https://chat.whatsapp.com/link_201", category="whatsapp", session_name="session_test")
    assert "part_3.txt" in p3_path
    part3_file = wa_dir / "part_3.txt"
    assert part3_file.exists()
    part3_lines = [line.strip() for line in part3_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(part3_lines) == 1


def test_get_files_by_category_ordering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_files_by_category searches across all dates and orders files chronologically and by part."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    # Set up multi-date hierarchy in session_alpha
    d1_wa = temp_links_dir / "session_alpha" / "2026-08-01" / "whatsapp"
    d1_wa.mkdir(parents=True, exist_ok=True)
    (d1_wa / "part_1.txt").write_text("wa1\n", encoding="utf-8")
    (d1_wa / "part_2.txt").write_text("wa2\n", encoding="utf-8")

    d2_wa = temp_links_dir / "session_alpha" / "2026-08-02" / "whatsapp"
    d2_wa.mkdir(parents=True, exist_ok=True)
    (d2_wa / "part_1.txt").write_text("wa3\n", encoding="utf-8")

    d1_tg = temp_links_dir / "session_alpha" / "2026-08-01" / "telegram_groups"
    d1_tg.mkdir(parents=True, exist_ok=True)
    (d1_tg / "part_1.txt").write_text("tg1\n", encoding="utf-8")

    # Another session
    d_beta = temp_links_dir / "session_beta" / "2026-08-01" / "whatsapp"
    d_beta.mkdir(parents=True, exist_ok=True)
    (d_beta / "part_1.txt").write_text("wa_beta\n", encoding="utf-8")

    # Scoped to session_alpha
    wa_files_alpha = file_manager.get_files_by_category("whatsapp", session_name="session_alpha")
    assert len(wa_files_alpha) == 3
    assert wa_files_alpha[0] == d1_wa / "part_1.txt"
    assert wa_files_alpha[1] == d1_wa / "part_2.txt"
    assert wa_files_alpha[2] == d2_wa / "part_1.txt"

    # Scoped to session_beta
    wa_files_beta = file_manager.get_files_by_category("whatsapp", session_name="session_beta")
    assert len(wa_files_beta) == 1
    assert wa_files_beta[0] == d_beta / "part_1.txt"

    tg_files = file_manager.get_files_by_category("telegram_groups", session_name="session_alpha")
    assert len(tg_files) == 1
    assert tg_files[0] == d1_tg / "part_1.txt"

    folder_files = file_manager.get_files_by_category("telegram_folders", session_name="session_alpha")
    assert folder_files == []


@pytest.mark.asyncio
async def test_get_all_link_files_and_total_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_all_link_files, granular get_total_links_count dict, and non-blocking async counting."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    # Non-existent directory returns empty list / all zeros dictionary
    assert file_manager.get_all_link_files(session_name="sess1") == []
    empty_stats = file_manager.get_total_links_count(session_name="sess1")
    assert empty_stats == {
        "whatsapp": 0,
        "telegram_groups": 0,
        "telegram_folders": 0,
        "total": 0,
    }
    assert await file_manager.get_total_links_count_async(session_name="sess1") == empty_stats

    # Populate structure with WhatsApp, Telegram groups, and Telegram folders for sess1
    d_wa = temp_links_dir / "sess1" / "2026-08-08" / "whatsapp"
    d_tg = temp_links_dir / "sess1" / "2026-08-08" / "telegram_groups"
    d_tf = temp_links_dir / "sess1" / "2026-08-08" / "telegram_folders"
    d_wa.mkdir(parents=True, exist_ok=True)
    d_tg.mkdir(parents=True, exist_ok=True)
    d_tf.mkdir(parents=True, exist_ok=True)

    (d_wa / "part_1.txt").write_text("wa1\nwa2\n\n", encoding="utf-8")
    (d_tg / "part_1.txt").write_text("tg1\ntg2\ntg3\n", encoding="utf-8")
    (d_tf / "part_1.txt").write_text("folder1\n", encoding="utf-8")

    all_files = file_manager.get_all_link_files(session_name="sess1")
    assert len(all_files) == 3

    # Fast sync granular counting
    stats = file_manager.get_total_links_count(session_name="sess1")
    assert isinstance(stats, dict)
    assert stats["whatsapp"] == 2
    assert stats["telegram_groups"] == 3
    assert stats["telegram_folders"] == 1
    assert stats["total"] == 6

    # Fast async non-blocking counting
    async_stats = await file_manager.get_total_links_count_async(session_name="sess1")
    assert async_stats == stats


def test_get_available_dates_for_category(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_available_dates_for_category returns sorted date folders containing category files."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    d1 = temp_links_dir / "sess_active" / "2026-08-10" / "whatsapp"
    d1.mkdir(parents=True, exist_ok=True)
    (d1 / "part_1.txt").write_text("wa1")

    d2 = temp_links_dir / "sess_active" / "2026-08-11" / "whatsapp"
    d2.mkdir(parents=True, exist_ok=True)
    (d2 / "part_1.txt").write_text("wa2")

    # Empty folder (no txt)
    d3 = temp_links_dir / "sess_active" / "2026-08-12" / "whatsapp"
    d3.mkdir(parents=True, exist_ok=True)

    # Another session
    d_other = temp_links_dir / "sess_other" / "2026-08-15" / "whatsapp"
    d_other.mkdir(parents=True, exist_ok=True)
    (d_other / "part_1.txt").write_text("wa_other")

    dates = file_manager.get_available_dates_for_category("whatsapp", session_name="sess_active")
    assert dates == ["2026-08-11", "2026-08-10"]


def test_get_files_for_category_and_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_files_for_category_and_date returns sorted part files for given date."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    cat_dir = temp_links_dir / "sess_active" / "2026-08-11" / "telegram_folders"
    cat_dir.mkdir(parents=True, exist_ok=True)
    (cat_dir / "part_2.txt").write_text("folder2")
    (cat_dir / "part_1.txt").write_text("folder1")
    (cat_dir / "notes.txt").write_text("notes")

    files = file_manager.get_files_for_category_and_date("telegram_folders", "2026-08-11", session_name="sess_active")
    assert files == ["part_1.txt", "part_2.txt", "notes.txt"]


def test_save_link_run_timestamp_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that save_link with different run_timestamps creates distinct files without appending to earlier runs."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    date_str = datetime.now().strftime("%Y-%m-%d")
    wa_dir = temp_links_dir / "session_test" / date_str / "whatsapp"

    run1_ts = "20260818_100000"
    run2_ts = "20260818_120000"

    p1 = file_manager.save_link("https://chat.whatsapp.com/run1_link", category="whatsapp", session_name="session_test", run_timestamp=run1_ts)
    p2 = file_manager.save_link("https://chat.whatsapp.com/run2_link", category="whatsapp", session_name="session_test", run_timestamp=run2_ts)

    assert f"part_{run1_ts}.txt" in p1
    assert f"part_{run2_ts}.txt" in p2
    assert p1 != p2

    f1 = wa_dir / f"part_{run1_ts}.txt"
    f2 = wa_dir / f"part_{run2_ts}.txt"

    assert f1.exists()
    assert f2.exists()
    assert f1.read_text(encoding="utf-8").strip() == "https://chat.whatsapp.com/run1_link"
    assert f2.read_text(encoding="utf-8").strip() == "https://chat.whatsapp.com/run2_link"


def test_save_link_run_timestamp_pagination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test pagination for save_link with run_timestamp rolls over to part_<timestamp>_2.txt after 100 links."""
    temp_links_dir = tmp_path / "links"
    monkeypatch.setattr(file_manager, "LINKS_DIR", temp_links_dir)

    date_str = datetime.now().strftime("%Y-%m-%d")
    wa_dir = temp_links_dir / "session_test" / date_str / "whatsapp"
    run_ts = "20260818_150000"

    for i in range(1, 101):
        file_manager.save_link(f"https://chat.whatsapp.com/link_{i}", category="whatsapp", session_name="session_test", run_timestamp=run_ts)

    p1_file = wa_dir / f"part_{run_ts}.txt"
    assert p1_file.exists()
    p1_lines = [line.strip() for line in p1_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(p1_lines) == 100

    # 101st link rolls over
    p2 = file_manager.save_link("https://chat.whatsapp.com/link_101", category="whatsapp", session_name="session_test", run_timestamp=run_ts)
    assert f"part_{run_ts}_2.txt" in p2
    p2_file = wa_dir / f"part_{run_ts}_2.txt"
    assert p2_file.exists()
    p2_lines = [line.strip() for line in p2_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(p2_lines) == 1
    assert p2_lines[0] == "https://chat.whatsapp.com/link_101"


