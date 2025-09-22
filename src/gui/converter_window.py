"""
PDF変換ウィンドウ
要件定義書 4.2 PDF変換モードの実装
"""

import customtkinter as ctk
from typing import Callable, Optional
from tkinterdnd2 import DND_FILES, TkinterDnD

from ..utils.logger import logger


class ConverterWindow(ctk.CTkToplevel):
    """PDF変換ウィンドウクラス"""
    
    def __init__(self, parent: ctk.CTk,
                 on_back: Callable[[], None],
                 on_combine_request: Optional[Callable[[list[str]], None]] = None):
        super().__init__(parent)
        
        self.on_back = on_back
        self.on_combine_request = on_combine_request
        
        self._setup_window()
        self._create_widgets()
        
        logger.info("PDF変換ウィンドウ初期化完了")
    
    def _setup_window(self) -> None:
        """ウィンドウ設定"""
        self.title("PDF変換モード")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # 親ウィンドウの中央に配置
        self.transient(self.master)
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - 400
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - 300
        self.geometry(f"800x600+{x}+{y}")
        
        # 最前面に表示
        self.lift()
        self.focus_set()
    
    def _create_widgets(self) -> None:
        """ウィジェット作成"""
        # メインフレーム
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ヘッダーフレーム
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 20))
        
        # 戻るボタン
        back_button = ctk.CTkButton(
            header_frame,
            text="← 戻る",
            width=100,
            command=self.on_back
        )
        back_button.pack(side="left", padx=10, pady=10)
        
        # タイトル
        title_label = ctk.CTkLabel(
            header_frame,
            text="PDF変換",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=(20, 0), pady=10)
        
        # ドロップエリアフレーム
        drop_frame = ctk.CTkFrame(main_frame)
        drop_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ドロップエリア
        self.drop_area = ctk.CTkTextbox(
            drop_frame,
            height=200,
            font=ctk.CTkFont(size=14)
        )
        self.drop_area.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 初期メッセージ
        initial_message = """📁 ファイルをここにドラッグ&ドロップしてください

対応ファイル:
• Word: .docx, .doc
• Excel: .xlsx, .xls  
• PowerPoint: .pptx, .ppt
• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff

フォルダをドロップすると、内部のファイルを自動的に検索します。"""
        
        self.drop_area.insert("0.0", initial_message)
        self.drop_area.configure(state="disabled")
        
        # TODO: ドラッグ&ドロップ機能実装（次のフェーズで実装）
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 変換ボタン（現在は無効）
        self.convert_button = ctk.CTkButton(
            button_frame,
            text="PDF変換開始",
            height=40,
            state="disabled"
        )
        self.convert_button.pack(side="right", padx=10, pady=10)
        
        # ファイル選択ボタン（フォールバック用）
        select_button = ctk.CTkButton(
            button_frame,
            text="📂 ファイルを選択",
            height=40,
            command=self._select_files
        )
        select_button.pack(side="right", padx=10, pady=10)
    
    def _select_files(self) -> None:
        """ファイル選択ダイアログ"""
        # TODO: ファイル選択ダイアログの実装（次のフェーズで実装）
        logger.info("ファイル選択ダイアログ（未実装）")
        
        # デモ用メッセージ
        self.drop_area.configure(state="normal")
        self.drop_area.delete("0.0", "end")
        self.drop_area.insert("0.0", "ファイル選択機能は次のフェーズで実装予定です。")
        self.drop_area.configure(state="disabled")