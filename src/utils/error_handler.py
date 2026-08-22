"""
エラーハンドリングユーティリティ
要件定義書 5.1 エラーハンドリング要件の実装
"""

import sys
import traceback
from typing import Optional, Callable, Any
from enum import Enum
import customtkinter as ctk

from .logger import logger


class ErrorSeverity(Enum):
    """エラー重要度分類（要件定義書 5.1）"""
    FATAL = "致命的エラー"      # アプリケーション続行不可
    CRITICAL = "重大エラー"     # 機能実行不可、但し他機能は継続可能
    WARNING = "警告"          # 処理続行可能、ユーザー通知必要
    INFO = "情報"             # 処理続行可能、記録のみ


class ErrorHandler:
    """エラーハンドリング統合管理クラス"""
    
    def __init__(self, parent_window: Optional[ctk.CTk] = None):
        self.parent_window = parent_window
        self.error_count = 0
        self.warning_count = 0
        
        # 未処理例外のハンドラを設定
        sys.excepthook = self._handle_uncaught_exception
        
        logger.info("エラーハンドラー初期化完了")
    
    def handle_error(self, error: Exception, severity: ErrorSeverity, 
                    context: str = "", user_message: str = "",
                    callback: Optional[Callable] = None) -> None:
        """
        統合エラーハンドリング（要件定義書 5.1）
        
        Args:
            error: 発生した例外
            severity: エラー重要度
            context: エラー発生コンテキスト
            user_message: ユーザー向けメッセージ（空の場合は自動生成）
            callback: エラー後のコールバック関数
        """
        # エラーカウント更新
        if severity in [ErrorSeverity.FATAL, ErrorSeverity.CRITICAL]:
            self.error_count += 1
        elif severity == ErrorSeverity.WARNING:
            self.warning_count += 1
        
        # ログ記録（要件定義書 5.1.ログ連携）
        error_details = f"{context}: {str(error)}" if context else str(error)
        
        if severity == ErrorSeverity.FATAL:
            logger.error(f"[FATAL] {error_details}", exc_info=True)
        elif severity == ErrorSeverity.CRITICAL:
            logger.error(f"[CRITICAL] {error_details}", exc_info=True)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(f"[WARNING] {error_details}")
        else:
            logger.info(f"[INFO] {error_details}")
        
        # ユーザー通知メッセージ準備
        if not user_message:
            user_message = self._generate_user_message(error, severity, context)
        
        # ユーザー通知（要件定義書 5.1.通知方法）
        if severity in [ErrorSeverity.FATAL, ErrorSeverity.CRITICAL, ErrorSeverity.WARNING]:
            self._show_error_dialog(user_message, severity)
        
        # 致命的エラー時の処理（要件定義書 5.1.致命的エラー）
        if severity == ErrorSeverity.FATAL:
            logger.error("致命的エラーによりアプリケーションを終了します")
            if callback:
                callback()
            sys.exit(1)
        
        # コールバック実行
        if callback and severity != ErrorSeverity.FATAL:
            try:
                callback()
            except Exception as cb_error:
                logger.error(f"エラーハンドラーコールバック実行エラー: {cb_error}")
    
    def _generate_user_message(self, error: Exception, severity: ErrorSeverity, context: str) -> str:
        """ユーザー向けエラーメッセージ生成（要件定義書 5.1.利用者が原因を特定できるよう）"""
        base_message = ""
        
        # コンテキスト別メッセージ
        if "変換" in context:
            if isinstance(error, FileNotFoundError):
                base_message = "ファイルが見つかりません。ファイルパスを確認してください。"
            elif isinstance(error, PermissionError):
                base_message = "ファイルにアクセスできません。ファイルが他のアプリで開かれていないか確認してください。"
            elif "破損" in str(error).lower():
                base_message = "ファイルが破損している可能性があります。別のファイルをお試しください。"
            else:
                base_message = "ファイル変換中にエラーが発生しました。ファイル形式が対応しているか確認してください。"
        
        elif "結合" in context:
            if isinstance(error, FileNotFoundError):
                base_message = "結合対象のPDFファイルが見つかりません。"
            elif "破損" in str(error).lower():
                base_message = "PDFファイルが破損している可能性があります。有効なPDFファイルを使用してください。"
            else:
                base_message = "PDF結合中にエラーが発生しました。すべてのファイルが有効なPDFか確認してください。"
        
        elif "保存" in context:
            if isinstance(error, PermissionError):
                base_message = "保存先に書き込み権限がありません。別の場所を選択してください。"
            elif isinstance(error, OSError):
                base_message = "保存先の容量が不足している可能性があります。"
            else:
                base_message = "ファイル保存中にエラーが発生しました。"
        
        else:
            # 一般的なエラーメッセージ
            if isinstance(error, FileNotFoundError):
                base_message = "指定されたファイルまたはフォルダが見つかりません。"
            elif isinstance(error, PermissionError):
                base_message = "ファイルまたはフォルダにアクセスする権限がありません。"
            elif isinstance(error, MemoryError):
                base_message = "メモリが不足しています。処理するファイル数を減らしてください。"
            else:
                base_message = f"予期しないエラーが発生しました: {type(error).__name__}"
        
        # 重要度に応じた対処法追加
        if severity == ErrorSeverity.FATAL:
            base_message += "\n\nアプリケーションを再起動してください。"
        elif severity == ErrorSeverity.CRITICAL:
            base_message += "\n\n操作をやり直してください。"
        elif severity == ErrorSeverity.WARNING:
            base_message += "\n\n処理は継続されます。"
        
        return base_message
    
    def _show_error_dialog(self, message: str, severity: ErrorSeverity) -> None:
        """エラーダイアログ表示（要件定義書 5.1.モーダルダイアログで通知）"""
        try:
            if self.parent_window is None:
                # 親ウィンドウがない場合は標準ダイアログ
                print(f"[{severity.value}] {message}")
                return
            
            # CustomTkinterダイアログ
            dialog = ctk.CTkToplevel(self.parent_window)
            dialog.title(f"{severity.value}")
            dialog.geometry("400x200")
            dialog.transient(self.parent_window)
            dialog.grab_set()  # モーダル設定
            
            # 中央配置
            dialog.update_idletasks()
            x = self.parent_window.winfo_x() + (self.parent_window.winfo_width() // 2) - 200
            y = self.parent_window.winfo_y() + (self.parent_window.winfo_height() // 2) - 100
            dialog.geometry(f"400x200+{x}+{y}")
            
            # アイコンと色設定
            if severity == ErrorSeverity.FATAL:
                icon = "🚨"
                color = "#ff4444"
            elif severity == ErrorSeverity.CRITICAL:
                icon = "❌"
                color = "#ff6666"
            elif severity == ErrorSeverity.WARNING:
                icon = "⚠️"
                color = "#ffaa00"
            else:
                icon = "ℹ️"
                color = "#4444ff"
            
            # メインフレーム
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # タイトルラベル
            title_label = ctk.CTkLabel(
                main_frame,
                text=f"{icon} {severity.value}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=color
            )
            title_label.pack(pady=(10, 15))
            
            # メッセージテキスト
            message_text = ctk.CTkTextbox(
                main_frame,
                height=80,
                font=ctk.CTkFont(size=12)
            )
            message_text.pack(fill="both", expand=True, padx=10, pady=(0, 15))
            message_text.insert("0.0", message)
            message_text.configure(state="disabled")
            
            # OKボタン（要件定義書 5.1.「OK」ボタンのみを表示）
            ok_button = ctk.CTkButton(
                main_frame,
                text="OK",
                command=dialog.destroy,
                width=100
            )
            ok_button.pack(pady=(0, 10))
            
            # フォーカス設定
            ok_button.focus_set()

            if severity == ErrorSeverity.FATAL:
                # FATAL時はこの直後にsys.exit()するため、描画を確定させたうえで
                # ユーザーがOKを押すまでブロックする（さもないと画面に出る前に終了する）
                dialog.update()
                self.parent_window.wait_window(dialog)

        except Exception as dialog_error:
            # ダイアログ表示エラー時はログのみ
            logger.error(f"エラーダイアログ表示エラー: {dialog_error}")
            print(f"[{severity.value}] {message}")
    
    def _handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        """未処理例外のハンドラ"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C等の中断は通常処理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # 未処理例外を致命的エラーとして扱う
        error_msg = f"未処理例外: {exc_type.__name__}: {exc_value}"
        logger.error(error_msg, exc_info=(exc_type, exc_value, exc_traceback))
        
        self.handle_error(
            exc_value,
            ErrorSeverity.FATAL,
            "システム例外",
            f"予期しない内部エラーが発生しました。\n\n{error_msg}\n\nアプリケーションを終了します。"
        )
    
    def get_error_statistics(self) -> dict:
        """エラー統計情報取得"""
        return {
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'total_issues': self.error_count + self.warning_count
        }


# グローバルエラーハンドラーインスタンス
error_handler = ErrorHandler()