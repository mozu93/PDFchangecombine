"""
メインウィンドウクラス
要件定義書 F-001 モード選択機能の実装
"""

import customtkinter as ctk
from typing import Optional
import time

from ..config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, 
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    UI_THEME, UI_COLOR_THEME,
    MAX_STARTUP_TIME_SECONDS
)
from ..utils.logger import logger
from .mode_selector import ModeSelector
from .converter_window import ConverterWindow
from .combiner_window import CombinerWindow


class MainWindow:
    """メインアプリケーションウィンドウ"""
    
    def __init__(self):
        self.startup_time = time.time()
        
        # CustomTkinter設定
        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)
        
        # メインウィンドウ作成
        self.root = ctk.CTk()
        self._setup_window()
        
        # 子ウィンドウ
        self.current_window: Optional[ctk.CTkToplevel] = None
        
        # モード選択画面作成
        self.mode_selector = ModeSelector(
            parent=self.root,
            on_convert_mode=self._open_converter_mode,
            on_combine_mode=self._open_combiner_mode
        )
        
        self._log_startup_time()
    
    def _setup_window(self) -> None:
        """ウィンドウ初期設定"""
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # ウィンドウを中央に配置
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (WINDOW_HEIGHT // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")
        
        # アプリ終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("メインウィンドウ初期化完了")
    
    def _log_startup_time(self) -> None:
        """起動時間のログ記録（要件定義書 5.3.性能）"""
        startup_duration = time.time() - self.startup_time
        
        if startup_duration <= MAX_STARTUP_TIME_SECONDS:
            logger.info(f"起動時間: {startup_duration:.2f}秒 (要件内)")
        else:
            logger.warning(f"起動時間超過: {startup_duration:.2f}秒 (要件: {MAX_STARTUP_TIME_SECONDS}秒以内)")
    
    def _open_converter_mode(self) -> None:
        """PDF変換モード起動（要件定義書 F-001）"""
        logger.info("PDF変換モード選択")
        self._close_current_window()
        
        self.current_window = ConverterWindow(
            parent=self.root,
            on_back=self._back_to_mode_selection,
            on_combine_request=self._open_combiner_with_files
        )
        
        # メイン画面を隠す
        self.root.withdraw()
    
    def _open_combiner_mode(self) -> None:
        """PDF結合モード起動（要件定義書 F-001）"""
        logger.info("PDF結合モード選択")
        self._close_current_window()
        
        self.current_window = CombinerWindow(
            parent=self.root,
            on_back=self._back_to_mode_selection
        )
        
        # メイン画面を隠す
        self.root.withdraw()
    
    def _open_combiner_with_files(self, pdf_files: list[str]) -> None:
        """変換後のファイル群で結合モード起動（要件定義書 F-106）"""
        logger.info(f"変換後結合モード移行 - ファイル数: {len(pdf_files)}")
        self._close_current_window()
        
        self.current_window = CombinerWindow(
            parent=self.root,
            on_back=self._back_to_mode_selection,
            initial_files=pdf_files
        )
    
    def _back_to_mode_selection(self) -> None:
        """モード選択画面に戻る"""
        logger.info("モード選択画面に戻る")
        self._close_current_window()
        
        # メイン画面を表示
        self.root.deiconify()
        self.mode_selector.reset()
    
    def _close_current_window(self) -> None:
        """現在の子ウィンドウを閉じる"""
        if self.current_window:
            self.current_window.destroy()
            self.current_window = None
    
    def _on_closing(self) -> None:
        """アプリケーション終了処理"""
        logger.info("アプリケーション終了処理開始")
        
        # 子ウィンドウを閉じる
        self._close_current_window()
        
        # メインウィンドウ破棄
        self.root.quit()
        self.root.destroy()
    
    def run(self) -> None:
        """アプリケーション実行"""
        logger.info("アプリケーション実行開始")
        self.root.mainloop()