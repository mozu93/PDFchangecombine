"""
セキュリティユーティリティ（SecurityValidator / InputValidator）のテスト
要件定義書 5.4.セキュリティ要件・5.6.テスト自動化の実装
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.security import SecurityValidator, InputValidator


class TestSecurityValidatorFilePath:
    """SecurityValidator.validate_file_path のテスト"""

    def test_empty_or_none_rejected(self):
        assert SecurityValidator.validate_file_path("") is False
        assert SecurityValidator.validate_file_path(None) is False

    def test_path_traversal_rejected(self, tmp_path):
        traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")
        assert SecurityValidator.validate_file_path(traversal_path) is False

    def test_control_character_rejected(self, tmp_path):
        malicious = str(tmp_path / "evil\x00.pdf")
        assert SecurityValidator.validate_file_path(malicious) is False

    def test_windows_reserved_name_rejected(self, tmp_path):
        # CONはWindowsのデバイス予約名でOSレベルでも作成できないため、実ファイルは作らず
        # パス解決のみで判定されることを確認する（validate_file_pathは実在チェックより前に判定する）
        reserved = str(tmp_path / "CON.pdf")
        assert SecurityValidator.validate_file_path(reserved) is False

    def test_illegal_filename_characters_rejected(self, tmp_path):
        illegal = str(tmp_path / "bad<name>.pdf")
        assert SecurityValidator.validate_file_path(illegal) is False

    def test_unsupported_extension_rejected(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("hello")
        assert SecurityValidator.validate_file_path(str(f)) is False

    def test_nonexistent_file_rejected(self, tmp_path):
        missing = tmp_path / "missing.pdf"
        assert SecurityValidator.validate_file_path(str(missing)) is False

    def test_directory_rejected(self, tmp_path):
        directory = tmp_path / "somedir.pdf"
        directory.mkdir()
        assert SecurityValidator.validate_file_path(str(directory)) is False

    def test_valid_existing_pdf_accepted(self, tmp_path):
        f = tmp_path / "report.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        assert SecurityValidator.validate_file_path(str(f)) is True

    def test_valid_file_outside_base_dir_still_accepted(self, tmp_path):
        # base_dir外でも安全なファイルなら許可される仕様（コメント参照）
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        f = other_dir / "doc.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        assert SecurityValidator.validate_file_path(str(f), base_dir=str(base_dir)) is True


class TestSecurityValidatorMultiplePaths:
    def test_filters_out_invalid_paths(self, tmp_path):
        valid = tmp_path / "a.pdf"
        valid.write_bytes(b"%PDF-1.4")
        invalid = tmp_path / "missing.pdf"

        result = SecurityValidator.validate_multiple_paths([str(valid), str(invalid)])
        assert result == [str(valid)]

    def test_empty_list_returns_empty(self):
        assert SecurityValidator.validate_multiple_paths([]) == []


class TestSecurityValidatorOutputPath:
    def test_output_within_source_dir_accepted(self, tmp_path):
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        output_path = source_dir / "out.pdf"
        assert SecurityValidator.validate_output_path(str(output_path), str(source_dir)) is True

    def test_output_outside_source_dir_rejected(self, tmp_path):
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        output_path = outside_dir / "out.pdf"
        assert SecurityValidator.validate_output_path(str(output_path), str(source_dir)) is False


class TestSanitizeFilename:
    def test_removes_illegal_characters(self):
        sanitized = SecurityValidator.sanitize_filename('bad<>:"|?*name.pdf')
        assert sanitized == "bad_______name.pdf"

    def test_reserved_name_gets_prefixed(self):
        sanitized = SecurityValidator.sanitize_filename("CON.pdf")
        assert sanitized == "_CON.pdf"

    def test_normal_filename_untouched(self):
        assert SecurityValidator.sanitize_filename("資料1.pdf") == "資料1.pdf"

    def test_overlong_filename_truncated(self):
        long_name = "a" * 300 + ".pdf"
        sanitized = SecurityValidator.sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".pdf")


class TestInputValidatorDocumentNumber:
    def test_valid_number(self):
        assert InputValidator.validate_document_number("資料1") is True

    def test_empty_rejected(self):
        assert InputValidator.validate_document_number("") is False
        assert InputValidator.validate_document_number(None) is False

    def test_too_long_rejected(self):
        assert InputValidator.validate_document_number("a" * 21) is False

    def test_boundary_20_chars_accepted(self):
        assert InputValidator.validate_document_number("a" * 20) is True

    @pytest.mark.parametrize("bad_char", ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}'])
    def test_dangerous_characters_rejected(self, bad_char):
        assert InputValidator.validate_document_number(f"資料{bad_char}") is False

    def test_platform_dependent_char_allowed_by_default_font(self):
        # グリフ不足フォント指定時のみ弾かれるため、未指定なら許可される
        assert InputValidator.validate_document_number("資料①") is True

    def test_platform_dependent_char_rejected_for_glyph_limited_font(self):
        assert InputValidator.validate_document_number("資料①", font_name="BIZ UDPゴシック") is False

    def test_normal_char_accepted_for_glyph_limited_font(self):
        assert InputValidator.validate_document_number("資料1", font_name="BIZ UDPゴシック") is True


class TestFindPlatformDependentChar:
    def test_finds_circled_number(self):
        assert InputValidator.find_platform_dependent_char("項目①") == "①"

    def test_finds_roman_numeral(self):
        assert InputValidator.find_platform_dependent_char("ⅢChapter") == "Ⅲ"

    def test_returns_none_for_clean_text(self):
        assert InputValidator.find_platform_dependent_char("資料1-2") is None


class TestInputValidatorPageRange:
    def test_valid_range(self):
        assert InputValidator.validate_page_range("1", "1") is True

    def test_empty_values_accepted(self):
        assert InputValidator.validate_page_range("", "") is True

    def test_zero_rejected(self):
        assert InputValidator.validate_page_range("0", "1") is False

    def test_over_max_rejected(self):
        assert InputValidator.validate_page_range("1", "10000") is False

    def test_non_numeric_rejected(self):
        assert InputValidator.validate_page_range("abc", "1") is False
