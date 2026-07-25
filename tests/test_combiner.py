"""
PDF結合機能のテスト
要件定義書 8.テスト要件の実装
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import fitz

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.combiner import PDFCombiner, CombineResult


def _create_test_pdf(path: str) -> str:
    """テスト用の最小PDFを作成して返す"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "test", fontsize=12)
    doc.save(path)
    doc.close()
    return path


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
    
    def test_combine_pdfs_success(self):
        """PDF結合成功テスト（実際のPDFを使用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf1 = _create_test_pdf(str(Path(temp_dir) / "file1.pdf"))
            pdf2 = _create_test_pdf(str(Path(temp_dir) / "file2.pdf"))
            output = str(Path(temp_dir) / "output.pdf")

            result = self.combiner.combine_pdfs([pdf1, pdf2], output)

            assert result.success is True
            assert len(result.processed_files) == 2
            assert result.total_pages == 2  # 各1ページ × 2ファイル
            assert Path(output).exists()
    
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
    
    def test_validate_pdf_files_success(self):
        """PDF妥当性チェック成功テスト（実際のPDFを使用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_pdf = _create_test_pdf(str(Path(temp_dir) / "valid.pdf"))
            result = self.combiner._validate_pdf_files([valid_pdf])
            assert len(result) == 1
            assert result[0] == valid_pdf
    
    def test_ensure_output_directory(self):
        """出力ディレクトリ確保テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "subdir" / "test.pdf")
            self.combiner._ensure_output_directory(output_path)
            assert Path(temp_dir, "subdir").exists()
    
    def test_get_pdf_info_success(self):
        """PDF情報取得成功テスト（実際のPDFを使用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = _create_test_pdf(str(Path(temp_dir) / "test.pdf"))
            info = self.combiner.get_pdf_info(pdf_path)
            assert info['pages'] == 1
            assert info['file_size'] > 0
            assert info['file_name'] == "test.pdf"
            assert info['encrypted'] is False

    def test_get_pdf_info_error(self):
        """PDF情報取得エラーテスト"""
        info = self.combiner.get_pdf_info("nonexistent_invalid.pdf")
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


    def test_combine_pdfs_with_blank_page(self):
        """奇数ページPDFへの白紙挿入テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf1 = _create_test_pdf(str(Path(temp_dir) / "odd.pdf"))  # 1ページ（奇数）
            output = str(Path(temp_dir) / "output.pdf")

            result = self.combiner.combine_pdfs([pdf1], output, add_blank_page=True)

            assert result.success is True
            # 奇数ページなので白紙が追加され2ページになる
            with fitz.open(output) as doc:
                assert doc.page_count == 2

    def test_combine_pdfs_with_page_numbers(self):
        """ページ番号挿入テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf1 = _create_test_pdf(str(Path(temp_dir) / "p1.pdf"))
            pdf2 = _create_test_pdf(str(Path(temp_dir) / "p2.pdf"))
            output = str(Path(temp_dir) / "output.pdf")

            result = self.combiner.combine_pdfs(
                [pdf1, pdf2], output,
                add_page_numbers=True, start_number=1
            )

            assert result.success is True
            assert result.total_pages == 2

    def test_combine_pdfs_single_file(self):
        """単一ファイル結合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf1 = _create_test_pdf(str(Path(temp_dir) / "single.pdf"))
            output = str(Path(temp_dir) / "output.pdf")

            result = self.combiner.combine_pdfs([pdf1], output)

            assert result.success is True
            assert len(result.processed_files) == 1

    def test_document_number_white_background(self):
        """資料番号の枠内を白色で塗りつぶせる"""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            pdf_path = _create_test_pdf(str(source_dir / "document.pdf"))

            result = self.combiner.add_document_numbers(
                [pdf_path], "", "1", output_dir=str(output_dir),
                white_background=True,
            )

            assert result.success is True
            with fitz.open(result.processed_files[0]) as doc:
                drawings = doc[0].get_drawings()
                assert any(drawing.get("fill") == (1.0, 1.0, 1.0) for drawing in drawings)

    @pytest.mark.parametrize(
        ("width", "height", "expected"),
        [
            (595.2756, 841.8898, 1.0),       # 通常のA4縦
            (841.8898, 595.2756, 1.0),       # 通常のA4横
            (793.6, 1122.24, 4 / 3),         # Excelの96dpi相当A4縦
            (1122.24, 793.6, 4 / 3),         # Excelの96dpi相当A4横
            (841.8898, 1190.5512, 1.0),      # A3は補正対象外
        ],
    )
    def test_document_number_page_scale(self, width, height, expected):
        scale = self.combiner._document_number_page_scale(width, height)
        assert scale == pytest.approx(expected, rel=0.002)

    def test_document_number_is_scaled_for_enlarged_a4_coordinates(self):
        """4/3倍座標のA4で資料NOがA4印刷時に縮小されない"""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            pdf_path = source_dir / "enlarged_a4.pdf"

            with fitz.open() as doc:
                doc.new_page(width=793.6, height=1122.24)
                doc.save(pdf_path)

            result = self.combiner.add_document_numbers(
                [str(pdf_path)], "", "1", doc_font_size=20,
                output_dir=str(output_dir),
            )

            assert result.success is True
            with fitz.open(result.processed_files[0]) as doc:
                spans = [
                    span
                    for block in doc[0].get_text("dict")["blocks"]
                    if "lines" in block
                    for line in block["lines"]
                    for span in line["spans"]
                    if "資料1" in span["text"]
                ]
                assert len(spans) == 1
                assert spans[0]["size"] == pytest.approx(20 * 4 / 3, rel=0.002)


class TestOverwriteOutput:
    """出力時の上書き（overwriteパラメータ）のテスト。

    同じファイル名で繰り返し処理すると (2).pdf のような連番ファイルが
    増え続けて整理しづらいというフィードバックを受けて追加した。
    overwrite=Trueなら、同名ファイルがあってもその名前のまま上書きする。
    """

    def setup_method(self):
        self.combiner = PDFCombiner()

    def test_add_document_numbers_overwrite_reuses_same_filename(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_dir = tmp_path / "out"
        src = src_dir / "a.pdf"
        _create_test_pdf(str(src))

        first = self.combiner.add_document_numbers(
            [str(src)], "", "1", output_dir=str(out_dir),
        )
        assert first.success is True
        first_output = first.processed_files[0]
        assert Path(first_output).name == "a.pdf"

        second = self.combiner.add_document_numbers(
            [str(src)], "", "2", output_dir=str(out_dir), overwrite=True,
        )
        assert second.success is True
        second_output = second.processed_files[0]

        # overwrite=Trueなら (2).pdf のような連番が付かず、同じファイル名で上書きされる
        assert second_output == first_output

    def test_add_document_numbers_without_overwrite_appends_number(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_dir = tmp_path / "out"
        src = src_dir / "a.pdf"
        _create_test_pdf(str(src))

        first = self.combiner.add_document_numbers(
            [str(src)], "", "1", output_dir=str(out_dir),
        )
        second = self.combiner.add_document_numbers(
            [str(src)], "", "2", output_dir=str(out_dir),
        )

        # overwrite未指定（従来通り）なら別ファイル名になる
        assert second.processed_files[0] != first.processed_files[0]
        assert "(2)" in Path(second.processed_files[0]).name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
