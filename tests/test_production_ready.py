# -*- coding: utf-8 -*-
"""
本番配布用包括テストスイート
エラーハンドリング、セキュリティ、パフォーマンス、機能の統合テスト
"""

import unittest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.combiner import PDFCombiner
from src.utils.error_handler import ErrorHandler, ErrorSeverity
from src.utils.logger import AppLogger
from src.utils.security import SecurityValidator, InputValidator
from src.utils.file_utils import FileValidator, FileScanner
import fitz


class TestSecurityFeatures(unittest.TestCase):
    """セキュリティ機能テスト"""

    def setUp(self):
        """テスト環境セットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = self._create_test_pdf()

    def tearDown(self):
        """テスト環境クリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_pdf(self) -> str:
        """テスト用PDFファイル作成"""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "テスト用PDFファイル", fontsize=12)

        pdf_path = Path(self.temp_dir) / "test.pdf"
        doc.save(str(pdf_path))
        doc.close()
        return str(pdf_path)

    def test_path_traversal_protection(self):
        """Path Traversal攻撃の防御テスト"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "test/../../../sensitive_file.txt",
            "normal_file.pdf/../../../etc/hosts"
        ]

        for dangerous_path in dangerous_paths:
            with self.subTest(path=dangerous_path):
                result = SecurityValidator.validate_file_path(dangerous_path)
                self.assertFalse(result, f"危険なパスが許可されました: {dangerous_path}")

    def test_malicious_filename_protection(self):
        """悪意のあるファイル名の防御テスト"""
        malicious_names = [
            "CON.pdf",
            "PRN.docx",
            "file<script>alert('xss')</script>.pdf",
            "file\x00hidden.pdf",
            "file|rm -rf /.pdf"
        ]

        for malicious_name in malicious_names:
            with self.subTest(filename=malicious_name):
                sanitized = SecurityValidator.sanitize_filename(malicious_name)
                self.assertNotIn('<', sanitized)
                self.assertNotIn('>', sanitized)
                self.assertNotIn('\x00', sanitized)

    def test_input_validation(self):
        """入力値検証テスト"""
        # 正常な資料番号
        valid_numbers = ["1", "資料1", "Document-001"]
        for number in valid_numbers:
            with self.subTest(number=number):
                self.assertTrue(InputValidator.validate_document_number(number))

        # 危険な資料番号
        dangerous_numbers = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "a" * 100  # 長すぎる
        ]
        for number in dangerous_numbers:
            with self.subTest(number=number):
                self.assertFalse(InputValidator.validate_document_number(number))

    def test_platform_dependent_char_rejection(self):
        """機種依存文字（①、Ⅰ、㎡など）を含む資料番号・プレフィックスの拒否テスト"""
        bad_numbers = ["①", "資料①", "Ⅰ", "1-①", "㎡"]
        for number in bad_numbers:
            with self.subTest(number=number):
                self.assertFalse(InputValidator.validate_document_number(number))
                self.assertFalse(InputValidator.validate_prefix_text(number))

        good_numbers = ["1", "I", "1-1"]
        for number in good_numbers:
            with self.subTest(number=number):
                self.assertTrue(InputValidator.validate_document_number(number))

    def test_file_size_limits(self):
        """ファイルサイズ制限テスト"""
        # 大きなファイルを模擬
        large_file = Path(self.temp_dir) / "large_file.pdf"
        with open(large_file, 'wb') as f:
            f.write(b'0' * (101 * 1024 * 1024))  # 101MB

        result = FileValidator.is_valid_file_size(str(large_file))
        self.assertFalse(result, "大きすぎるファイルが許可されました")


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングテスト"""

    def setUp(self):
        """テスト環境セットアップ"""
        self.error_handler = ErrorHandler()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """テスト環境クリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_not_found_handling(self):
        """ファイル不存在エラーハンドリング"""
        combiner = PDFCombiner()
        non_existent_file = str(Path(self.temp_dir) / "not_exist.pdf")

        result = combiner.combine_pdfs([non_existent_file], "")
        self.assertFalse(result.success)
        self.assertIn("ありません", result.error_message)

    def test_permission_error_handling(self):
        """権限エラーハンドリング"""
        if os.name == 'nt':  # Windows
            restricted_path = "C:\\Windows\\System32\\test.pdf"
        else:  # Unix系
            restricted_path = "/root/test.pdf"

        combiner = PDFCombiner()
        result = combiner.combine_pdfs([restricted_path], "")
        self.assertFalse(result.success)

    def test_corrupted_pdf_handling(self):
        """破損PDFファイルハンドリング"""
        # 破損PDFファイルを作成
        corrupted_pdf = Path(self.temp_dir) / "corrupted.pdf"
        with open(corrupted_pdf, 'wb') as f:
            f.write(b'This is not a PDF file')

        combiner = PDFCombiner()
        result = combiner.combine_pdfs([str(corrupted_pdf)], "")
        self.assertFalse(result.success)

    def test_error_severity_classification(self):
        """エラー重要度分類テスト"""
        test_cases = [
            (FileNotFoundError("File not found"), ErrorSeverity.CRITICAL),
            (PermissionError("Permission denied"), ErrorSeverity.CRITICAL),
            (MemoryError("Out of memory"), ErrorSeverity.FATAL),
            (ValueError("Invalid value"), ErrorSeverity.WARNING)
        ]

        for error, expected_severity in test_cases:
            with self.subTest(error=type(error).__name__):
                # エラーハンドラーが適切な重要度を判定することをテスト
                # （実際の実装に応じて調整が必要）
                pass


class TestPerformance(unittest.TestCase):
    """パフォーマンステスト"""

    def setUp(self):
        """テスト環境セットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.combiner = PDFCombiner()

    def tearDown(self):
        """テスト環境クリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_pdfs(self, count: int) -> list:
        """複数のテスト用PDFファイル作成"""
        pdf_files = []
        for i in range(count):
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), f"テストPDF {i+1}", fontsize=12)

            pdf_path = Path(self.temp_dir) / f"test_{i+1}.pdf"
            doc.save(str(pdf_path))
            doc.close()
            pdf_files.append(str(pdf_path))

        return pdf_files

    def test_startup_time(self):
        """起動時間テスト（5秒以内）"""
        start_time = time.time()

        # アプリケーション初期化
        combiner = PDFCombiner()
        logger = AppLogger()

        startup_time = time.time() - start_time
        self.assertLess(startup_time, 5.0, f"起動時間が遅すぎます: {startup_time:.2f}秒")

    def test_large_file_processing(self):
        """大量ファイル処理性能テスト"""
        # 50個のPDFファイルで結合テスト
        pdf_files = self._create_test_pdfs(50)

        start_time = time.time()
        result = self.combiner.combine_pdfs(pdf_files, str(Path(self.temp_dir) / "combined.pdf"))
        processing_time = time.time() - start_time

        self.assertTrue(result.success, "大量ファイル処理に失敗")
        self.assertLess(processing_time, 60.0, f"処理時間が遅すぎます: {processing_time:.2f}秒")

    def test_memory_usage(self):
        """メモリ使用量テスト"""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 処理実行
        pdf_files = self._create_test_pdfs(10)
        self.combiner.combine_pdfs(pdf_files, str(Path(self.temp_dir) / "combined.pdf"))

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        self.assertLess(memory_increase, 200, f"メモリ使用量が多すぎます: {memory_increase:.2f}MB増加")


class TestFunctionalIntegration(unittest.TestCase):
    """機能統合テスト"""

    def setUp(self):
        """テスト環境セットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.combiner = PDFCombiner()

    def tearDown(self):
        """テスト環境クリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_pdf(self, filename: str, text: str = None) -> str:
        """テスト用PDFファイル作成"""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), text or f"テスト用PDF: {filename}", fontsize=12)

        pdf_path = Path(self.temp_dir) / filename
        doc.save(str(pdf_path))
        doc.close()
        return str(pdf_path)

    def test_pdf_combination_end_to_end(self):
        """PDF結合のエンドツーエンドテスト"""
        # テスト用PDFファイル作成
        pdf1 = self._create_test_pdf("test1.pdf", "ページ1")
        pdf2 = self._create_test_pdf("test2.pdf", "ページ2")
        pdf3 = self._create_test_pdf("test3.pdf", "ページ3")

        output_path = str(Path(self.temp_dir) / "combined.pdf")

        # 結合実行
        result = self.combiner.combine_pdfs([pdf1, pdf2, pdf3], output_path)

        # 結果検証
        self.assertTrue(result.success, f"結合失敗: {result.error_message}")
        self.assertTrue(Path(output_path).exists(), "出力ファイルが作成されていません")

        # 結合されたPDFの検証
        combined_doc = fitz.open(output_path)
        self.assertEqual(len(combined_doc), 3, "ページ数が正しくありません")
        combined_doc.close()

    def test_document_numbering_modes(self):
        """資料番号挿入モードテスト"""
        # テスト用PDFファイル作成
        pdf_files = [
            self._create_test_pdf("doc1.pdf"),
            self._create_test_pdf("doc2.pdf"),
            self._create_test_pdf("doc3.pdf")
        ]

        # 1. 連番モードテスト
        result = self.combiner.add_sequential_document_numbers(
            pdf_paths=pdf_files,
            numbering_type="basic",
            start_number=1
        )
        self.assertTrue(result.success, "連番モード失敗")

        # 2. ハイフン連番モードテスト
        result = self.combiner.add_sequential_document_numbers(
            pdf_paths=pdf_files,
            numbering_type="hyphen",
            prefix_number="1"
        )
        self.assertTrue(result.success, "ハイフン連番モード失敗")

    def test_error_recovery(self):
        """エラー復旧機能テスト"""
        # 正常ファイルと異常ファイルの混在
        valid_pdf = self._create_test_pdf("valid.pdf")
        invalid_file = str(Path(self.temp_dir) / "invalid.txt")
        with open(invalid_file, 'w') as f:
            f.write("This is not a PDF")

        # 一部失敗でも処理を継続することを確認
        result = self.combiner.combine_pdfs([valid_pdf, invalid_file], "")
        # 実装に応じて期待する動作を調整


class TestDataIntegrity(unittest.TestCase):
    """データ整合性テスト"""

    def setUp(self):
        """テスト環境セットアップ"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """テスト環境クリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_output_file_integrity(self):
        """出力ファイル整合性テスト"""
        # オリジナルファイルと出力ファイルの整合性確認
        pass  # 具体的な整合性チェックロジックを実装

    def test_backup_creation(self):
        """バックアップ作成テスト"""
        # 元ファイルフォルダの作成確認
        pass  # バックアップ機能のテスト実装


def run_production_tests():
    """本番配布用テストスイート実行"""
    print("=== 本番配布用テストスイート実行 ===")

    # テストスイート構成
    test_suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestSecurityFeatures),
        unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling),
        unittest.TestLoader().loadTestsFromTestCase(TestPerformance),
        unittest.TestLoader().loadTestsFromTestCase(TestFunctionalIntegration),
        unittest.TestLoader().loadTestsFromTestCase(TestDataIntegrity),
    ]

    # 全テスト実行
    all_tests = unittest.TestSuite(test_suites)
    runner = unittest.TextTestRunner(verbosity=2)

    start_time = time.time()
    result = runner.run(all_tests)
    execution_time = time.time() - start_time

    # 結果サマリー
    print(f"\n=== テスト結果サマリー ===")
    print(f"実行時間: {execution_time:.2f}秒")
    print(f"テスト総数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")

    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_production_tests()
    sys.exit(0 if success else 1)