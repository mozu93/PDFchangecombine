"""
PDF結合機能のテスト
要件定義書 8.テスト要件の実装
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.combiner import PDFCombiner, CombineResult


class TestCombineResult:
    """CombineResultクラスのテスト"""
    
    def test_combine_result_initialization(self):
        """CombineResult初期化テスト"""
        result = CombineResult()
        assert result.output_path == ""
        assert result.success is False
        assert result.error_message == ""
        assert result.processed_files == []
        assert result.processing_time == 0.0
        assert result.total_pages == 0
    
    def test_combine_result_with_values(self):
        """CombineResult値設定テスト"""
        result = CombineResult(
            output_path="combined.pdf",
            success=True,
            processed_files=["file1.pdf", "file2.pdf"]
        )
        assert result.output_path == "combined.pdf"
        assert result.success is True
        assert len(result.processed_files) == 2


class TestPDFCombiner:
    """PDFCombinerクラスのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.combiner = PDFCombiner()
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.combiner is not None
    
    def test_combine_pdfs_empty_list(self):
        """空リスト結合テスト"""
        result = self.combiner.combine_pdfs([], "output.pdf")
        assert result.success is False
        assert "結合対象ファイルが指定されていません" in result.error_message
    
    @patch('src.core.combiner.PDFCombiner._validate_pdf_files')
    def test_combine_pdfs_no_valid_files(self, mock_validate):
        """有効ファイルなし結合テスト"""
        mock_validate.return_value = []
        
        result = self.combiner.combine_pdfs(["invalid.pdf"], "output.pdf")
        assert result.success is False
        assert "有効なPDFファイルがありません" in result.error_message
    
    @patch('src.core.combiner.PDFCombiner._validate_pdf_files')
    @patch('src.core.combiner.PdfReader')
    @patch('src.core.combiner.PdfWriter')
    @patch('src.core.combiner.PDFCombiner._ensure_output_directory')
    @patch('builtins.open', new_callable=mock_open)
    def test_combine_pdfs_success(self, mock_file_open, mock_ensure_dir, 
                                  mock_writer, mock_reader, mock_validate):
        """PDF結合成功テスト"""
        # モック設定
        mock_validate.return_value = ["file1.pdf", "file2.pdf"]
        
        # PDF Reader Mock
        mock_reader_instance = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_reader.return_value = mock_reader_instance
        
        # PDF Writer Mock
        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        
        result = self.combiner.combine_pdfs(["file1.pdf", "file2.pdf"], "output.pdf")
        
        assert result.success is True
        assert len(result.processed_files) == 2
        assert result.total_pages == 4  # 2ファイル × 2ページ
        mock_writer_instance.add_page.assert_called()
        mock_writer_instance.write.assert_called_once()
    
    @patch('src.core.combiner.Path')
    def test_validate_pdf_files_file_not_exists(self, mock_path):
        """存在しないファイルの妥当性チェック"""
        mock_path.return_value.is_file.return_value = False
        
        result = self.combiner._validate_pdf_files(["nonexistent.pdf"])
        assert len(result) == 0
    
    @patch('src.core.combiner.Path')
    def test_validate_pdf_files_not_pdf(self, mock_path):
        """PDFでないファイルの妥当性チェック"""
        mock_path.return_value.is_file.return_value = True
        
        result = self.combiner._validate_pdf_files(["document.txt"])
        assert len(result) == 0
    
    @patch('src.core.combiner.Path')
    @patch('src.core.combiner.FileValidator.is_readable_file')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.core.combiner.PdfReader')
    def test_validate_pdf_files_success(self, mock_reader, mock_file_open, 
                                       mock_is_readable, mock_path):
        """PDF妥当性チェック成功テスト"""
        # モック設定
        mock_path.return_value.is_file.return_value = True
        mock_is_readable.return_value = True
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock()]  # 1ページ
        mock_reader.return_value = mock_reader_instance
        
        result = self.combiner._validate_pdf_files(["valid.pdf"])
        assert len(result) == 1
        assert result[0] == "valid.pdf"
    
    @patch('src.core.combiner.Path')
    def test_ensure_output_directory(self, mock_path):
        """出力ディレクトリ確保テスト"""
        mock_parent = MagicMock()
        mock_parent.exists.return_value = False
        mock_path.return_value.parent = mock_parent
        
        self.combiner._ensure_output_directory("output/test.pdf")
        mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('src.core.combiner.PdfReader')
    @patch('src.core.combiner.Path')
    def test_get_pdf_info_success(self, mock_path, mock_reader):
        """PDF情報取得成功テスト"""
        # モック設定
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock(), MagicMock()]  # 2ページ
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.metadata = {'/Title': 'テストPDF', '/Author': 'テスト作成者'}
        mock_reader.return_value = mock_reader_instance
        
        mock_stat = MagicMock()
        mock_stat.st_size = 1024
        mock_path.return_value.stat.return_value = mock_stat
        mock_path.return_value.name = "test.pdf"
        
        info = self.combiner.get_pdf_info("test.pdf")
        
        assert info['pages'] == 2
        assert info['file_size'] == 1024
        assert info['file_name'] == "test.pdf"
        assert info['encrypted'] is False
        assert info['title'] == 'テストPDF'
        assert info['author'] == 'テスト作成者'
    
    @patch('src.core.combiner.PdfReader')
    def test_get_pdf_info_error(self, mock_reader):
        """PDF情報取得エラーテスト"""
        mock_reader.side_effect = Exception("PDF読み込みエラー")
        
        info = self.combiner.get_pdf_info("invalid.pdf")
        
        assert info['pages'] == 0
        assert info['file_size'] == 0
        assert 'error' in info
    
    def test_reorder_files_success(self):
        """ファイル順序変更成功テスト"""
        files = ["file1.pdf", "file2.pdf", "file3.pdf"]
        result = self.combiner.reorder_files(files, 0, 2)  # file1をfile3の後に移動
        
        expected = ["file2.pdf", "file3.pdf", "file1.pdf"]
        assert result == expected
    
    def test_reorder_files_invalid_index(self):
        """ファイル順序変更無効インデックステスト"""
        files = ["file1.pdf", "file2.pdf"]
        result = self.combiner.reorder_files(files, 5, 1)  # 無効なインデックス
        
        assert result == files  # 変更されない
    
    def test_remove_file_from_list_success(self):
        """ファイル削除成功テスト"""
        files = ["file1.pdf", "file2.pdf", "file3.pdf"]
        result = self.combiner.remove_file_from_list(files, 1)  # file2.pdfを削除
        
        expected = ["file1.pdf", "file3.pdf"]
        assert result == expected
    
    def test_remove_file_from_list_invalid_index(self):
        """ファイル削除無効インデックステスト"""
        files = ["file1.pdf", "file2.pdf"]
        result = self.combiner.remove_file_from_list(files, 5)  # 無効なインデックス
        
        assert result == files  # 変更されない
    
    def test_progress_callback_execution(self):
        """進捗コールバック実行テスト"""
        callback_calls = []
        
        def test_callback(message, progress):
            callback_calls.append((message, progress))
        
        with patch('src.core.combiner.PDFCombiner._validate_pdf_files', return_value=[]):
            result = self.combiner.combine_pdfs(["test.pdf"], "output.pdf", test_callback)
            
            # 有効ファイルなしの場合はコールバック呼び出しなし
            assert result.success is False


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])