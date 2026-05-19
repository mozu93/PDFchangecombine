"""
ファイルユーティリティのテスト
要件定義書 5.6.テスト自動化の実装
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.file_utils import FileValidator, FileScanner, OutputManager
from src.config import ALL_SUPPORTED_EXTENSIONS, OUTPUT_FOLDER_NAME


class TestFileValidator:
    """FileValidatorクラスのテスト"""
    
    def test_is_supported_file_valid_extensions(self):
        """対応形式の正常判定テスト"""
        # Word文書
        assert FileValidator.is_supported_file("test.docx") is True
        assert FileValidator.is_supported_file("test.doc") is True
        
        # Excel文書
        assert FileValidator.is_supported_file("test.xlsx") is True
        assert FileValidator.is_supported_file("test.xls") is True
        
        # PowerPoint文書
        assert FileValidator.is_supported_file("test.pptx") is True
        assert FileValidator.is_supported_file("test.ppt") is True
        
        # 画像ファイル
        assert FileValidator.is_supported_file("test.jpg") is True
        assert FileValidator.is_supported_file("test.png") is True
        assert FileValidator.is_supported_file("test.gif") is True
    
    def test_is_supported_file_invalid_extensions(self):
        """非対応形式の判定テスト"""
        assert FileValidator.is_supported_file("test.txt") is False
        assert FileValidator.is_supported_file("test.zip") is False
        assert FileValidator.is_supported_file("test.exe") is False

    def test_is_supported_file_pdf(self):
        """PDF（コピー対応）の判定テスト"""
        assert FileValidator.is_supported_file("test.pdf") is True
    
    def test_is_supported_file_case_insensitive(self):
        """大文字小文字非依存テスト"""
        assert FileValidator.is_supported_file("test.DOCX") is True
        assert FileValidator.is_supported_file("test.JPG") is True
        assert FileValidator.is_supported_file("test.PNG") is True
    
    def test_get_file_type(self):
        """ファイル種別判定テスト"""
        assert FileValidator.get_file_type("test.docx") == "word"
        assert FileValidator.get_file_type("test.xlsx") == "excel"
        assert FileValidator.get_file_type("test.pptx") == "powerpoint"
        assert FileValidator.get_file_type("test.jpg") == "image"
        assert FileValidator.get_file_type("test.pdf") == "pdf"
        assert FileValidator.get_file_type("test.txt") == "unknown"
    
    @patch('src.utils.file_utils.Path')
    def test_is_valid_file_size(self, mock_path):
        """ファイルサイズ検証テスト"""
        # 正常サイズ (10MB)
        mock_stat = MagicMock()
        mock_stat.st_size = 10 * 1024 * 1024
        mock_path.return_value.stat.return_value = mock_stat
        
        assert FileValidator.is_valid_file_size("test.docx") is True
        
        # サイズ超過 (200MB)
        mock_stat.st_size = 200 * 1024 * 1024
        assert FileValidator.is_valid_file_size("test.docx") is False
    
    @patch('src.utils.file_utils.Path')
    def test_is_readable_file(self, mock_path):
        """読み取り可能性チェックテスト"""
        with patch('os.access', return_value=True):
            mock_path.return_value.is_file.return_value = True
            assert FileValidator.is_readable_file("test.docx") is True
        
        with patch('os.access', return_value=False):
            mock_path.return_value.is_file.return_value = True
            assert FileValidator.is_readable_file("test.docx") is False


class TestFileScanner:
    """FileScannerクラスのテスト"""
    
    def test_scan_files_from_paths_empty_list(self):
        """空リストの処理テスト"""
        result = FileScanner.scan_files_from_paths([])
        assert result['valid'] == []
        assert result['invalid'] == []
    
    @patch('src.utils.file_utils.Path')
    @patch('src.utils.file_utils.FileValidator')
    def test_scan_files_single_valid_file(self, mock_validator, mock_path):
        """単一有効ファイルのスキャンテスト"""
        # モック設定
        mock_path_obj = mock_path.return_value
        mock_path_obj.is_file.return_value = True
        mock_path_obj.is_dir.return_value = False
        
        mock_validator.is_readable_file.return_value = True
        mock_validator.is_supported_file.return_value = True
        mock_validator.is_valid_file_size.return_value = True
        
        result = FileScanner.scan_files_from_paths(["test.docx"])
        assert len(result['valid']) == 1
        assert len(result['invalid']) == 0


class TestOutputManager:
    """OutputManagerクラスのテスト"""
    
    def test_generate_output_filename(self):
        """出力ファイル名生成テスト"""
        filename = OutputManager.generate_output_filename("test.docx")
        assert filename == "test.pdf"
        
        filename = OutputManager.generate_output_filename("/path/to/document.xlsx")
        assert filename == "document.pdf"
    
    @patch('src.utils.file_utils.Path')
    def test_create_output_directory(self, mock_path):
        """出力ディレクトリ作成テスト"""
        mock_parent = MagicMock()
        mock_output_dir = MagicMock()
        
        mock_path.return_value.parent = mock_parent
        mock_parent.__truediv__.return_value = mock_output_dir
        mock_output_dir.mkdir = MagicMock()
        
        result = OutputManager.create_output_directory("test.docx")
        mock_output_dir.mkdir.assert_called_once_with(exist_ok=True)
    
    def test_get_output_file_path_integration(self):
        """出力ファイルパス生成統合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # テスト用ファイル作成
            test_file = Path(temp_dir) / "test.docx"
            test_file.touch()
            
            output_path = OutputManager.get_output_file_path(str(test_file))
            
            # 期待パス構築
            expected_dir = Path(temp_dir) / OUTPUT_FOLDER_NAME
            expected_path = expected_dir / "test.pdf"
            
            assert output_path == str(expected_path)
            assert expected_dir.exists()  # ディレクトリが作成されることを確認


from src.utils.security import InputValidator

class TestValidatePrefixText:
    def test_valid_kanji(self):
        assert InputValidator.validate_prefix_text("別紙") is True

    def test_valid_alphanumeric(self):
        assert InputValidator.validate_prefix_text("Doc") is True

    def test_empty_string(self):
        assert InputValidator.validate_prefix_text("") is False

    def test_too_long(self):
        assert InputValidator.validate_prefix_text("あ" * 11) is False

    def test_dangerous_char_lt(self):
        assert InputValidator.validate_prefix_text("<script>") is False

    def test_dangerous_char_semicolon(self):
        assert InputValidator.validate_prefix_text("資料;") is False


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])