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
from ..utils.file_utils import FileValidator, OutputManager


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
        """MS明朝/MSゴシックフォントの登録"""
        try:
            # 複数のフォントパスを試行
            font_paths = [
                ("C:/Windows/Fonts/msmincho.ttc", "MS-Mincho", "MS明朝"),
                ("C:/Windows/Fonts/msgothic.ttc", "MS-Gothic", "MSゴシック"),
                ("C:/Windows/Fonts/meiryo.ttc", "Meiryo", "メイリオ"),
                ("C:/Windows/Fonts/YuGothic.ttf", "Yu-Gothic", "游ゴシック")
            ]

            for font_path, font_name, display_name in font_paths:
                if Path(font_path).exists():
                    try:
                        if font_path.endswith('.ttc'):
                            # TrueType Collection (.ttc) の場合
                            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                        else:
                            # 通常の TrueType (.ttf) の場合
                            pdfmetrics.registerFont(TTFont(font_name, font_path))

                        logger.info(f"{display_name}フォントを登録しました: {font_path}")
                        self.font_name = font_name
                        return
                    except Exception as e:
                        logger.warning(f"{display_name}フォント登録失敗: {e}")
                        continue

            # 全てのフォントで失敗した場合
            raise FileNotFoundError("日本語フォントが見つかりません")

        except Exception as e:
            logger.warning(f"日本語フォント登録エラー: {e}。Courierで代替します")
            self.font_name = "Courier"

    # 表示名 → [(ファイルパス, 登録名, TTC判定), ...] の優先順リスト
    _FONT_MAP = {
        "メイリオ":        [("C:/Windows/Fonts/meiryo.ttc",         "Meiryo",         True)],
        "MSゴシック":      [("C:/Windows/Fonts/msgothic.ttc",        "MS-Gothic",      True)],
        "MS明朝":          [("C:/Windows/Fonts/msmincho.ttc",        "MS-Mincho",      True)],
        "游ゴシック":      [("C:/Windows/Fonts/YuGothic.ttf",        "Yu-Gothic",      False)],
        "BIZ UDPゴシック": [
            ("C:/Windows/Fonts/BIZ-UDPGothicR.ttc", "BIZ-UDP-Gothic", True),   # P版TTC（優先）
            ("C:/Windows/Fonts/BIZ-UDPGothic.ttf",  "BIZ-UDP-Gothic", False),  # P版TTF
            ("C:/Windows/Fonts/BIZ-UDGothicR.ttc",  "BIZ-UD-Gothic",  True),   # 非P版フォールバック
        ],
    }

    def set_user_font(self, display_name: str) -> bool:
        """ユーザーが選択したフォントを登録して self.font_name に設定する。
        候補パスを順に試し、最初に見つかったものを使用する。"""
        if display_name not in self._FONT_MAP:
            return False
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for font_path, font_name, is_ttc in self._FONT_MAP[display_name]:
            if not Path(font_path).exists():
                continue
            try:
                if is_ttc:
                    pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                self.font_name = font_name
                logger.info(f"ユーザー選択フォント設定: {display_name} → {font_name} ({font_path})")
                return True
            except Exception as e:
                logger.debug(f"フォント登録失敗（次候補へ）: {font_name} - {e}")
        logger.warning(f"フォント設定失敗（候補なし）: {display_name}")
        return False

    def combine_pdfs(self, pdf_paths: List[str], output_path: str,
                    add_blank_page: bool = False,
                    add_page_numbers: bool = False,
                    start_page: int = 1,
                    start_number: int = 1,
                    progress_callback: Optional[callable] = None,
                    page_number_binding_compat: bool = False) -> CombineResult:
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

            try:
                for i, pdf_path in enumerate(valid_files):
                    try:
                        if progress_callback:
                            progress = (i + 1) / len(valid_files) * 90 # 結合処理を90%とする
                            progress_callback(f"結合中: {Path(pdf_path).name}", progress)

                        with fitz.open(pdf_path) as reader:
                            if add_blank_page and len(reader) % 2 != 0:
                                with fitz.open() as temp_doc:
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
                                    logger.info(f"白紙ページ追加（回転{rotation}度対応）: {Path(pdf_path).name}")
                            else:
                                writer.insert_pdf(reader)

                        processed_files.append(pdf_path)
                        logger.info(f"PDF追加完了: {Path(pdf_path).name}")

                    except Exception as e:
                        logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                        continue

            finally:
                pass  # try/finallyブロックの終了

            if len(writer) == 0:
                result.error_message = "結合可能なページがありませんでした"
                return result

            # ページ番号挿入
            if add_page_numbers:
                logger.info("ページ番号の挿入を開始")

                # 一度クリーンなPDFを作成してからページ番号を挿入する
                with fitz.open() as clean_doc:
                    clean_doc.insert_pdf(writer)
                    writer.close()
                    writer = fitz.open()
                    writer.insert_pdf(clean_doc)

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
                        # 左綴じ対応モード: ページサイズで挿入位置を切り替え
                        is_a3_landscape = page_width > page_height and page_width > 1100
                        is_left_binding = (
                            (page_width > page_height and page_width <= 1100) or
                            (page_height > page_width and page_height > 1000)
                        )
                        if page_number_binding_compat and is_a3_landscape:
                            # A3横 Z折り（片袖折り）: 右端から75mm
                            # Z折り時は右半分が表面になるため、右寄せで配置
                            x = page_width - (75 * 72 / 25.4) - text_width
                            y = page_height - 28.35
                            rotate_param = 0
                        elif page_number_binding_compat and is_left_binding:
                            # A4横・A3縦 左綴じ対応: 左端中央に90°CW回転で挿入
                            x = 28.35
                            y = (page_height - text_width) / 2
                            rotate_param = -90
                        else:
                            # 通常: 下部中央
                            x = (page_width - text_width) / 2
                            y = page_height - 28.35
                            rotate_param = 0
                    elif original_rotation == 90:
                        # 90度回転: 右側中央が下部になる
                        x = page_width - 28.35  # 右端から10mm
                        y = (page_height - text_width) / 2  # 垂直中央
                        rotate_param = 90
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
                # writer の確実なクリーンアップ
                try:
                    if writer:
                        writer.close()
                except:
                    pass

            # 結果設定
            result.success = True
            result.processed_files = processed_files

            # 元ファイルを「変換元」フォルダへ退避
            for processed_path in processed_files:
                OutputManager.archive_source_file(processed_path)

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
                    with fitz.open(pdf_path) as doc:
                        if doc.page_count == 0:
                            logger.warning(f"空のPDFファイル: {pdf_path}")
                            continue
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
            with fitz.open(pdf_path) as doc:
                info = {
                    'pages': doc.page_count,
                    'file_size': Path(pdf_path).stat().st_size,
                    'file_name': Path(pdf_path).name,
                    'encrypted': doc.is_encrypted
                }
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

    def add_document_numbers(self, pdf_paths: List[str], output_path: str,
                           document_number: str, document_prefix: str = "資料",
                           rename_file: bool = False,
                           a3_portrait_compat: bool = False,
                           insert_all_pages: bool = False,
                           doc_font_size: int = 20,
                           output_dir: str = "",
                           progress_callback: Optional[callable] = None) -> CombineResult:
        """
        PDFファイルに資料NO挿入（各ファイル個別処理・非破壊出力）

        Args:
            pdf_paths: 対象PDFファイルパスのリスト
            output_path: 使用しない（後方互換のために残す）
            document_number: 資料番号（例: "1", "2", "1-1"）
            output_dir: 出力先ディレクトリ（空文字の場合は元ファイルと同じフォルダ）
            progress_callback: 進捗コールバック関数

        Returns:
            CombineResult: 処理結果
        """
        start_time = time.time()
        result = CombineResult(output_path="")

        if not pdf_paths:
            result.error_message = "対象ファイルが指定されていません"
            return result

        if not document_number.strip():
            result.error_message = "資料番号が入力されていません"
            return result

        try:
            valid_files = self._validate_pdf_files(pdf_paths)
            if not valid_files:
                result.error_message = "有効なPDFファイルがありません"
                return result

            processed_files = []
            total_pages = 0

            # 各ファイルを個別に処理
            for i, pdf_path in enumerate(valid_files):
                try:
                    if progress_callback:
                        progress = (i + 1) / len(valid_files) * 90
                        progress_callback(f"処理中: {Path(pdf_path).name}", progress)

                    # 資料NO挿入（非破壊・出力先フォルダに新規作成）
                    effective_output_dir = output_dir if output_dir else str(Path(pdf_path).parent)
                    new_path = self._process_single_pdf_to_dir(pdf_path, document_number, document_prefix, rename_file, a3_portrait_compat, insert_all_pages, doc_font_size, effective_output_dir)

                    if new_path:
                        processed_files.append(new_path)

                        # ページ数をカウント
                        with fitz.open(new_path) as doc:
                            total_pages += len(doc)

                        logger.info(f"資料NO挿入完了: {Path(new_path).name}")
                    else:
                        logger.error(f"資料NO挿入失敗: {Path(pdf_path).name}")

                except Exception as e:
                    logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                    continue

            if not processed_files:
                result.error_message = "処理可能なファイルがありませんでした"
                return result


            # 結果設定
            result.success = True
            result.processed_files = processed_files
            result.total_pages = total_pages
            result.output_path = f"{len(processed_files)}個のファイルに資料NO挿入完了"

            # 進捗完了報告
            if progress_callback:
                progress_callback("資料NO挿入完了", 100)

            logger.info(f"資料NO挿入完了: {len(processed_files)}ファイル, {total_pages}ページ")

        except Exception as e:
            result.error_message = f"資料NO挿入処理エラー: {str(e)}"
            logger.error(f"資料NO挿入エラー: {str(e)}", exc_info=True)

        finally:
            result.processing_time = time.time() - start_time

        return result

    def add_sequential_document_numbers(self, pdf_paths: List[str], output_dir: str = "",
                                      numbering_type: str = "basic", start_number: int = 1,
                                      prefix_number: str = "1", document_prefix: str = "資料",
                                      rename_file: bool = False,
                                      a3_portrait_compat: bool = False,
                                      insert_all_pages: bool = False,
                                      doc_font_size: int = 20,
                                      progress_callback: Optional[callable] = None) -> CombineResult:
        """
        複数PDFファイルに連番で資料NO挿入

        Args:
            pdf_paths: 対象PDFファイルパスのリスト
            output_dir: 出力ディレクトリ（空文字で元フォルダ）
            numbering_type: 連番タイプ ("basic", "start_at", "hyphen")
            start_number: 開始番号（start_atとhyphenで使用）
            prefix_number: ハイフン前の番号（hyphenで使用）
            document_prefix: 文書プレフィックス（デフォルト: "資料"）
            progress_callback: 進捗コールバック関数

        Returns:
            CombineResult: 処理結果

        Examples:
            # 基本連番: 資料1, 資料2, 資料3...
            result = combiner.add_sequential_document_numbers(
                pdf_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
                numbering_type="basic"
            )

            # 任意スタート: 資料3, 資料4, 資料5...
            result = combiner.add_sequential_document_numbers(
                pdf_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
                numbering_type="start_at",
                start_number=3
            )

            # ハイフン付き: 資料1-1, 資料1-2, 資料1-3...
            result = combiner.add_sequential_document_numbers(
                pdf_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
                numbering_type="hyphen",
                prefix_number="1"
            )
        """
        start_time = time.time()
        result = CombineResult(output_path="")

        if not pdf_paths:
            result.error_message = "対象ファイルが指定されていません"
            return result

        if numbering_type not in ["basic", "start_at", "hyphen", "none"]:
            result.error_message = f"無効な連番タイプ: {numbering_type}. 'basic', 'start_at', 'hyphen', 'none'のいずれかを指定してください"
            return result

        try:
            valid_files = self._validate_pdf_files(pdf_paths)
            if not valid_files:
                result.error_message = "有効なPDFファイルがありません"
                return result

            processed_files = []
            total_pages = 0
            failed_files = []

            logger.info(f"連番挿入開始: {len(valid_files)}ファイル, タイプ={numbering_type}")

            # 各ファイルを順次処理
            for i, pdf_path in enumerate(valid_files):
                try:
                    # 進捗報告
                    if progress_callback:
                        progress = (i + 1) / len(valid_files) * 90
                        file_name = Path(pdf_path).name
                        progress_callback(f"処理中 ({i + 1}/{len(valid_files)}): {file_name}", progress)

                    # 連番生成
                    document_number = self._generate_document_number(
                        index=i,
                        numbering_type=numbering_type,
                        start_number=start_number,
                        prefix_number=prefix_number,
                        document_prefix=document_prefix
                    )

                    logger.info(f"ファイル処理開始: {Path(pdf_path).name} → {document_number}")

                    # 資料NO挿入実行（非破壊・出力先フォルダに新規作成）
                    effective_output_dir = output_dir if output_dir else str(Path(pdf_path).parent)
                    new_path = self._process_single_pdf_to_dir(pdf_path, document_number, document_prefix, rename_file, a3_portrait_compat, insert_all_pages, doc_font_size, effective_output_dir)

                    if new_path:
                        processed_files.append(new_path)

                        # ページ数をカウント
                        with fitz.open(new_path) as doc:
                            total_pages += len(doc)

                        logger.info(f"資料NO挿入完了: {Path(new_path).name} → {document_number}")
                    else:
                        failed_files.append((pdf_path, f"処理失敗"))
                        logger.error(f"資料NO挿入失敗: {Path(pdf_path).name}")

                except Exception as e:
                    failed_files.append((pdf_path, str(e)))
                    logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                    continue

            # 結果判定
            if not processed_files:
                result.error_message = "処理可能なファイルがありませんでした"
                if failed_files:
                    error_details = "\n".join([f"・{Path(path).name}: {error}" for path, error in failed_files])
                    result.error_message += f"\n\n失敗詳細:\n{error_details}"
                return result

            # 成功結果設定
            result.success = True
            result.processed_files = processed_files
            result.total_pages = total_pages

            # 出力メッセージ作成
            success_count = len(processed_files)
            total_count = len(valid_files)
            result.output_path = f"連番挿入完了: {success_count}/{total_count}ファイル処理済み"

            if failed_files:
                result.output_path += f" ({len(failed_files)}ファイル失敗)"

            # 進捗完了報告
            if progress_callback:
                progress_callback("連番挿入完了", 100)

            logger.info(f"連番挿入完了: {success_count}ファイル成功, {total_pages}ページ, {len(failed_files)}ファイル失敗")

            # 失敗ファイルがある場合の警告ログ
            if failed_files:
                for path, error in failed_files:
                    logger.warning(f"処理失敗: {Path(path).name} - {error}")

        except Exception as e:
            result.error_message = f"連番挿入処理エラー: {str(e)}"
            logger.error(f"連番挿入エラー: {str(e)}", exc_info=True)

        finally:
            result.processing_time = time.time() - start_time

        return result

    def _generate_document_number(self, index: int, numbering_type: str, start_number: int,
                                prefix_number: str, document_prefix: str) -> str:
        """
        インデックスに基づいて文書番号を生成

        Args:
            index: ファイルインデックス（0から開始）
            numbering_type: 連番タイプ
            start_number: 開始番号
            prefix_number: ハイフン前の番号
            document_prefix: 文書プレフィックス

        Returns:
            str: 生成された文書番号
        """
        if numbering_type == "none":
            # 番号なし: 「資料」「参考」のみ
            return ""

        elif numbering_type == "basic":
            # 基本連番: 資料1, 資料2, 資料3...
            number = index + 1
            return f"{number}"

        elif numbering_type == "start_at":
            # 任意スタート: 資料3, 資料4, 資料5...
            number = start_number + index
            return f"{number}" if number != 0 else ""

        elif numbering_type == "hyphen":
            # ハイフン付き: 資料1-1, 資料1-2, 資料1-3...
            suffix = index + 1
            return f"{prefix_number}-{suffix}"

        else:
            # フォールバック（基本連番）
            number = index + 1
            return f"{number}"

    def _process_single_pdf_to_dir(self, pdf_path: str, document_number: str, document_prefix: str = "資料", rename_file: bool = False, a3_portrait_compat: bool = False, insert_all_pages: bool = False, doc_font_size: int = 20, output_dir: str = "") -> str:
        """
        単一PDFファイルに資料NO挿入（非破壊・出力先フォルダに新規作成）

        Args:
            pdf_path: 対象PDFファイルパス
            document_number: 資料番号
            insert_all_pages: Trueのとき全ページに挿入、FalseのときはP.1のみ
            doc_font_size: 資料番号のフォントサイズ（20 / 18 / 16 / 14 / 12）
            output_dir: 出力先ディレクトリ（空文字の場合は元ファイルと同じフォルダ）

        Returns:
            str: 出力ファイルパス（成功時）、None（失敗時）
        """
        try:
            pdf_path_obj = Path(pdf_path)
            import shutil

            # 出力先ディレクトリの決定
            effective_output_dir = output_dir if output_dir else str(pdf_path_obj.parent)
            Path(effective_output_dir).mkdir(parents=True, exist_ok=True)

            # PDFを開いて資料NO挿入
            with fitz.open(pdf_path) as doc:
                document_text = f"{document_prefix}{document_number}"

                # 処理対象ページインデックスを決定
                if len(doc) == 0:
                    logger.warning("PDFにページが存在しません")
                    return None

                page_indices = range(len(doc)) if insert_all_pages else [0]

                # フォント設定（全ページ共通）
                font_size = doc_font_size
                font_file = self._get_japanese_font_file()

                # テキスト幅計算（日本語テキストベース・全ページ共通）
                japanese_chars = len([c for c in document_text if ord(c) > 127])
                ascii_chars = len(document_text) - japanese_chars
                text_width = japanese_chars * font_size + ascii_chars * (font_size * 0.6)

                for page_idx in page_indices:
                    page = doc[page_idx]

                    # ページ情報を取得
                    original_rotation = page.rotation

                    # 0度にリセットして作業
                    if original_rotation != 0:
                        page.set_rotation(0)

                    page_width = page.rect.width
                    page_height = page.rect.height

                    # 左綴じ対応が必要なページ検出（rotation=0のみ）
                    # A3縦: 高さ>1000pt かつ 縦長
                    is_a3_portrait = (original_rotation == 0
                                      and page_height > 1000
                                      and page_height > page_width)
                    # 横長ページ: rotation=0 の横長（A3横=幅約1190ptを除外するため幅<1100pt）
                    # PowerPoint 16:9(約960pt)・A4横(約842pt)等をすべて対象に含める
                    is_landscape_for_binding = (original_rotation == 0
                                                and page_width > page_height
                                                and page_width < 1100)
                    needs_bottom_right = a3_portrait_compat and (is_a3_portrait or is_landscape_for_binding)

                    # 座標計算（右上配置、回転対応）
                    margin = 28.35  # 10mm
                    if original_rotation == 0:
                        if needs_bottom_right:
                            # 左綴じ対応: 右下 + 90°CW回転テキスト
                            # 回転後の視覚幅=font_size, 視覚高=text_width で座標を配置
                            x = page_width - margin - font_size
                            y = page_height - margin - text_width
                            if is_landscape_for_binding:
                                logger.info(f"横長ページ検出: 左綴じ対応(右下+90°CW) (w={page_width:.0f}, h={page_height:.0f})")
                            else:
                                logger.info(f"A3縦検出: 左綴じ対応(右下+90°CW) (w={page_width:.0f}, h={page_height:.0f})")
                        else:
                            x = page_width - text_width - margin
                            y = margin + font_size
                        rotate_param = 0
                    elif original_rotation == 90:
                        x = margin
                        y = margin + font_size
                        rotate_param = -90
                    elif original_rotation == 180:
                        x = margin + text_width
                        y = page_height - margin
                        rotate_param = 180
                    elif original_rotation == 270:
                        x = page_width - margin
                        y = page_height - margin
                        rotate_param = -90
                    else:
                        x = page_width - text_width - margin
                        y = margin + font_size
                        rotate_param = 0

                    # テキスト挿入（全回転角度でReportLabオーバーレイ使用）
                    try:
                        if original_rotation in [90, 180, 270]:
                            # 回転ページでReportLabオーバーレイを使用
                            logger.info(f"{original_rotation}度回転ページでReportLabオーバーレイを使用")

                            # 回転角度別の座標調整（右上角配置）
                            # 0度状態（未回転）の座標系で、最終的な表示回転を適用した後に
                            # 右上角へ来る位置を狙って算出する
                            if original_rotation == 90:
                                # 90度回転: 0度状態の左上角が表示上の右上角になる
                                overlay_x = margin + font_size
                                overlay_y = margin + text_width
                                logger.info(f"90度回転ページ用オーバーレイ座標（右上角横向き）: x={overlay_x:.1f}, y={overlay_y:.1f}")
                            elif original_rotation == 180:
                                # 180度回転: 0度状態の左下角が表示上の右上角になる
                                overlay_x = margin + text_width
                                overlay_y = page_height - margin - font_size
                                logger.info(f"180度回転ページ用オーバーレイ座標（右上角逆向き）: x={overlay_x:.1f}, y={overlay_y:.1f}")
                            elif original_rotation == 270:
                                # 270度回転: テキストを右上角に縦向き配置
                                overlay_x = page_width - margin - font_size
                                overlay_y = page_height - margin - text_width
                                logger.info(f"270度回転ページ用オーバーレイ座標（右上角縦向き）: x={overlay_x:.1f}, y={overlay_y:.1f}")

                            overlay_data = self._create_japanese_overlay_with_proper_embedding(
                                page_width, page_height, document_text, overlay_x, overlay_y, font_size, original_rotation
                            )

                            if overlay_data:
                                # オーバーレイを適用
                                with fitz.open("pdf", overlay_data) as overlay_pdf:
                                    overlay_page = overlay_pdf[0]
                                    page.show_pdf_page(page.rect, overlay_pdf, 0)
                                logger.info(f"{original_rotation}度回転ページ: ReportLabオーバーレイで挿入成功 {document_text}")

                                # 四角囲いを描画
                                self._draw_simple_rectangle(page, overlay_x, overlay_y, text_width, font_size, original_rotation)
                            else:
                                logger.warning(f"{original_rotation}度回転ページ: ReportLabオーバーレイ作成失敗")
                                # フォールバック: 基本フォント
                                page.insert_text(
                                    (overlay_x, overlay_y),
                                    document_text,
                                    fontname="cour",
                                    fontsize=font_size,
                                    color=(0, 0, 0)
                                )
                                logger.warning(f"{original_rotation}度回転ページ: Courierフォントでフォールバック")

                        else:
                            # 通常ページ（0度）の場合はReportLabオーバーレイ
                            lb_text_rotate = -90 if needs_bottom_right else 0
                            overlay_data = self._create_japanese_overlay_with_proper_embedding(
                                page_width, page_height, document_text, x, y, font_size, rotate_param,
                                text_rotate=lb_text_rotate
                            )

                            if overlay_data:
                                # オーバーレイを適用
                                with fitz.open("pdf", overlay_data) as overlay_doc:
                                    page.show_pdf_page(page.rect, overlay_doc, 0)
                                logger.info(f"ReportLab確実日本語オーバーレイで挿入: {document_text}")
                            else:
                                # ReportLab失敗時はひらがなでフォールバック
                                kana_text = document_text.replace("資料", "シリョウ")
                                page.insert_text(
                                    (x, y),
                                    kana_text,
                                    fontname="cour",
                                    fontsize=font_size,
                                    color=(0, 0, 0),
                                    rotate=rotate_param
                                )
                                logger.warning(f"ReportLab失敗、ひらがなで挿入: {kana_text}")

                            # 四角囲いの描画（PyMuPDF）
                            if needs_bottom_right:
                                # 90°CW回転テキスト: 幅=font_size, 高さ=text_width
                                try:
                                    rp = 4
                                    rect = fitz.Rect(x - rp, y - rp,
                                                     x + font_size + rp, y + text_width + rp)
                                    page.draw_rect(rect, color=(0, 0, 0), width=1.5)
                                except Exception as re:
                                    logger.debug(f"左綴じ矩形描画エラー: {re}")
                            else:
                                self._draw_simple_rectangle(page, x, y, text_width, font_size, rotate_param)

                    except Exception as e:
                        logger.error(f"P.{page_idx + 1} テキスト挿入エラー: {e}")
                        # エラー時の最終フォールバック
                        try:
                            fallback_text = "Doc " + document_text.replace("資料", "")
                            page.insert_text((x, y), fallback_text, fontsize=font_size, color=(0, 0, 0))
                            logger.warning(f"最終フォールバック: {fallback_text}")
                        except Exception as fallback_error:
                            logger.error(f"最終フォールバックも失敗: {fallback_error}")

                    # 回転を元に戻す
                    if original_rotation != 0:
                        page.set_rotation(original_rotation)

                    logger.info(f"P.{page_idx + 1} に資料NO挿入完了: {document_text}")

                logger.info(f"資料NO挿入完了 ({len(list(page_indices))}ページ): {document_text}")

                # ファイル名の先頭に資料番号を付加（オプション）
                if rename_file:
                    fw_number = self._to_fullwidth_number(document_number)
                    label = f"【{document_prefix}{fw_number}】"
                    output_filename = label + pdf_path_obj.name
                else:
                    output_filename = pdf_path_obj.name

                # 出力先パスを決定（同名ファイルがあれば連番付与）
                output_file_path = OutputManager.get_unique_output_path(effective_output_dir, output_filename)

                # 一時ファイルに保存してから出力先へ移動（フリーズ対策）
                temp_path = pdf_path + ".tmp"
                doc.save(temp_path, garbage=4, deflate=True, clean=True)

            # 出力先に移動（with文外で実行）
            shutil.move(temp_path, output_file_path)

            # 元ファイルを「変換元」フォルダへ退避
            OutputManager.archive_source_file(pdf_path)

            logger.info(f"資料NO挿入完了: {pdf_path_obj.name} → {output_file_path}")
            return output_file_path

        except Exception as e:
            logger.error(f"単一PDF処理エラー ({pdf_path}): {e}")
            return None

    @staticmethod
    def _to_fullwidth_number(text: str) -> str:
        """数字とハイフンを全角に変換"""
        result = []
        for c in text:
            if '0' <= c <= '9':
                result.append(chr(ord('０') + ord(c) - ord('0')))
            elif c == '-':
                result.append('－')
            else:
                result.append(c)
        return ''.join(result)

    def _create_japanese_overlay_with_proper_embedding(self, page_width: float, page_height: float,
                                                     document_text: str, x: float, y: float,
                                                     font_size: float, rotate_param: int,
                                                     text_rotate: int = 0) -> bytes:
        """
        確実な日本語フォント埋め込みでReportLabオーバーレイを作成

        Args:
            page_width: ページ幅
            page_height: ページ高さ
            document_text: 挿入するテキスト
            x: x座標
            y: y座標
            font_size: フォントサイズ
            rotate_param: 回転角度

        Returns:
            bytes: 確実な日本語PDFオーバーレイ
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io

            # メモリ上にPDFを作成
            packet = io.BytesIO()

            # ReportLabキャンバス
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # 日本語フォントを確実に登録（self.font_name優先、TTF/TTC両対応）
            font_registered = False
            _all_fonts = [
                ("C:/Windows/Fonts/meiryo.ttc",         "Meiryo",         True),
                ("C:/Windows/Fonts/msgothic.ttc",        "MS-Gothic",      True),
                ("C:/Windows/Fonts/msmincho.ttc",        "MS-Mincho",      True),
                ("C:/Windows/Fonts/YuGothic.ttf",        "Yu-Gothic",      False),
                ("C:/Windows/Fonts/BIZ-UDPGothicR.ttc", "BIZ-UDP-Gothic", True),
                ("C:/Windows/Fonts/BIZ-UDPGothic.ttf",  "BIZ-UDP-Gothic", False),
                ("C:/Windows/Fonts/BIZ-UDGothicR.ttc",  "BIZ-UD-Gothic",  True),
            ]
            preferred = [(p, n, t) for p, n, t in _all_fonts if n == self.font_name]
            fallbacks = [(p, n, t) for p, n, t in _all_fonts if n != self.font_name]
            japanese_fonts = preferred + fallbacks

            for font_path, font_name, is_ttc in japanese_fonts:
                if Path(font_path).exists() and not font_registered:
                    try:
                        if is_ttc:
                            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                        else:
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                        c.setFont(font_name, font_size)
                        font_registered = True
                        logger.info(f"ReportLab日本語フォント登録成功: {font_name}")
                        break
                    except Exception as font_error:
                        if is_ttc:
                            try:
                                bold_name = f"{font_name}-Bold"
                                pdfmetrics.registerFont(TTFont(bold_name, font_path, subfontIndex=1))
                                c.setFont(bold_name, font_size)
                                font_registered = True
                                logger.info(f"ReportLab日本語フォント登録成功（Bold）: {bold_name}")
                                break
                            except Exception as font_error2:
                                logger.debug(f"フォント登録失敗: {font_name} - {font_error2}")
                        else:
                            logger.debug(f"フォント登録失敗: {font_name} - {font_error}")

            if not font_registered:
                logger.warning("ReportLab日本語フォント登録失敗")
                return None

            # ページ回転に応じたテキスト描画
            if rotate_param == 90:
                # 90度回転ページの場合、表示時に90度回転されて正立するようテキストを90度回転させて描画
                draw_x = x
                draw_y = page_height - y  # Y座標を反転

                c.saveState()
                c.translate(draw_x, draw_y)
                c.rotate(90)
                c.drawString(0, 0, document_text)
                c.restoreState()

                logger.info(f"90度回転ページ: ReportLab座標({draw_x:.1f}, {draw_y:.1f})に90度回転テキスト描画")
            elif rotate_param == 180:
                # 180度回転ページの場合、テキストを180度回転
                draw_x = x
                draw_y = page_height - y  # Y座標を反転

                # テキストを180度回転させて描画
                c.saveState()
                c.translate(draw_x, draw_y)  # 描画位置に移動
                c.rotate(180)  # 180度回転
                c.drawString(0, 0, document_text)  # 回転後の原点に描画
                c.restoreState()

                logger.info(f"180度回転ページ: ReportLab座標({draw_x:.1f}, {draw_y:.1f})に180度回転テキスト描画")
            elif rotate_param == 270:
                # 270度回転ページの場合、テキストをマイナス90度回転
                draw_x = x
                draw_y = page_height - y  # Y座標を反転

                # テキストをマイナス90度回転させて描画
                c.saveState()
                c.translate(draw_x, draw_y)  # 描画位置に移動
                c.rotate(-90)  # マイナス90度回転
                c.drawString(0, 0, document_text)  # 回転後の原点に描画
                c.restoreState()

                logger.info(f"270度回転ページ: ReportLab座標({draw_x:.1f}, {draw_y:.1f})にマイナス90度回転テキスト描画")
            else:
                # 通常ページ（0度）の場合
                draw_x = x
                draw_y = page_height - y  # fitz→ReportLab座標変換
                if text_rotate == -90:
                    # 左綴じ対応: 90°CW回転テキスト
                    c.saveState()
                    c.translate(draw_x, draw_y)
                    c.rotate(-90)
                    c.drawString(0, 0, document_text)
                    c.restoreState()
                    logger.info(f"左綴じ対応90°CW回転テキスト: RL座標({draw_x:.1f}, {draw_y:.1f})")
                else:
                    c.drawString(draw_x, draw_y, document_text)

            # PDFを完成
            c.showPage()
            c.save()

            # バイナリデータを取得
            packet.seek(0)
            data = packet.getvalue()
            packet.close()

            return data

        except Exception as e:
            logger.error(f"ReportLab確実日本語オーバーレイ作成エラー: {e}")
            return None

    def _create_minimal_japanese_overlay(self, page_width: float, page_height: float,
                                       document_text: str, x: float, y: float, font_size: float) -> bytes:
        """
        最小限のReportLabオーバーレイ（日本語表示専用）

        Args:
            page_width: ページ幅
            page_height: ページ高さ
            document_text: 挿入するテキスト
            x: x座標
            y: y座標
            font_size: フォントサイズ

        Returns:
            bytes: 最小限のPDFオーバーレイ
        """
        try:
            # メモリ上にPDFを作成
            packet = io.BytesIO()

            # ReportLabキャンバス（最小構成）
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # フォント設定
            try:
                c.setFont(self.font_name, font_size)
            except:
                c.setFont("Helvetica", font_size)

            # 日本語テキストの適切なエンコーディング
            # UTF-8エンコーディングを明示的に処理
            try:
                # テキストが既にUnicodeかチェック
                if isinstance(document_text, str):
                    encoded_text = document_text
                else:
                    encoded_text = document_text.decode('utf-8') if isinstance(document_text, bytes) else str(document_text)

                # ReportLabで日本語テキストを描画
                c.drawString(x, y, encoded_text)

            except Exception as text_error:
                logger.warning(f"日本語テキスト描画エラー、代替手段を使用: {text_error}")
                # 代替として英語版を描画
                fallback_text = f"Doc{document_text.replace('資料', '')}"
                c.drawString(x, y, fallback_text)

            # PDFを完成（最小限）
            c.showPage()
            c.save()

            # バイナリデータを取得
            packet.seek(0)
            data = packet.getvalue()
            packet.close()

            return data

        except Exception as e:
            logger.error(f"最小オーバーレイ作成エラー: {e}")
            return b""

    def _draw_simple_rectangle(self, page, x: float, y: float, text_width: float,
                             font_size: float, rotate_param: int) -> None:
        """
        シンプルな四角囲い描画（フリーズ対策版）

        Args:
            page: PDF ページオブジェクト
            x: テキストのx座標
            y: テキストのy座標
            text_width: テキスト幅
            font_size: フォントサイズ
            rotate_param: 回転パラメータ
        """
        try:
            margin = 4
            text_height = font_size * 0.8

            # 回転に応じた四角形の座標計算（最適化版）
            if rotate_param == 0:
                # 0度：通常の四角囲い
                rect = fitz.Rect(x - margin, y - text_height - margin,
                               x + text_width + margin, y + margin)
            elif rotate_param == 90:
                # 90度回転：縦向きテキスト用（幅と高さを交換）
                rect = fitz.Rect(x - font_size - margin, y - text_width - margin,
                               x + margin, y + margin)
            elif rotate_param == 180:
                # 180度回転：逆向きテキスト用
                rect = fitz.Rect(x - text_width - margin, y - margin,
                               x + margin, y + text_height + margin)
            elif rotate_param == 270:
                # 270度回転：縦向きテキスト用（幅と高さを交換）
                x_adjust = 17  # 位置調整
                rect = fitz.Rect(x - text_height - margin + x_adjust, y - margin,
                               x + margin + x_adjust, y + text_width + margin)
            elif rotate_param == -90:
                # PyMuPDF用のマイナス90度
                rect = fitz.Rect(x - margin, y - text_width - margin,
                               x + text_height + margin, y + margin)
            else:
                # デフォルト
                rect = fitz.Rect(x - margin, y - text_height - margin,
                               x + text_width + margin, y + margin)

            # 四角形を描画（シンプルに）
            page.draw_rect(rect, color=(0, 0, 0), width=1.5)
            logger.info(f"四角囲い描画完了: {rect}")

        except Exception as e:
            logger.error(f"四角囲い描画エラー: {e}")

    def _create_optimized_text_overlay(self, page_width: float, page_height: float,
                                     document_text: str, rotation: int) -> bytes:
        """
        ReportLabを使用した最適化版オーバーレイ作成（フリーズ対策）

        Args:
            page_width: ページ幅
            page_height: ページ高さ
            document_text: 挿入するテキスト
            rotation: ページの回転角度

        Returns:
            bytes: 最適化されたPDFオーバーレイのバイナリデータ
        """
        try:
            # メモリ上にPDFを作成
            packet = io.BytesIO()

            # ReportLabキャンバスを作成（最小サイズで最適化）
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # フォント設定（最適化）
            font_size = 20

            try:
                c.setFont(self.font_name, font_size)
            except:
                c.setFont("Helvetica", font_size)

            # テキスト幅を高速計算
            text_width = c.stringWidth(document_text, self.font_name, font_size)

            # 座標計算（簡略化）
            margin = 10 * 2.83465  # 10mmをポイントに変換
            padding = 4

            if rotation == 0:
                x = page_width - text_width - margin
                y = page_height - margin - font_size
            elif rotation == 90:
                x = margin
                y = page_height - margin - font_size
            elif rotation == 180:
                x = margin + text_width
                y = margin + font_size
            elif rotation == 270:
                x = page_width - margin
                y = margin + font_size
            else:
                x = page_width - text_width - margin
                y = page_height - margin - font_size

            # テキスト描画（シンプルに）
            c.drawString(x, y, document_text)

            # 四角囲い描画（最適化）
            text_height = font_size * 0.8
            rect_x = x - padding
            rect_y = y - padding
            rect_width = text_width + (padding * 2)
            rect_height = text_height + (padding * 2)

            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(1.5)
            c.rect(rect_x, rect_y, rect_width, rect_height, fill=0, stroke=1)

            # PDFを完成（最適化オプション）
            c.showPage()
            c.save()

            # バイナリデータを取得
            packet.seek(0)
            data = packet.getvalue()
            packet.close()

            return data

        except Exception as e:
            logger.error(f"最適化オーバーレイ作成エラー: {e}")
            return b""

    def _create_text_overlay_with_reportlab(self, page_width: float, page_height: float,
                                          document_text: str, rotation: int) -> bytes:
        """
        ReportLabを使用して日本語テキストのPDFオーバーレイを作成

        Args:
            page_width: ページ幅
            page_height: ページ高さ
            document_text: 挿入するテキスト（例："資料1-1"）
            rotation: ページの回転角度（0, 90, 180, 270）

        Returns:
            bytes: PDFオーバーレイのバイナリデータ
        """
        try:
            # メモリ上にPDFを作成
            packet = io.BytesIO()

            # ReportLabキャンバスを作成（ポイント単位）
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # フォント設定
            font_size = 20

            # 日本語フォントを使用（事前に登録済み）
            try:
                c.setFont(self.font_name, font_size)
                logger.info(f"ReportLabで{self.font_name}フォントを使用")
            except Exception as e:
                logger.warning(f"フォント設定エラー: {e}。デフォルトフォントを使用")
                c.setFont("Helvetica", font_size)

            # テキスト幅を計算（ReportLabのstringWidth関数を使用）
            text_width = c.stringWidth(document_text, self.font_name, font_size)

            # 余白とパディング
            margin = 10  # mm
            margin_points = margin * mm  # ポイントに変換
            padding = 4  # ポイント

            # 回転に応じた座標計算（右上に配置）
            if rotation == 0:
                # 0度: 通常の右上
                x = page_width - text_width - margin_points
                y = page_height - margin_points - font_size
                text_rotation = 0
            elif rotation == 90:
                # 90度回転: 左上が視覚的な右上になる
                x = margin_points
                y = page_height - margin_points - font_size
                text_rotation = 0  # テキスト自体は回転させない
            elif rotation == 180:
                # 180度回転: 左下が視覚的な右上になる
                x = margin_points + text_width
                y = margin_points + font_size
                text_rotation = 180
            elif rotation == 270:
                # 270度回転: 右下が視覚的な右上になる
                x = page_width - margin_points
                y = margin_points + font_size
                text_rotation = 90
            else:
                # デフォルト（0度と同じ）
                x = page_width - text_width - margin_points
                y = page_height - margin_points - font_size
                text_rotation = 0

            # テキストを描画
            c.saveState()
            if text_rotation != 0:
                c.translate(x, y)
                c.rotate(text_rotation)
                if text_rotation == 180:
                    c.drawString(-text_width, 0, document_text)
                elif text_rotation == 90:
                    c.drawString(0, -text_width, document_text)
                else:
                    c.drawString(0, 0, document_text)
            else:
                c.drawString(x, y, document_text)
            c.restoreState()

            # 四角囲いを描画
            text_height = font_size * 0.8

            # 回転に応じた四角形の座標計算
            if rotation == 0:
                rect_x = x - padding
                rect_y = y - padding
                rect_width = text_width + (padding * 2)
                rect_height = text_height + (padding * 2)
            elif rotation == 90:
                rect_x = x - padding
                rect_y = y - padding
                rect_width = text_width + (padding * 2)
                rect_height = text_height + (padding * 2)
            elif rotation == 180:
                rect_x = x - text_width - padding
                rect_y = y - text_height - padding
                rect_width = text_width + (padding * 2)
                rect_height = text_height + (padding * 2)
            elif rotation == 270:
                rect_x = x - text_height - padding
                rect_y = y - text_width - padding
                rect_width = text_height + (padding * 2)
                rect_height = text_width + (padding * 2)
            else:
                rect_x = x - padding
                rect_y = y - padding
                rect_width = text_width + (padding * 2)
                rect_height = text_height + (padding * 2)

            # 四角形を描画（黒い枠線、塗りつぶしなし）
            c.setStrokeColorRGB(0, 0, 0)  # 黒色
            c.setLineWidth(1.5)  # 線の太さ
            c.rect(rect_x, rect_y, rect_width, rect_height, fill=0, stroke=1)

            # PDFを完成させる
            c.showPage()
            c.save()

            # バイナリデータを取得
            packet.seek(0)
            return packet.getvalue()

        except Exception as e:
            logger.error(f"ReportLabオーバーレイ作成エラー: {e}")
            return b""

    def _get_japanese_font_file(self) -> Optional[str]:
        """
        日本語フォントファイルを取得

        Returns:
            Optional[str]: 使用可能な日本語フォントファイルのパス
        """
        # Windows標準の日本語フォントファイルのパス
        font_paths = [
            "C:/Windows/Fonts/msgothic.ttc",    # MSゴシック
            "C:/Windows/Fonts/msmincho.ttc",    # MS明朝
            "C:/Windows/Fonts/meiryo.ttc",      # メイリオ
            "C:/Windows/Fonts/YuGothic.ttf",    # 游ゴシック
            "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
        ]

        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    # フォントファイルが読み取り可能かテスト
                    with open(font_path, 'rb') as f:
                        f.read(100)  # 最初の100バイトを読んでテスト
                    logger.info(f"日本語フォント見つかりました: {font_path}")
                    return font_path
            except Exception as e:
                logger.info(f"フォントファイルテスト失敗: {font_path} - {e}")
                continue

        logger.warning("日本語フォントファイルが見つかりませんでした")
        return None

    def _draw_rectangle_around_text(self, page, x: float, y: float, text_width: float,
                                   font_size: float, rotate_param: int) -> None:
        """
        テキスト周りに四角囲いを描画

        Args:
            page: PyMuPDFページオブジェクト
            x: テキストX座標
            y: テキストY座標
            text_width: テキスト幅
            font_size: フォントサイズ
            rotate_param: 回転パラメータ
        """
        try:
            # 余白設定
            margin = 3  # 適切な余白

            # テキストの実際の高さ（フォントサイズより少し小さい）
            text_height = font_size * 0.75

            # 四角形の座標計算（回転を考慮）
            if rotate_param == 0:
                # 通常（0度）
                rect = fitz.Rect(x - margin, y - margin,
                               x + text_width + margin, y + text_height + margin)
            elif rotate_param == 90:
                # 90度回転
                rect = fitz.Rect(x - text_height - margin, y - margin,
                               x + margin, y + text_width + margin)
            elif rotate_param == 180:
                # 180度回転
                rect = fitz.Rect(x - text_width - margin, y - text_height - margin,
                               x + margin, y + margin)
            elif rotate_param == -90:
                # -90度回転（270度PDFで使用）
                rect = fitz.Rect(x - margin, y - text_width - margin,
                               x + text_height + margin, y + margin)
            else:
                # デフォルト
                rect = fitz.Rect(x - margin, y - margin,
                               x + text_width + margin, y + text_height + margin)

            # 四角形を描画（黒い線、塗りつぶしなし）
            page.draw_rect(rect, color=(0, 0, 0), width=1)

            logger.info(f"四角囲い描画完了: {rect}")

        except Exception as e:
            logger.error(f"四角囲い描画エラー: {e}")
            # エラーが発生してもテキスト挿入は続行