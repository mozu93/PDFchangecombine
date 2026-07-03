"""
PDF変換コアモジュール
要件定義書 4.2 PDF変換モード機能の実装
"""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from ..utils.logger import logger
from ..utils.file_utils import FileValidator, OutputManager, is_cloud_sync_path
from ..config import MAX_CONVERSION_TIME_SECONDS, MAX_CONCURRENT_FILES
from .office_converter import OfficeConverter
from .image_converter import ImageConverter


class ConversionResult:
    """変換結果を保持するクラス"""
    
    def __init__(self, source_path: str, target_paths: List[str] = None, 
                 success: bool = False, error_message: str = ""):
        self.source_path = source_path
        self.target_paths = target_paths if target_paths is not None else []
        self.success = success
        self.error_message = error_message
        self.processing_time = 0.0


import fitz

class PDFConverter:
    """PDF変換メインクラス"""
    
    def __init__(self):
        self.office_converter = OfficeConverter()
        self.image_converter = ImageConverter()
        self.executor = ThreadPoolExecutor(max_workers=4)  # 同時実行数制限
        
        logger.info("PDFコンバーター初期化完了")
    
    async def convert_files_async(self, file_paths: List[str], split_sheets: bool = False, output_dir: str = "") -> List[ConversionResult]:
        """
        複数ファイルの非同期変換（要件定義書 F-103）

        Args:
            file_paths: 変換対象ファイルパスのリスト
            split_sheets: Excelシートを分割するかどうか
            output_dir: 出力先ディレクトリ（空文字の場合は各ファイルと同じフォルダ内の「変換済」へ）

        Returns:
            List[ConversionResult]: 変換結果のリスト
        """
        if len(file_paths) > MAX_CONCURRENT_FILES:
            logger.warning(f"同時変換ファイル数が上限を超過: {len(file_paths)}/{MAX_CONCURRENT_FILES}")

        start_time = time.time()
        results = []

        # セマフォで同時実行数制御
        semaphore = asyncio.Semaphore(4)

        # 非同期タスクを作成
        tasks = []
        for file_path in file_paths:
            task = self._convert_single_file_with_semaphore(semaphore, file_path, split_sheets, output_dir)
            tasks.append(task)
        
        # 全てのタスクを実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外処理
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = ConversionResult(
                    source_path=file_paths[i],
                    success=False,
                    error_message=f"変換エラー: {str(result)}"
                )
                final_results.append(error_result)
                logger.error(f"ファイル変換エラー: {file_paths[i]} - {str(result)}")
            else:
                final_results.append(result)
        
        # 統計情報のログ記録
        total_time = time.time() - start_time
        successful_count = sum(1 for r in final_results if r.success)
        failed_count = len(final_results) - successful_count
        
        logger.log_conversion_stats(
            total_files=len(file_paths),
            successful=successful_count,
            failed=failed_count,
            processing_time=total_time
        )
        
        return final_results
    
    async def _convert_single_file_with_semaphore(self, semaphore: asyncio.Semaphore,
                                                 file_path: str, split_sheets: bool = False,
                                                 output_dir: str = "") -> ConversionResult:
        """セマフォ付き単一ファイル変換"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._convert_single_file, file_path, split_sheets, output_dir
            )

    def _convert_single_file(self, file_path: str, split_sheets: bool = False, output_dir: str = "") -> ConversionResult:
        """
        単一ファイルの変換処理（要件定義書 F-103）

        Args:
            file_path: 変換対象ファイルパス
            split_sheets: Excelシートを分割するかどうか
            output_dir: 出力先ディレクトリ（空文字の場合は「変換済」フォルダ）

        Returns:
            ConversionResult: 変換結果
        """
        start_time = time.time()
        result = ConversionResult(source_path=file_path)

        try:
            # ファイル妥当性チェック
            if not self._validate_file(file_path):
                result.error_message = "ファイル妥当性チェック失敗"
                return result

            # 出力ファイルパス生成
            output_path = OutputManager.get_output_file_path(file_path, output_dir)
            
            # ファイル種別に応じて変換実行
            file_type = FileValidator.get_file_type(file_path)
            
            generated_files = []
            if file_type in ['word', 'excel', 'powerpoint']:
                generated_files = self.office_converter.convert_to_pdf(file_path, output_path, split_sheets)
            elif file_type == 'image':
                if self.image_converter.convert_to_pdf(file_path, output_path):
                    generated_files = [output_path]
            elif file_type == 'pdf':
                # PDFファイルは変換済フォルダにコピー
                if self._copy_pdf_file(file_path, output_path):
                    generated_files = [output_path]
            else:
                result.error_message = f"未対応のファイル種別: {file_type}"
                return result

            result.target_paths = generated_files
            success = bool(generated_files)

            if success and file_type != 'pdf':
                empty_files = []
                for gen_file in generated_files:
                    # クラウド同期パスの場合はローカル一時フォルダを使用してロック競合を回避
                    if is_cloud_sync_path(gen_file):
                        temp_path = os.path.join(
                            tempfile.gettempdir(),
                            Path(gen_file).stem + "_repair.tmp"
                        )
                        logger.info(f"クラウドパス検出: ローカル一時フォルダ経由で圧縮: {Path(gen_file).name}")
                    else:
                        temp_path = gen_file + ".tmp"
                    try:
                        with fitz.open(gen_file) as doc:
                            if doc.page_count == 0:
                                logger.warning(f"空のPDF（印刷対象なし）のためスキップ: {Path(gen_file).name}")
                                empty_files.append(gen_file)
                                continue
                            logger.info(f"PDF修復処理開始: {gen_file}")
                            doc.save(temp_path, garbage=4, deflate=True, clean=True)
                        os.replace(temp_path, gen_file)
                        logger.info(f"PDF修復処理完了: {gen_file}")
                    except Exception as e:
                        logger.warning(f"PDF修復処理に失敗: {gen_file} - {e}")
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass
                # 空のPDFをファイルリストと出力から除外
                for f in empty_files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                for f in empty_files:
                    if f in generated_files:
                        generated_files.remove(f)
            
            result.success = success

            if success:
                OutputManager.archive_source_file(file_path)
                logger.log_file_operation("変換", file_path, True)
            else:
                result.error_message = "変換処理が失敗しました"
                logger.log_file_operation("変換", file_path, False)
        
        except Exception as e:
            result.error_message = f"変換中にエラーが発生: {str(e)}"
            logger.error(f"ファイル変換エラー: {file_path} - {str(e)}", exc_info=True)
        
        finally:
            result.processing_time = time.time() - start_time
            
            # 性能要件チェック（要件定義書 5.3）
            if result.processing_time > MAX_CONVERSION_TIME_SECONDS:
                logger.warning(
                    f"変換時間超過: {Path(file_path).name} - "
                    f"{result.processing_time:.2f}秒 (要件: {MAX_CONVERSION_TIME_SECONDS}秒以内)"
                )
        
        return result
    
    def _validate_file(self, file_path: str) -> bool:
        """ファイル妥当性チェック"""
        if not FileValidator.is_readable_file(file_path):
            logger.warning(f"読み取り不可ファイル: {file_path}")
            return False
        
        if not FileValidator.is_supported_file(file_path):
            logger.warning(f"非対応ファイル形式: {file_path}")
            return False
        
        if not FileValidator.is_valid_file_size(file_path):
            logger.warning(f"ファイルサイズ超過: {file_path}")
            return False
        
        return True
    
    def get_conversion_statistics(self, results: List[ConversionResult]) -> Dict[str, Any]:
        """変換結果の統計情報を取得"""
        total_files = len(results)
        successful_files = [r for r in results if r.success]
        failed_files = [r for r in results if not r.success]
        
        total_time = sum(r.processing_time for r in results)
        avg_time = total_time / total_files if total_files > 0 else 0
        
        return {
            'total_files': total_files,
            'successful_count': len(successful_files),
            'failed_count': len(failed_files),
            'success_rate': len(successful_files) / total_files * 100 if total_files > 0 else 0,
            'total_processing_time': total_time,
            'average_processing_time': avg_time,
            'successful_files': [path for r in successful_files for path in r.target_paths],
            'failed_files': [(r.source_path, r.error_message) for r in failed_files]
        }
    
    def _copy_pdf_file(self, input_path: str, output_path: str) -> bool:
        """PDFファイルを変換済フォルダにコピー"""
        try:
            import shutil
            
            # 入力ファイル存在確認
            if not os.path.exists(input_path):
                logger.error(f"コピー元PDFファイルが存在しません: {input_path}")
                return False
            
            # 出力ディレクトリの存在確認・作成
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # PDFファイルをコピー
            shutil.copy2(input_path, output_path)
            logger.info(f"PDFファイルコピー成功: {Path(input_path).name} → {output_path}")
            
            return True
            
        except PermissionError as e:
            logger.error(f"PDFファイルコピーでアクセス権限エラー: {input_path} - {e}")
            return False
        except OSError as e:
            logger.error(f"PDFファイルコピーでシステムエラー: {input_path} - {e}")
            return False
        except Exception as e:
            logger.error(f"PDFファイルコピーで予期しないエラー: {input_path} - {e}")
            return False
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("PDFコンバーター リソースクリーンアップ完了")