"""
PDF結合コアモジュール
要件定義書 4.3 PDF結合モード機能の実装
"""

import os
from pathlib import Path
from typing import List, Optional
import time

try:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.errors import PdfReadError
except ImportError:
    try:
        from PyPDF4 import PdfFileReader as PdfReader, PdfFileWriter as PdfWriter
        from PyPDF4.utils import PdfReadError
    except ImportError:
        print("PDF処理ライブラリ未インストール: PyPDF2またはPyPDF4が必要です")

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


class PDFCombiner:
    """PDF結合メインクラス"""
    
    def __init__(self):
        logger.info("PDFコンバイナー初期化完了")
    
    def combine_pdfs(self, pdf_paths: List[str], output_path: str, 
                    progress_callback: Optional[callable] = None) -> CombineResult:
        """
        複数PDFファイルの結合（要件定義書 F-204）
        
        Args:
            pdf_paths: 結合対象PDFファイルパスのリスト（順序通り）
            output_path: 出力先PDFパス
            progress_callback: 進捗コールバック関数
            
        Returns:
            CombineResult: 結合結果
        """
        start_time = time.time()
        result = CombineResult(output_path=output_path)
        
        if not pdf_paths:
            result.error_message = "結合対象ファイルが指定されていません"
            return result
        
        try:
            # ファイル妥当性チェック
            valid_files = self._validate_pdf_files(pdf_paths)
            if not valid_files:
                result.error_message = "有効なPDFファイルがありません"
                return result
            
            # PDF結合実行
            writer = PdfWriter()
            total_pages = 0
            processed_files = []
            
            for i, pdf_path in enumerate(valid_files):
                try:
                    # 進捗報告
                    if progress_callback:
                        progress = (i + 1) / len(valid_files) * 100
                        progress_callback(f"処理中: {Path(pdf_path).name}", progress)
                    
                    # PDFファイル読み込み
                    reader = PdfReader(pdf_path)
                    pages_count = len(reader.pages)
                    
                    # 全ページを結合用PDFに追加
                    for page_num in range(pages_count):
                        page = reader.pages[page_num]
                        writer.add_page(page)
                    
                    total_pages += pages_count
                    processed_files.append(pdf_path)
                    
                    logger.info(f"PDF追加完了: {Path(pdf_path).name} ({pages_count}ページ)")
                
                except PdfReadError as e:
                    logger.error(f"PDF読み取りエラー: {pdf_path} - {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"PDF処理エラー: {pdf_path} - {str(e)}")
                    continue
            
            if total_pages == 0:
                result.error_message = "結合可能なページがありませんでした"
                return result
            
            # 結合PDFファイル保存
            self._ensure_output_directory(output_path)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            # 結果設定
            result.success = True
            result.processed_files = processed_files
            result.total_pages = total_pages
            
            # 進捗完了報告
            if progress_callback:
                progress_callback("結合完了", 100)
            
            logger.info(f"PDF結合完了: {len(processed_files)}ファイル, {total_pages}ページ -> {Path(output_path).name}")
        
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
                    with open(pdf_path, 'rb') as f:
                        reader = PdfReader(f)
                        page_count = len(reader.pages)
                        if page_count == 0:
                            logger.warning(f"空のPDFファイル: {pdf_path}")
                            continue
                except PdfReadError:
                    logger.warning(f"破損したPDFファイル: {pdf_path}")
                    continue
                
                valid_files.append(pdf_path)
                
            except Exception as e:
                logger.warning(f"PDFファイル妥当性チェックエラー: {pdf_path} - {str(e)}")
                continue
        
        return valid_files
    
    def _ensure_output_directory(self, output_path: str) -> None:
        """出力ディレクトリの確保"""
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"出力ディレクトリ作成: {output_dir}")
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """PDF情報の取得"""
        try:
            reader = PdfReader(pdf_path)
            info = {
                'pages': len(reader.pages),
                'file_size': Path(pdf_path).stat().st_size,
                'file_name': Path(pdf_path).name,
                'encrypted': reader.is_encrypted if hasattr(reader, 'is_encrypted') else False
            }
            
            # メタデータがある場合は追加
            if hasattr(reader, 'metadata') and reader.metadata:
                metadata = reader.metadata
                info.update({
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                })
            
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