"""
Officeファイル変換モジュール
要件定義書 F-102, F-103 Office文書のPDF変換実装
"""

import os
from pathlib import Path

# Microsoft Office COM API用ライブラリ（Windows専用）
# フォールバック機能は削除し、高品質なCOM APIのみを使用

from ..utils.logger import logger


class OfficeConverter:
    """Office文書からPDF変換を行うクラス"""
    
    def __init__(self):
        logger.info("Officeコンバーター初期化完了 - Microsoft Office COM API専用")
    
    def convert_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        OfficeファイルのPDF変換メイン処理
        
        Args:
            input_path: 入力ファイルパス
            output_path: 出力PDFパス
            
        Returns:
            bool: 変換成功時True
        """
        try:
            file_ext = Path(input_path).suffix.lower()
            
            if file_ext in ['.docx', '.doc']:
                return self._convert_word_to_pdf(input_path, output_path)
            elif file_ext in ['.xlsx', '.xls']:
                return self._convert_excel_to_pdf(input_path, output_path)
            elif file_ext in ['.pptx', '.ppt']:
                return self._convert_powerpoint_to_pdf(input_path, output_path)
            else:
                logger.error(f"未対応のOffice形式: {file_ext}")
                return False
        
        except Exception as e:
            logger.error(f"Office変換エラー: {input_path} - {str(e)}", exc_info=True)
            return False
    
    def _convert_word_to_pdf(self, input_path: str, output_path: str) -> bool:
        """Word文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        try:
            # Microsoft Office COM APIでのみ変換を試行
            if self._try_office_conversion(input_path, output_path):
                return True
            
            # COM APIが失敗した場合はエラー
            logger.error(f"Word変換失敗 - Microsoft Word COM API変換エラー: {input_path}")
            return False
            
        except Exception as e:
            logger.error(f"Word変換エラー: {input_path} - {str(e)}")
            return False
    
    def _convert_excel_to_pdf(self, input_path: str, output_path: str) -> bool:
        """Excel文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        try:
            # Microsoft Office COM APIでのみ変換を試行
            if self._try_office_conversion(input_path, output_path):
                return True
            
            # COM APIが失敗した場合はエラー
            logger.error(f"Excel変換失敗 - Microsoft Excel COM API変換エラー: {input_path}")
            return False
            
        except Exception as e:
            logger.error(f"Excel変換エラー: {input_path} - {str(e)}")
            return False
    
    
    def _convert_powerpoint_to_pdf(self, input_path: str, output_path: str) -> bool:
        """PowerPoint文書のPDF変換（Microsoft Office COM APIのみ使用）"""
        try:
            # Microsoft Office COM APIでのみ変換を試行
            if self._try_office_conversion(input_path, output_path):
                return True
            
            # COM APIが失敗した場合はエラー
            logger.error(f"PowerPoint変換失敗 - Microsoft PowerPoint COM API変換エラー: {input_path}")
            return False
            
        except Exception as e:
            logger.error(f"PowerPoint変換エラー: {input_path} - {str(e)}")
            return False
    
    
    def _try_office_conversion(self, input_path: str, output_path: str) -> bool:
        """Microsoft Office変換の試行"""
        word_app = None
        excel_app = None
        powerpoint_app = None
        
        try:
            # Windowsの場合のみMicrosoft Officeを使用
            if os.name != 'nt':
                return False
            
            import win32com.client
            from pywintypes import com_error
            file_ext = Path(input_path).suffix.lower()
            
            # 絶対パスに変換（COM API要件）
            input_abs_path = str(Path(input_path).resolve())
            output_abs_path = str(Path(output_path).resolve())
            
            if file_ext in ['.doc', '.docx']:
                # Word変換 - 詳細なエラーハンドリング付き
                try:
                    # 既存のWordインスタンスを確認してから新しいインスタンスを作成
                    try:
                        word_app = win32com.client.GetActiveObject("Word.Application")
                        logger.info("既存のWordインスタンスを使用")
                    except:
                        word_app = win32com.client.Dispatch("Word.Application")
                        logger.info("新しいWordインスタンスを作成")
                    
                    # Visibleプロパティ設定をtry-catchで保護
                    try:
                        word_app.Visible = False
                    except:
                        logger.warning("Word.Visibleプロパティの設定をスキップ")
                    
                    # DisplayAlerts設定をtry-catchで保護
                    try:
                        word_app.DisplayAlerts = 0  # アラート無効化
                    except:
                        logger.warning("Word.DisplayAlertsプロパティの設定をスキップ")
                    
                    # ファイル存在確認
                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return False
                    
                    # ドキュメントを開く（段階的フォールバック）
                    doc = None
                    try:
                        if file_ext == '.doc':
                            # .docファイル: シンプルな設定で開く
                            logger.info(f".docファイルを開いています: {Path(input_path).name}")
                            doc = word_app.Documents.Open(input_abs_path, ReadOnly=True, ConfirmConversions=False)
                        else:
                            # .docxファイル: 通常処理
                            logger.info(f".docxファイルを開いています: {Path(input_path).name}")
                            doc = word_app.Documents.Open(input_abs_path, ReadOnly=True)
                    except Exception as open_error:
                        logger.warning(f"通常のOpen処理失敗: {open_error}")
                        try:
                            # フォールバック: より基本的な設定で再試行
                            logger.info("フォールバック処理でファイルを開き直し")
                            doc = word_app.Documents.Open(input_abs_path)
                        except Exception as fallback_error:
                            logger.error(f"フォールバック処理も失敗: {fallback_error}")
                            return False
                    
                    if doc is None:
                        logger.error("ドキュメントを開くことができませんでした")
                        return False
                    
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
                    return True
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"Word COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return False
                except Exception as e:
                    logger.error(f"Word変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return False
            
            elif file_ext in ['.xls', '.xlsx']:
                # Excel変換 - 詳細なエラーハンドリング付き
                try:
                    # 既存のExcelインスタンスを確認してから新しいインスタンスを作成
                    try:
                        excel_app = win32com.client.GetActiveObject("Excel.Application")
                        logger.info("既存のExcelインスタンスを使用")
                    except:
                        excel_app = win32com.client.Dispatch("Excel.Application")
                        logger.info("新しいExcelインスタンスを作成")
                    
                    # Visibleプロパティ設定をtry-catchで保護
                    try:
                        excel_app.Visible = False
                    except:
                        logger.warning("Excel.Visibleプロパティの設定をスキップ")
                    
                    # DisplayAlerts設定をtry-catchで保護
                    try:
                        excel_app.DisplayAlerts = False
                    except:
                        logger.warning("Excel.DisplayAlertsプロパティの設定をスキップ")
                    
                    # ファイル存在確認
                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return False
                    
                    # ワークブックを開く
                    logger.info(f"Excelファイルを開いています: {Path(input_path).name}")
                    workbook = excel_app.Workbooks.Open(input_abs_path, ReadOnly=True)
                    
                    # 最初のシートをアクティブにして、そのシートのみをPDF化
                    if workbook.Worksheets.Count > 0:
                        first_sheet = workbook.Worksheets(1)  # 1番目のシート
                        first_sheet.Activate()
                        logger.info(f"最初のシートをPDF化: {first_sheet.Name}")
                        
                        # 最初のシートのみをPDFでエクスポート
                        first_sheet.ExportAsFixedFormat(Type=0,  # xlTypePDF
                                                       Filename=output_abs_path,
                                                       Quality=0,  # xlQualityStandard
                                                       IgnorePrintAreas=False,
                                                       OpenAfterPublish=False)
                    else:
                        logger.warning("シートが存在しないため、ワークブック全体をPDF化")
                        # フォールバック: ワークブック全体をPDF化
                        workbook.ExportAsFixedFormat(Type=0,
                                                   Filename=output_abs_path,
                                                   Quality=0,
                                                   IgnorePrintAreas=False,
                                                   OpenAfterPublish=False)
                    
                    workbook.Close()
                    logger.info(f"Microsoft Excel変換成功: {Path(input_path).name}")
                    return True
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"Excel COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return False
                except Exception as e:
                    logger.error(f"Excel変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return False
            
            elif file_ext in ['.ppt', '.pptx']:
                # PowerPoint変換 - 詳細なエラーハンドリング付き
                try:
                    powerpoint_app = win32com.client.Dispatch("PowerPoint.Application")
                    
                    # ファイル存在確認
                    if not os.path.exists(input_abs_path):
                        logger.error(f"ファイルが存在しません: {input_abs_path}")
                        return False
                    
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
                    return True
                    
                except com_error as e:
                    error_code = getattr(e, 'hresult', 'Unknown')
                    error_desc = getattr(e, 'strerror', str(e))
                    logger.error(f"PowerPoint COM エラー: {Path(input_path).name}")
                    logger.error(f"  エラーコード: {error_code}")
                    logger.error(f"  エラー詳細: {error_desc}")
                    return False
                except Exception as e:
                    logger.error(f"PowerPoint変換で予期しないエラー: {Path(input_path).name} - {type(e).__name__}: {e}")
                    return False
            
            return False
            
        except ImportError:
            logger.error("pywin32が未インストールです。Microsoft Office COM API変換には pywin32 が必要です。")
            return False
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
            return False
        finally:
            # COM オブジェクトの確実なクリーンアップ
            try:
                if word_app:
                    word_app.Quit()
                if excel_app:
                    excel_app.Quit()
                if powerpoint_app:
                    powerpoint_app.Quit()
            except:
                pass