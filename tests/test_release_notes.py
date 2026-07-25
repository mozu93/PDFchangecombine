"""
バージョンアップ時にリリースノートをポップアップ表示する判定ロジックのテスト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.release_notes import should_show_release_notes, find_release_notes_path


class TestShouldShowReleaseNotes:
    def test_first_install_no_popup(self):
        """last_seen_versionが空（初回インストール）なら表示しない"""
        assert should_show_release_notes("1.21.7", "") is False

    def test_same_version_no_popup(self):
        """前回と同じバージョンなら表示しない"""
        assert should_show_release_notes("1.21.7", "1.21.7") is False

    def test_version_changed_shows_popup(self):
        """バージョンが変わっていれば表示する"""
        assert should_show_release_notes("1.21.7", "1.21.6") is True


class TestFindReleaseNotesPath:
    def test_returns_existing_file(self, tmp_path):
        notes = tmp_path / "RELEASE_NOTES_v1.21.6.md"
        notes.write_text("test", encoding="utf-8")
        result = find_release_notes_path(tmp_path, "1.21.6")
        assert result == notes

    def test_returns_none_when_missing(self, tmp_path):
        result = find_release_notes_path(tmp_path, "9.9.9")
        assert result is None
