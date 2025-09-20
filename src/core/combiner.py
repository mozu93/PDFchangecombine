"""
PDF結合コアモジュール
要件定義書 4.3 PDF結合モード機能の実装
"""

import os
from pathlib import Path
from typing import List, Optional
import time
import fitz  # PyMuPDF

from ..utils.logger import logger
from ..utils.file_utils import FileValidator


class CombineResult:
    """結合結果を保持するクラス"""

    def __init__(self, output_path: str = "", success: bool = False,
                 error_message: str = "", processed_files: List[str] = None):
        self.output_path = output_path
        self.success = success
        self.error_message = error_message
        self.processed_files = processed_files or []
        self.processing_time = 0.0
        self.total_pages = 0


import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class PDFCombiner:
    """PDF結合メインクラス"""

    def __init__(self):
        logger.info("PDFコンバイナー初期化完了")
        self._register_ms_gothic_font()

    def _register_ms_gothic_font(self):
        try:
            # Windowsのフォントパス
            font_path = "C:/Windows/Fonts/msgothic.ttc"
            if Path(font_path).exists():
                pdfmetrics.registerFont(TTFont('MS-Gothic', font_path, subfontIndex=0))
                logger.info("MSゴシックフォントを登録しました")
                self.font_name = "MS-Gothic"
            else:
                raise FileNotFoundError
        except Exception:
            logger.warning("MSゴシックフォントが見つかりません。Courierで代替します")
            self.font_name = "Courier"

    def combine_pdfs(self, pdf_paths: List[str], output_path: str, 
                    add_blank_page: bool = False,
                    add_page_numbers: bool = False,
                    start_page: int = 1,
                    start_number: int = 1,
                    progress_callback: Optional[callable] = None) -> CombineResult:
        """
        複数PDFファイルの結合（要件定義書 F-204）
        """
        start_time = time.time()
        result = CombineResult(output_path=output_path)

        if not pdf_paths:
            result.error_message = "結合対象ファイルが指定されていません"
            return result

        try:
            valid_files = self._validate_pdf_files(pdf_paths)
            if not valid_files:
                result.error_message = "有効なPDFファイルがありません"
                return result

            # PDF結合実行
            writer = fitz.open()
            processed_files = []

            for i, pdf_path in enumerate(valid_files):
                try:
                    if progress_callback:
                        progress = (i + 1) / len(valid_files) * 90 # 結合処理を90%とする
                        progress_callback(f"結合中: {Path(pdf_path).name}", progress)

                    reader = fitz.open(pdf_path)
                    if add_blank_page and len(reader) % 2 != 0:
                        temp_doc = fitz.open()
                        temp_doc.insert_pdf(reader)

                        # 最終ページの情報を安全に取得
                        last_page_index = len(temp_doc) - 1
                        last_page = temp_doc[last_page_index]

                        # 回転とサイズ情報を取得
                        rotation = last_page.rotation
                        mediabox = last_page.mediabox

                        # 回転を考慮したサイズで白紙ページを作成
                        blank_page = temp_doc.new_page(width=mediabox.width, height=mediabox.height)

                        # 回転情報を適用
                        if rotation != 0:
                            blank_page_index = len(temp_doc) - 1
                            temp_doc[blank_page_index].set_rotation(rotation)

                        writer.insert_pdf(temp_doc)
                        temp_doc.close()
                        logger.info(f"白紙ページ追加（回転{rotation}度対応）: {Path(pdf_path).name}")
                    else:
                        writer.insert_pdf(reader)
                    
                    reader.close()
                    processed_files.append(pdf_path)
                    logger.info(f"PDF追加完了: {Path(pdf_path).name}")

                except Exception as e:
                    logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                    continue

            if len(writer) == 0:
                result.error_message = "結合可能なページがありませんでした"
                return result

            # ページ番号挿入
            if add_page_numbers:
                logger.info("ページ番号の挿入を開始")
                
                # 一度クリーンなPDFを作成してからページ番号を挿入する
                clean_doc = fitz.open()
                clean_doc.insert_pdf(writer)
                writer.close()
                writer = clean_doc

                font_name = "cour"

                for page_num in range(start_page - 1, len(writer)):
                    page = writer[page_num]
                    page_number_text = str(start_number + page_num - (start_page - 1))

                    # 回転を考慮したページ番号配置
                    original_rotation = page.rotation

                    # 回転を一時的に0度にして正しい向きでページ番号を挿入
                    if original_rotation != 0:
                        page.set_rotation(0)

                    # 0度状態での座標計算（テキストが正しい向きで表示される）
                    text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

                    # 0度状態でのページサイズ取得
                    page_width = page.rect.width
                    page_height = page.rect.height

                    # 回転別の正確な座標計算とrotateパラメータ
                    if original_rotation == 0:
                        # 0度: 通常の下部中央
                        x = (page_width - text_width) / 2  # 水平中央
                        y = page_height - 28.35  # 下端から10mm
                        rotate_param = 0
                    elif original_rotation == 90:
                        # 90度回転: 右側中央が下部になる
                        x = page_width - 28.35  # 右端から10mm
                        y = (page_height - text_width) / 2  # 垂直中央
                        rotate_param = -90
                    elif original_rotation == 180:
                        # 180度回転: 上部中央が下部になる
                        x = (page_width - text_width) / 2  # 水平中央
                        y = 28.35  # 上端から10mm
                        rotate_param = 180
                    elif original_rotation == 270:
                        # 270度回転: 左側中央が下部になる
                        x = 28.35  # 左端から10mm
                        y = (page_height - text_width) / 2  # 垂直中央
                        rotate_param = -90
                    else:
                        # その他の角度: デフォルト
                        x = (page_width - text_width) / 2  # 水平中央
                        y = page_height - 28.35  # 下端から10mm
                        rotate_param = 0

                    logger.info(f"ページ番号座標（元回転{original_rotation}度、0度状態での配置）: x={x:.1f}, y={y:.1f}, rotate={rotate_param}")

                    # ページ番号を挿入（全回転角度に対応）
                    page.insert_text((x, y),
                                     page_number_text,
                                     fontname=font_name,
                                     fontsize=12,
                                     color=(0, 0, 0),
                                     rotate=rotate_param)

                    # 回転を元に戻す
                    if original_rotation != 0:
                        page.set_rotation(original_rotation)

                    # logger.debug(f"ページ番号挿入: ページ{page_num+1}, 回転{original_rotation}度")
                logger.info("ページ番号の挿入完了")

            # 結合PDFファイル保存
            self._ensure_output_directory(output_path)
            result.total_pages = len(writer)

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

            # 進捗完了報告
            if progress_callback:
                progress_callback("結合完了", 100)

            logger.info(f"PDF結合完了: {len(processed_files)}ファイル, {result.total_pages}ページ -> {Path(output_path).name}")

        except Exception as e:
            result.error_message = f"結合処理エラー: {str(e)}"
            logger.error(f"PDF結合エラー: {str(e)}", exc_info=True)

        finally:
            result.processing_time = time.time() - start_time

        return result
        
    def _validate_pdf_files(self, pdf_paths: List[str]) -> List[str]:
        """PDF ファイル群の妥当性チェック"""
        valid_files = []

        for pdf_path in pdf_paths:
            try:
                # ファイル存在確認
                if not Path(pdf_path).is_file():
                    logger.warning(f"ファイルが存在しません: {pdf_path}")
                    continue

                # PDF拡張子チェック
                if not pdf_path.lower().endswith('.pdf'):
                    logger.warning(f"PDFファイルではありません: {pdf_path}")
                    continue

                # ファイル読み取り可能性チェック
                if not FileValidator.is_readable_file(pdf_path):
                    logger.warning(f"読み取り不可ファイル: {pdf_path}")
                    continue

                # PDF構造チェック（簡易）
                try:
                    doc = fitz.open(pdf_path)
                    if doc.page_count == 0:
                        logger.warning(f"空のPDFファイル: {pdf_path}")
                        doc.close()
                        continue
                    doc.close()
                except Exception:
                    logger.warning(f"破損したPDFファイル: {pdf_path}")
                    continue

                valid_files.append(pdf_path)

            except Exception as e:
                logger.warning(f"PDFファイル妥当性チェックエラー: {pdf_path} - {str(e)}")
                continue

        return valid_files

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

    def get_pdf_info(self, pdf_path: str) -> dict:
        """PDF情報の取得"""
        try:
            doc = fitz.open(pdf_path)
            info = {
                'pages': doc.page_count,
                'file_size': Path(pdf_path).stat().st_size,
                'file_name': Path(pdf_path).name,
                'encrypted': doc.is_encrypted
            }
            doc.close()
            return info

        except Exception as e:
            logger.error(f"PDF情報取得エラー: {pdf_path} - {str(e)}")
            return {
                'pages': 0,
                'file_size': 0,
                'file_name': Path(pdf_path).name,
                'error': str(e)
            }

    def reorder_files(self, file_list: List[str], old_index: int, new_index: int) -> List[str]:
        """
        ファイルリストの順序変更（要件定義書 F-202）

        Args:
            file_list: 現在のファイルリスト
            old_index: 移動元インデックス
            new_index: 移動先インデックス

        Returns:
            List[str]: 順序変更後のファイルリスト
        """
        if not (0 <= old_index < len(file_list)) or not (0 <= new_index < len(file_list)):
            logger.warning(f"無効なインデックス指定: {old_index} -> {new_index}")
            return file_list

        new_list = file_list.copy()
        item = new_list.pop(old_index)
        new_list.insert(new_index, item)

        logger.info(f"ファイル順序変更: {old_index} -> {new_index}")
        return new_list

    def remove_file_from_list(self, file_list: List[str], index: int) -> List[str]:
        """
        ファイルリストからの削除（要件定義書 F-202）

        Args:
            file_list: 現在のファイルリスト
            index: 削除対象インデックス

        Returns:
            List[str]: 削除後のファイルリスト
        """
        if not (0 <= index < len(file_list)):
            logger.warning(f"無効なインデックス指定: {index}")
            return file_list

        new_list = file_list.copy()
        removed_file = new_list.pop(index)

        logger.info(f"ファイル削除: {Path(removed_file).name}")
        return new_list