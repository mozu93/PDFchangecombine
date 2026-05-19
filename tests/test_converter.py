"""
PDF変換機能のテスト
要件定義書 8.テスト要件の実装
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.converter import PDFConverter, ConversionResult
from src.core.office_converter import OfficeConverter
from src.core.image_converter import ImageConverter


class TestConversionResult:
    """ConversionResultクラスのテスト"""

    def test_conversion_result_initialization(self):
        """ConversionResult初期化テスト"""
        result = ConversionResult("input.docx")
        assert result.source_path == "input.docx"
        assert result.target_paths == []
        assert result.success is False
        assert result.error_message == ""
        assert result.processing_time == 0.0

    def test_conversion_result_with_values(self):
        """ConversionResult値設定テスト"""
        result = ConversionResult(
            source_path="input.docx",
            target_paths=["output.pdf"],
            success=True,
            error_message=""
        )
        assert result.source_path == "input.docx"
        assert result.target_paths == ["output.pdf"]
        assert result.success is True


class TestPDFConverter:
    """PDFConverterクラスのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.converter = PDFConverter()
    
    def teardown_method(self):
        """テストクリーンアップ"""
        if hasattr(self, 'converter'):
            self.converter.cleanup()
    
    @patch('src.core.converter.FileValidator')
    def test_validate_file_success(self, mock_validator):
        """ファイル妥当性チェック成功テスト"""
        mock_validator.is_readable_file.return_value = True
        mock_validator.is_supported_file.return_value = True
        mock_validator.is_valid_file_size.return_value = True
        
        result = self.converter._validate_file("test.docx")
        assert result is True
    
    @patch('src.core.converter.FileValidator')
    def test_validate_file_failure(self, mock_validator):
        """ファイル妥当性チェック失敗テスト"""
        mock_validator.is_readable_file.return_value = False
        
        result = self.converter._validate_file("test.docx")
        assert result is False
    
    def test_convert_files_async_empty_list(self):
        """空リスト変換テスト"""
        import asyncio
        results = asyncio.run(self.converter.convert_files_async([]))
        assert len(results) == 0
    
    @patch('src.core.converter.PDFConverter._validate_file')
    @patch('src.core.converter.OutputManager.get_output_file_path')
    @patch('src.core.converter.FileValidator.get_file_type')
    def test_convert_single_file_success(self, mock_get_type, mock_get_path, mock_validate):
        """単一ファイル変換成功テスト"""
        mock_validate.return_value = True
        mock_get_path.return_value = "output.pdf"
        mock_get_type.return_value = "word"

        with patch.object(self.converter.office_converter, 'convert_to_pdf', return_value=["output.pdf"]):
            with patch('src.core.converter.fitz.open'):
                result = self.converter._convert_single_file("test.docx")

            assert result.success is True
            assert "output.pdf" in result.target_paths
            assert result.error_message == ""
    
    @patch('src.core.converter.PDFConverter._validate_file')
    def test_convert_single_file_validation_failure(self, mock_validate):
        """ファイル妥当性チェック失敗による変換失敗テスト"""
        mock_validate.return_value = False
        
        result = self.converter._convert_single_file("invalid.txt")
        assert result.success is False
        assert "妥当性チェック失敗" in result.error_message
    
    def test_get_conversion_statistics(self):
        """変換統計情報取得テスト"""
        results = [
            ConversionResult("file1.docx", ["file1.pdf"], True),
            ConversionResult("file2.xlsx", ["file2.pdf"], True),
            ConversionResult("file3.pptx", [], False, "エラー")
        ]

        stats = self.converter.get_conversion_statistics(results)

        assert stats['total_files'] == 3
        assert stats['successful_count'] == 2
        assert stats['failed_count'] == 1
        assert abs(stats['success_rate'] - 200 / 3) < 0.01
        assert len(stats['successful_files']) == 2
        assert len(stats['failed_files']) == 1


    def test_copy_pdf_file_success(self):
        """PDFコピー成功テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            import fitz
            src = Path(temp_dir) / "source.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(str(src))
            doc.close()

            dst = str(Path(temp_dir) / "dest_subdir" / "output.pdf")
            result = self.converter._copy_pdf_file(str(src), dst)
            assert result is True
            assert Path(dst).exists()

    def test_copy_pdf_file_missing_source(self):
        """コピー元不在テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.converter._copy_pdf_file(
                str(Path(temp_dir) / "nonexistent.pdf"),
                str(Path(temp_dir) / "out.pdf")
            )
            assert result is False


class TestOfficeConverter:
    """OfficeConverterクラスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.converter = OfficeConverter()

    def test_initialization(self):
        """初期化テスト"""
        assert self.converter is not None

    @patch.object(OfficeConverter, '_try_office_conversion', return_value=["output.pdf"])
    def test_convert_word_to_pdf_success(self, mock_try):
        """Word変換成功テスト（COM APIモック）"""
        result = self.converter._convert_word_to_pdf("test.docx", "output.pdf")
        assert result == ["output.pdf"]
        mock_try.assert_called_once()

    def test_convert_to_pdf_unsupported_format(self):
        """非対応形式変換テスト"""
        result = self.converter.convert_to_pdf("test.txt", "output.pdf")
        assert result == []

    @patch.object(OfficeConverter, '_try_office_conversion', return_value=[])
    def test_convert_word_to_pdf_no_com_api(self, mock_try):
        """COM API失敗時はWordの変換結果が空リストになること"""
        result = self.converter._convert_word_to_pdf("test.docx", "output.pdf")
        assert result == []

    @patch.object(OfficeConverter, '_try_office_conversion', return_value=["out1.pdf", "out2.pdf"])
    def test_convert_excel_split_sheets(self, mock_try):
        """Excelシート分割変換テスト"""
        result = self.converter._convert_excel_to_pdf("data.xlsx", "out.pdf", split_sheets=True)
        assert result == ["out1.pdf", "out2.pdf"]
        mock_try.assert_called_once_with("data.xlsx", "out.pdf", True)


class TestImageConverter:
    """ImageConverterクラスのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.converter = ImageConverter()
    
    def test_initialization(self):
        """初期化テスト"""
        from src.config import SUPPORTED_IMAGE_EXTENSIONS
        assert self.converter.supported_formats == SUPPORTED_IMAGE_EXTENSIONS
    
    def test_is_supported_format(self):
        """対応形式チェックテスト"""
        assert self.converter.is_supported_format("test.jpg") is True
        assert self.converter.is_supported_format("test.png") is True
        assert self.converter.is_supported_format("test.gif") is True
        assert self.converter.is_supported_format("test.txt") is False
    
    @patch('src.core.image_converter.Image.open')
    @patch('src.core.image_converter.canvas.Canvas')
    def test_convert_single_image_success(self, mock_canvas, mock_image_open):
        """単一画像変換成功テスト"""
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (800, 600)
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock ReportLab Canvas
        mock_canvas_obj = MagicMock()
        mock_canvas.return_value = mock_canvas_obj
        
        with patch.object(self.converter, '_add_image_to_canvas_with_pil', return_value=True):
            result = self.converter._convert_single_image("test.jpg", "output.pdf")
            assert result is True
    
    @patch('src.core.image_converter.Image.open')
    def test_convert_single_image_failure(self, mock_image_open):
        """単一画像変換失敗テスト"""
        mock_image_open.side_effect = Exception("画像読み込みエラー")
        
        result = self.converter._convert_single_image("test.jpg", "output.pdf")
        assert result is False
    
    def test_get_image_info_invalid_file(self):
        """無効画像ファイル情報取得テスト"""
        with patch('src.core.image_converter.Image.open', side_effect=Exception("エラー")):
            info = self.converter.get_image_info("invalid.jpg")
            assert info == {}


class TestExcelSheetNumbering:
    """Excelシート分割時の連番ファイル名テスト"""

    def test_sheet_filenames_are_numbered_sequentially(self):
        """シートファイル名に左から順の2桁連番が付く"""
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        converter = OfficeConverter()

        mock_sheet1 = MagicMock()
        mock_sheet1.Name = "Sheet1"
        mock_sheet2 = MagicMock()
        mock_sheet2.Name = "データ"
        mock_sheet3 = MagicMock()
        mock_sheet3.Name = "まとめ"

        mock_workbook = MagicMock()
        mock_workbook.Worksheets = [mock_sheet1, mock_sheet2, mock_sheet3]

        mock_excel_app = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_workbook.ActiveSheet = mock_sheet1

        generated = []

        mock_sheet1.ExportAsFixedFormat.side_effect = lambda **kw: generated.append(kw["Filename"])
        mock_sheet2.ExportAsFixedFormat.side_effect = lambda **kw: generated.append(kw["Filename"])
        mock_sheet3.ExportAsFixedFormat.side_effect = lambda **kw: generated.append(kw["Filename"])

        with patch("win32com.client.DispatchEx", return_value=mock_excel_app), \
             patch("win32com.client.Dispatch", return_value=mock_excel_app):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = str(Path(tmpdir) / "report.xlsx")
                Path(input_path).touch()
                output_path = str(Path(tmpdir) / "report.pdf")
                converter._try_office_conversion(input_path, output_path, split_sheets=True)

        assert len(generated) == 3
        names = [Path(p).name for p in generated]
        assert names[0] == "report_01_Sheet1.pdf"
        assert names[1] == "report_02_データ.pdf"
        assert names[2] == "report_03_まとめ.pdf"


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])