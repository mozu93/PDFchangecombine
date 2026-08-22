"""
Officeファイル変換モジュール
要件定義書 F-102, F-103 Office文書のPDF変換実装
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple
import time

# Microsoft Office COM API用ライブラリ（Windows専用）
# フォールバック機能は削除し、高品質なCOM APIのみを使用

from ..utils.logger import logger
from ..utils.file_utils import is_cloud_sync_path

# RPC_E_CALL_REJECTED: COMサーバービジー時のエラーコード
_RPC_E_CALL_REJECTED = -2147418111


class OfficeConverter:
    """Office文書からPDF変換を行うクラス"""

    def __init__(self):
        logger.info("Officeコンバーター初期化完了 - Microsoft Office COM API専用")

    def _copy_to_temp_if_onedrive(self, input_path: str) -> Tuple[str, str]:
        """
        OneDriveパスのファイルを一時ディレクトリにコピーする。
        OneDriveの同期処理がCOM APIに干渉するのを防ぐため。

        Returns:
            (実際に変換に使うパス, 一時ディレクトリパスまたは空文字)
        """
        if is_cloud_sync_path(input_path):
            try:
                temp_dir = tempfile.mkdtemp(prefix="pdf_conv_")
                temp_path = os.path.join(temp_dir, Path(input_path).name)
                shutil.copy2(input_path, temp_path)
                logger.info(f"クラウド同期ファイルを一時フォルダにコピー: {Path(input_path).name} -> {temp_dir}")
                return temp_path, temp_dir
            except Exception as e:
                logger.warning(f"一時コピー失敗、元パスで続行: {e}")
                return input_path, ""
        return input_path, ""
    
    def convert_to_pdf(self, input_path: str, output_path: str, split_sheets: bool = False) -> List[str]:
        """
        OfficeファイルのPDF変換メイン処理
        
        Args:
            input_path: 入力ファイルパス
            output_path: 出力PDFパス
            
        Returns:
            List[str]: 生成されたPDFファイルのパスのリスト
        """
        try:
            file_ext = Path(input_path).suffix.lower()
            
            if file_ext in ['.docx', '.doc']:
                return self._convert_word_to_pdf(input_path, output_path)
            elif file_ext in ['.xlsx', '.xls']:
                return self._convert_excel_to_pdf(input_path, output_path, split_sheets)
            elif file_ext in ['.pptx', '.ppt']:
                return self._convert_powerpoint_to_pdf(input_path, output_path)
            else:
                logger.error(f"未対応のOffice形式: {file_ext}")
                return []
        
        except Exception as e:
            logger.error(f"Office変換エラー: {input_path} - {str(e)}", exc_info=True)
            return []
    
    def _convert_word_to_pdf(self, input_path: str, output_path: str) -> List[str]:
        """Word文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        # OneDriveパスは一時フォルダにコピーして変換
        work_path, temp_dir = self._copy_to_temp_if_onedrive(input_path)
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    generated_files = self._try_office_conversion(work_path, output_path)
                    if generated_files:
                        return generated_files
                except Exception as e:
                    logger.warning(f"Word変換 試行{attempt + 1}/{max_retries} 例外: {e}")

                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 2
                    logger.info(f"Word変換リトライ待機 {wait_sec}秒 ({attempt + 1}/{max_retries}): {Path(input_path).name}")
                    time.sleep(wait_sec)

            logger.error(f"Word変換失敗 - Microsoft Word COM API変換エラー: {input_path}")
            return []

        except Exception as e:
            logger.error(f"Word変換エラー: {input_path} - {str(e)}")
            return []
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    
    def _convert_excel_to_pdf(self, input_path: str, output_path: str, split_sheets: bool = False) -> List[str]:
        """Excel文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        # OneDriveパスは一時フォルダにコピーして変換
        work_path, temp_dir = self._copy_to_temp_if_onedrive(input_path)
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    generated_files = self._try_office_conversion(work_path, output_path, split_sheets)
                    if generated_files:
                        return generated_files
                except Exception as e:
                    logger.warning(f"Excel変換 試行{attempt + 1}/{max_retries} 例外: {e}")

                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 2
                    logger.info(f"Excel変換リトライ待機 {wait_sec}秒 ({attempt + 1}/{max_retries}): {Path(input_path).name}")
                    time.sleep(wait_sec)

            logger.error(f"Excel変換失敗 - Microsoft Excel COM API変換エラー: {input_path}")
            return []

        except Exception as e:
            logger.error(f"Excel変換エラー: {input_path} - {str(e)}")
            return []
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    
    
    def _convert_powerpoint_to_pdf(self, input_path: str, output_path: str) -> List[str]:
        """PowerPoint文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        # OneDriveパスは一時フォルダにコピーして変換
        work_path, temp_dir = self._copy_to_temp_if_onedrive(input_path)
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    generated_files = self._try_office_conversion(work_path, output_path)
                    if generated_files:
                        return generated_files
                except Exception as e:
                    logger.warning(f"PowerPoint変換 試行{attempt + 1}/{max_retries} 例外: {e}")

                if attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 2
                    logger.info(f"PowerPoint変換リトライ待機 {wait_sec}秒 ({attempt + 1}/{max_retries}): {Path(input_path).name}")
                    time.sleep(wait_sec)

            logger.error(f"PowerPoint変換失敗 - Microsoft PowerPoint COM API変換エラー: {input_path}")
            return []

        except Exception as e:
            logger.error(f"PowerPoint変換エラー: {input_path} - {str(e)}")
            return []
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    
    
    def _try_office_conversion(self, input_path: str, output_path: str, split_sheets: bool = False) -> List[str]:
        """Microsoft Office変換の試行"""
        word_app = None
        excel_app = None
        powerpoint_app = None

        try:
            # Windowsの場合のみMicrosoft Officeを使用
            if os.name != 'nt':
                return []

            import win32com.client
            from pywintypes import com_error
            import pythoncom

            # COM初期化を確実に実行
            try:
                pythoncom.CoInitialize()
                logger.info("COM初期化完了")
            except Exception:
                logger.info("COM初期化済み（既に初期化されているか別スレッド）")
            file_ext = Path(input_path).suffix.lower()
            
            # 絶対パスに変換（COM API要件）
            input_abs_path = str(Path(input_path).resolve())
            output_abs_path = str(Path(output_path).resolve())
            
            if file_ext in ['.doc', '.docx']:
                # Word変換 - 詳細なエラーハンドリング付き
                try:
                    # PyInstallerでの実行の場合はDispatchExを使用
                    try:
                        word_app = win32com.client.DispatchEx("Word.Application")
                        logger.info("新しいWordインスタンスを作成 (DispatchEx)")
                    except Exception:
                        word_app = win32com.client.Dispatch("Word.Application")
                        logger.info("新しいWordインスタンスを作成 (Dispatch)")
                    
                    # Visibleプロパティ設定をtry-catchで保護
                    try:
                        word_app.Visible = False
                    except Exception:
                        logger.warning("Word.Visibleプロパティの設定をスキップ")
                    
                    # DisplayAlerts設定をtry-catchで保護
                    try:
                        word_app.DisplayAlerts = 0  # アラート無効化
                    except Exception:
                        logger.warning("Word.DisplayAlertsプロパティの設定をスキップ")
                    
                    # ファイル存在確認
                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return []
                    
                    # ドキュメントを開く（段階的フォールバック）
                    doc = None
                    try:
                        if file_ext == '.doc':
                            # .docファイル: シンプルな設定で開く
                            logger.info(f".docファイルを開いています: {Path(input_path).name}")
                            doc = word_app.Documents.Open(
                                input_abs_path,
                                ReadOnly=True,
                                ConfirmConversions=False,
                                AddToRecentFiles=False,  # 最近使ったファイルに追加しない
                                Revert=False             # 再読み込み確認を抑制
                            )
                        else:
                            # .docxファイル: 通常処理
                            logger.info(f".docxファイルを開いています: {Path(input_path).name}")
                            doc = word_app.Documents.Open(
                                input_abs_path,
                                ReadOnly=True,
                                AddToRecentFiles=False,  # 最近使ったファイルに追加しない
                                Revert=False             # 再読み込み確認を抑制
                            )
                    except Exception as open_error:
                        logger.warning(f"通常のOpen処理失敗: {open_error}")
                        try:
                            # フォールバック: より基本的な設定で再試行
                            logger.info("フォールバック処理でファイルを開き直し")
                            doc = word_app.Documents.Open(input_abs_path)
                        except Exception as fallback_error:
                            logger.error(f"フォールバック処理も失敗: {fallback_error}")
                            return []
                    
                    if doc is None:
                        logger.error("ドキュメントを開くことができませんでした")
                        return []
                    
                    # PDF品質設定
                    # ExportFormat:17=PDF, OptimizeFor:0=印刷品質, BitmapMissingFonts:True
                    doc.ExportAsFixedFormat(output_abs_path, 
                                          ExportFormat=17, 
                                          OptimizeFor=0,
                                          BitmapMissingFonts=True,
                                          DocStructureTags=True,
                                          CreateBookmarks=0)
                    
                    doc.Close()
                    logger.info(f"Microsoft Word変換成功: {Path(input_path).name}")
                    return [output_abs_path]
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"Word COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return []
                except Exception as e:
                    logger.error(f"Word変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return []
            
            elif file_ext in ['.xls', '.xlsx']:
                # Excel変換 - 詳細なエラーハンドリング付き
                try:
                    # PyInstallerでの実行の場合はDispatchExを使用
                    try:
                        excel_app = win32com.client.DispatchEx("Excel.Application")
                        logger.info("新しいExcelインスタンスを作成 (DispatchEx)")
                    except Exception:
                        excel_app = win32com.client.Dispatch("Excel.Application")
                        logger.info("新しいExcelインスタンスを作成 (Dispatch)")

                    # Visibleプロパティ設定をtry-catchで保護
                    try:
                        excel_app.Visible = False
                    except Exception:
                        logger.warning("Excel.Visibleプロパティの設定をスキップ")

                    # DisplayAlerts設定でダイアログを無効化
                    try:
                        excel_app.DisplayAlerts = False
                    except Exception:
                        logger.warning("Excel.DisplayAlertsプロパティの設定をスキップ")

                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return []

                    # ワークブックを開く
                    logger.info(f"Excelファイルを開いています: {Path(input_path).name}")
                    workbook = excel_app.Workbooks.Open(
                        input_abs_path,
                        UpdateLinks=0,              # 外部リンク更新ダイアログを抑制
                        ReadOnly=True,
                        IgnoreReadOnlyRecommended=True,
                        Notify=False                # 「別アプリで開かれています」ダイアログを抑制
                    )
                    
                    generated_files = []
                    # シートごとにPDF化するオプションを確認
                    if split_sheets:
                        logger.info("Excelの全シートを個別のPDFとして出力します。")

                        base = output_abs_path.rsplit('.', 1)[0]
                        # 全てのシートをループ（左から順に2桁連番付与）
                        for idx, sheet in enumerate(workbook.Worksheets, start=1):
                            sheet.Activate()

                            # 出力ファイル名を生成 (元ファイル名_連番_シート名.pdf)
                            output_sheet_path = f"{base}_{idx:02d}_{sheet.Name}.pdf"

                            logger.info(f"シートをPDF化: {sheet.Name} -> {Path(output_sheet_path).name}")

                            # シートをPDFとしてエクスポート
                            sheet.ExportAsFixedFormat(Type=0,  # xlTypePDF
                                                      Filename=output_sheet_path,
                                                      Quality=0,  # xlQualityStandard
                                                      IgnorePrintAreas=False,
                                                      OpenAfterPublish=False)
                            generated_files.append(output_sheet_path)
                    else:
                        # デフォルト: アクティブシート（開いた時のシート）のみをPDF化
                        logger.info("Excelのアクティブシート（開いた時のシート）のみをPDF化します。")

                        # 現在アクティブなシートを取得
                        active_sheet = workbook.ActiveSheet
                        logger.info(f"アクティブシート: {active_sheet.Name}")

                        # 他のシートを一時的に非表示にする
                        original_visibility = {}
                        for sheet in workbook.Worksheets:
                            original_visibility[sheet.Name] = sheet.Visible
                            if sheet.Name != active_sheet.Name:
                                sheet.Visible = False  # xlSheetHidden

                        # アクティブシートのみPDF化
                        workbook.ExportAsFixedFormat(Type=0,
                                                   Filename=output_abs_path,
                                                   Quality=0,
                                                   IgnorePrintAreas=False,
                                                   OpenAfterPublish=False)

                        # シートの表示状態を復元
                        for sheet_name, visibility in original_visibility.items():
                            try:
                                workbook.Worksheets(sheet_name).Visible = visibility
                            except Exception:
                                pass

                        generated_files.append(output_abs_path)
                    
                    workbook.Close()
                    logger.info(f"Microsoft Excel変換成功: {Path(input_path).name}")
                    return generated_files
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"Excel COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return []
                except Exception as e:
                    logger.error(f"Excel変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return []
            
            elif file_ext in ['.ppt', '.pptx']:
                # PowerPoint変換 - 詳細なエラーハンドリング付き
                try:
                    # PyInstallerでの実行の場合はDispatchExを使用
                    try:
                        powerpoint_app = win32com.client.DispatchEx("PowerPoint.Application")
                        logger.info("新しいPowerPointインスタンスを作成 (DispatchEx)")
                    except Exception:
                        powerpoint_app = win32com.client.Dispatch("PowerPoint.Application")
                        logger.info("新しいPowerPointインスタンスを作成 (Dispatch)")
                    
                    # ファイル存在確認
                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return []
                    
                    # プレゼンテーションを開く
                    logger.info(f"PowerPointファイルを開いています: {Path(input_path).name}")
                    presentation = powerpoint_app.Presentations.Open(input_abs_path, ReadOnly=True)
                    
                    # PDF品質設定でエクスポート
                    presentation.ExportAsFixedFormat(output_abs_path,
                                                   FixedFormatType=2,  # ppFixedFormatTypePDF
                                                   Intent=1,  # ppFixedFormatIntentPrint
                                                   FrameSlides=0,  # msoFalse
                                                   HandoutOrder=1,
                                                   OutputType=5)  # ppPrintOutputSlides
                    
                    presentation.Close()
                    logger.info(f"Microsoft PowerPoint変換成功: {Path(input_path).name}")
                    return [output_abs_path]
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"PowerPoint COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return []
                except Exception as e:
                    logger.error(f"PowerPoint変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return []
            
            return []
            
        except ImportError:
            logger.error("pywin32が未インストールです。Microsoft Office COM API変換には pywin32 が必要です。")
            return []
        except Exception as e:
            error_message = str(e)
            if "Microsoft Word" in error_message or "Word.Application" in error_message:
                logger.error(f"Microsoft Wordが利用できません: {error_message}")
                logger.error("Microsoft Wordがインストールされ、正しく動作していることを確認してください。")
            elif "Microsoft Excel" in error_message or "Excel.Application" in error_message:
                logger.error(f"Microsoft Excelが利用できません: {error_message}")
                logger.error("Microsoft Excelがインストールされ、正しく動作していることを確認してください。")
            elif "Microsoft PowerPoint" in error_message or "PowerPoint.Application" in error_message:
                logger.error(f"Microsoft PowerPointが利用できません: {error_message}")
                logger.error("Microsoft PowerPointがインストールされ、正しく動作していることを確認してください。")
            else:
                logger.error(f"Microsoft Office COM API変換エラー: {error_message}")
            return []
        finally:
            # COM オブジェクトの確実なクリーンアップ
            try:
                if word_app:
                    # 全てのドキュメントを強制クローズ
                    try:
                        for doc in word_app.Documents:
                            doc.Close(SaveChanges=False)
                    except Exception:
                        pass
                    word_app.Quit()
                    # COMオブジェクトの明示的解放
                    del word_app
                    # Wordプロセスが完全に終了するまで待機（次回RPC_E_CALL_REJECTEDを防ぐ）
                    time.sleep(1)

                if excel_app:
                    # 全てのワークブックを強制クローズ
                    try:
                        for wb in excel_app.Workbooks:
                            wb.Close(SaveChanges=False)
                    except Exception:
                        pass
                    excel_app.Quit()
                    del excel_app
                    time.sleep(1)

                if powerpoint_app:
                    # 全てのプレゼンテーションを強制クローズ
                    try:
                        for pres in powerpoint_app.Presentations:
                            pres.Close()
                    except Exception:
                        pass
                    powerpoint_app.Quit()
                    del powerpoint_app
                    time.sleep(1)

                # COMライブラリのクリーンアップ（個別変換では行わない）
                # アプリケーション終了時のみCoUninitializeを実行

            except Exception as cleanup_error:
                logger.warning(f"COM クリーンアップエラー: {cleanup_error}")
                pass