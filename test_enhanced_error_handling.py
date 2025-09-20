"""
強化されたエラーハンドリングのテスト
"""
import sys
import os
from pathlib import Path
import logging

# srcディレクトリをパスに追加
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/core')
sys.path.insert(0, 'src/utils')

# ログ設定（詳細レベル）
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 必要なモジュールを手動でインポート
import fitz
import time

# ログラー設定
logger = logging.getLogger(__name__)

class FileValidator:
    @staticmethod
    def is_readable_file(file_path):
        try:
            return os.access(file_path, os.R_OK)
        except:
            return False

class CombineResult:
    def __init__(self, output_path: str = "", success: bool = False,
                 error_message: str = "", processed_files: list = None):
        self.output_path = output_path
        self.success = success
        self.error_message = error_message
        self.processed_files = processed_files or []
        self.processing_time = 0.0
        self.total_pages = 0

class TestPDFCombiner:
    """テスト用の簡略化されたPDFCombiner"""

    def __init__(self):
        logger.info("TestPDFCombiner初期化完了")

    def combine_pdfs(self, pdf_paths: list, output_path: str,
                    add_blank_page: bool = False,
                    add_page_numbers: bool = False,
                    start_page: int = 1,
                    start_number: int = 1,
                    progress_callback = None):
        """強化されたエラーハンドリングを含むPDF結合"""
        start_time = time.time()
        result = CombineResult(output_path=output_path)

        logger.info(f"=== PDF結合開始 ===")
        logger.info(f"入力ファイル数: {len(pdf_paths)}")
        logger.info(f"出力パス: {output_path}")
        logger.info(f"白紙ページ追加: {add_blank_page}")
        logger.info(f"ページ番号追加: {add_page_numbers}")

        if not pdf_paths:
            result.error_message = "結合対象ファイルが指定されていません"
            logger.error(result.error_message)
            return result

        try:
            # ファイル検証
            valid_files = []
            for pdf_path in pdf_paths:
                logger.info(f"ファイル検証: {pdf_path}")

                if not Path(pdf_path).is_file():
                    logger.warning(f"ファイルが存在しません: {pdf_path}")
                    continue

                if not FileValidator.is_readable_file(pdf_path):
                    logger.warning(f"読み取り不可ファイル: {pdf_path}")
                    continue

                try:
                    doc = fitz.open(pdf_path)
                    if doc.page_count == 0:
                        logger.warning(f"空のPDFファイル: {pdf_path}")
                        doc.close()
                        continue
                    doc.close()
                    valid_files.append(pdf_path)
                    logger.info(f"ファイル検証OK: {pdf_path}")
                except Exception as e:
                    logger.warning(f"PDF構造エラー: {pdf_path} - {e}")
                    continue

            if not valid_files:
                result.error_message = "有効なPDFファイルがありません"
                logger.error(result.error_message)
                return result

            logger.info(f"有効ファイル数: {len(valid_files)}")

            # PDF結合実行
            writer = fitz.open()
            processed_files = []

            for i, pdf_path in enumerate(valid_files):
                try:
                    logger.info(f"処理中 ({i+1}/{len(valid_files)}): {Path(pdf_path).name}")

                    reader = fitz.open(pdf_path)

                    if add_blank_page and len(reader) % 2 != 0:
                        logger.info(f"白紙ページ追加処理: {Path(pdf_path).name}")
                        temp_doc = fitz.open()
                        temp_doc.insert_pdf(reader)

                        # 回転対応の白紙ページ追加
                        last_page_index = len(temp_doc) - 1
                        last_page = temp_doc[last_page_index]
                        rotation = last_page.rotation
                        mediabox = last_page.mediabox

                        logger.debug(f"最終ページ回転: {rotation}度")
                        logger.debug(f"MediaBox: {mediabox}")

                        blank_page = temp_doc.new_page(width=mediabox.width, height=mediabox.height)

                        if rotation != 0:
                            blank_page_index = len(temp_doc) - 1
                            temp_doc[blank_page_index].set_rotation(rotation)

                        writer.insert_pdf(temp_doc)
                        temp_doc.close()
                        logger.info(f"白紙ページ追加完了（回転{rotation}度対応）")
                    else:
                        writer.insert_pdf(reader)

                    reader.close()
                    processed_files.append(pdf_path)

                except Exception as e:
                    logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                    continue

            if len(writer) == 0:
                result.error_message = "結合可能なページがありませんでした"
                logger.error(result.error_message)
                return result

            # ページ番号挿入
            if add_page_numbers:
                logger.info("ページ番号挿入開始")

                clean_doc = fitz.open()
                clean_doc.insert_pdf(writer)
                writer.close()
                writer = clean_doc

                font_name = "cour"

                for page_num in range(start_page - 1, len(writer)):
                    page = writer[page_num]
                    page_number_text = str(start_number + page_num - (start_page - 1))

                    # 回転対応
                    original_rotation = page.rotation

                    if original_rotation != 0:
                        page.set_rotation(0)

                    text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)
                    x = (page.rect.width - text_width) / 2
                    y = page.rect.height - 28.35

                    page.insert_text((x, y), page_number_text, fontname=font_name, fontsize=12, color=(0, 0, 0))

                    if original_rotation != 0:
                        page.set_rotation(original_rotation)

                logger.info("ページ番号挿入完了")

            # ディレクトリ準備
            self._ensure_output_directory(output_path)
            result.total_pages = len(writer)

            # 保存処理（強化されたエラーハンドリング）
            logger.info(f"PDF保存開始: {output_path}")
            logger.info(f"保存ページ数: {result.total_pages}")
            logger.info(f"出力ディレクトリ: {Path(output_path).parent}")
            logger.info(f"ディレクトリ存在確認: {Path(output_path).parent.exists()}")

            try:
                writer.save(output_path, garbage=0, deflate=False)
                logger.info(f"PDF保存処理完了: {output_path}")

                # 保存後の検証
                if Path(output_path).exists():
                    file_size = Path(output_path).stat().st_size
                    logger.info(f"保存ファイル確認OK: {file_size:,} bytes")
                else:
                    logger.error(f"保存ファイルが見つかりません: {output_path}")
                    result.error_message = "保存ファイルの作成に失敗しました"
                    return result

            except Exception as save_error:
                logger.error(f"PDF保存エラー: {save_error}")
                result.error_message = f"ファイル保存エラー: {str(save_error)}"
                return result
            finally:
                writer.close()

            # 結果設定
            result.success = True
            result.processed_files = processed_files

            logger.info(f"PDF結合完了: {len(processed_files)}ファイル, {result.total_pages}ページ")

        except Exception as e:
            result.error_message = f"結合処理エラー: {str(e)}"
            logger.error(f"PDF結合エラー: {str(e)}", exc_info=True)

        finally:
            result.processing_time = time.time() - start_time
            logger.info(f"総処理時間: {result.processing_time:.2f}秒")

        return result

    def _ensure_output_directory(self, output_path: str) -> None:
        """出力ディレクトリの確保"""
        try:
            output_dir = Path(output_path).parent
            logger.info(f"出力ディレクトリチェック: {output_dir}")

            if not output_dir.exists():
                logger.info(f"ディレクトリが存在しないため作成します: {output_dir}")
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"出力ディレクトリ作成完了: {output_dir}")
            else:
                logger.info(f"出力ディレクトリ確認OK: {output_dir}")

            # 書き込み権限チェック
            if not os.access(output_dir, os.W_OK):
                logger.error(f"出力ディレクトリに書き込み権限がありません: {output_dir}")
                raise PermissionError(f"書き込み権限がありません: {output_dir}")

        except Exception as e:
            logger.error(f"出力ディレクトリ準備エラー: {e}")
            raise

def test_enhanced_error_handling():
    """強化されたエラーハンドリングのテスト"""
    print("=== 強化されたエラーハンドリングテスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    combiner = TestPDFCombiner()

    # 正常ケースのテスト
    print("\n1. 正常ケーステスト")
    result1 = combiner.combine_pdfs(
        [problem_pdf],
        "test_enhanced_normal.pdf",
        add_blank_page=True,
        add_page_numbers=True
    )

    if result1.success:
        print(f"[SUCCESS] 正常処理: {result1.total_pages}ページ, {result1.processing_time:.2f}秒")
    else:
        print(f"[FAILED] 正常処理失敗: {result1.error_message}")

    # 異常ケースのテスト
    print("\n2. 異常ケーステスト")

    # 存在しないディレクトリに保存
    result2 = combiner.combine_pdfs(
        [problem_pdf],
        "nonexistent_directory/test_output.pdf",
        add_blank_page=False,
        add_page_numbers=False
    )

    if result2.success:
        print(f"[SUCCESS] 存在しないディレクトリテスト: {result2.total_pages}ページ")
    else:
        print(f"[EXPECTED_FAIL] 存在しないディレクトリテスト: {result2.error_message}")

if __name__ == "__main__":
    test_enhanced_error_handling()