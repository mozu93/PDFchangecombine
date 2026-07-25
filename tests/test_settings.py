"""
ユーザー設定永続化（settings.py）のテスト
要件定義書 5.6.保守性・テスト自動化の実装
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import settings


@pytest.fixture
def isolated_settings_path(tmp_path, monkeypatch):
    """実際の%APPDATA%を汚さないよう、設定ファイルの保存先を一時ディレクトリに差し替える"""
    settings_dir = tmp_path / "PDF変換・結合ツール"
    settings_path = settings_dir / "settings.json"
    monkeypatch.setattr(settings, "_SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(settings, "SETTINGS_PATH", settings_path)
    return settings_path


class TestLoadSettings:
    def test_missing_file_returns_defaults(self, isolated_settings_path):
        result = settings.load_settings()
        assert result == settings.DEFAULT_SETTINGS
        # デフォルト辞書のコピーであり、同一オブジェクトではないこと
        assert result is not settings.DEFAULT_SETTINGS

    def test_corrupted_json_falls_back_to_defaults(self, isolated_settings_path):
        isolated_settings_path.parent.mkdir(parents=True)
        isolated_settings_path.write_text("{not valid json", encoding="utf-8")

        result = settings.load_settings()
        assert result == settings.DEFAULT_SETTINGS

    def test_saved_values_are_restored(self, isolated_settings_path):
        custom = settings.DEFAULT_SETTINGS.copy()
        custom["doc_font"] = "游ゴシック"
        custom["add_blank_page"] = True

        settings.save_settings(custom)
        result = settings.load_settings()

        assert result["doc_font"] == "游ゴシック"
        assert result["add_blank_page"] is True

    def test_unknown_keys_in_file_are_ignored(self, isolated_settings_path):
        isolated_settings_path.parent.mkdir(parents=True)
        isolated_settings_path.write_text(
            '{"doc_font": "MS明朝", "totally_unknown_key": 123}', encoding="utf-8"
        )

        result = settings.load_settings()
        assert result["doc_font"] == "MS明朝"
        assert "totally_unknown_key" not in result

    def test_partial_file_merges_with_defaults(self, isolated_settings_path):
        isolated_settings_path.parent.mkdir(parents=True)
        isolated_settings_path.write_text('{"rename_file": true}', encoding="utf-8")

        result = settings.load_settings()
        assert result["rename_file"] is True
        # 未指定のキーはデフォルト値のまま
        assert result["doc_font"] == settings.DEFAULT_SETTINGS["doc_font"]


class TestSaveSettings:
    def test_creates_directory_if_missing(self, isolated_settings_path):
        assert not isolated_settings_path.parent.exists()
        settings.save_settings(settings.DEFAULT_SETTINGS)
        assert isolated_settings_path.exists()

    def test_save_failure_does_not_raise(self, isolated_settings_path, monkeypatch):
        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(settings.Path, "mkdir", boom)
        # 例外を投げずに完了すること（ログ警告のみ）
        settings.save_settings(settings.DEFAULT_SETTINGS)
