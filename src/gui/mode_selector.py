"""
モード選択画面
要件定義書 F-001 モード選択機能の具体的実装
"""

import customtkinter as ctk
from typing import Callable

from ..utils.logger import logger


class ModeSelector:
    """モード選択画面クラス"""
    
    def __init__(self, parent: ctk.CTk, 
                 on_convert_mode: Callable[[], None],
                 on_combine_mode: Callable[[], None]):
        self.parent = parent
        self.on_convert_mode = on_convert_mode
        self.on_combine_mode = on_combine_mode
        
        self._create_widgets()
        logger.info("モード選択画面初期化完了")
    
    def _create_widgets(self) -> None:
        """ウィジェット作成"""
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # タイトルラベル
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="PDF変換・結合ツール",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(30, 10))
        
        # サブタイトル
        subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="実行したい機能を選択してください",
            font=ctk.CTkFont(size=16)
        )
        subtitle_label.pack(pady=(0, 40))
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(expand=True, fill="both", padx=40, pady=20)
        
        # PDF変換ボタン
        convert_button = ctk.CTkButton(
            button_frame,
            text="📄 PDF変換\\nOffice・画像ファイルをPDFに変換",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=120,
            command=self._on_convert_clicked
        )
        convert_button.pack(pady=(40, 20), padx=40, fill="x")
        
        # PDF結合ボタン  
        combine_button = ctk.CTkButton(
            button_frame,
            text="📋 PDF結合\\n複数のPDFファイルを1つに結合",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=120,
            command=self._on_combine_clicked
        )
        combine_button.pack(pady=(20, 40), padx=40, fill="x")
        
        # 説明テキスト
        info_text = ctk.CTkTextbox(
            self.main_frame,
            height=100,
            font=ctk.CTkFont(size=12)
        )
        info_text.pack(fill="x", padx=20, pady=(0, 20))
        
        info_content = \"\"\"対応形式:
• Office: Word (.docx, .doc), Excel (.xlsx, .xls), PowerPoint (.pptx, .ppt)
• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff
• PDF: 結合処理に使用\"\"\"
        
        info_text.insert("0.0", info_content)
        info_text.configure(state="disabled")
    
    def _on_convert_clicked(self) -> None:
        """PDF変換ボタンクリック処理"""
        logger.info("PDF変換モードボタンがクリックされました")
        self.on_convert_mode()
    
    def _on_combine_clicked(self) -> None:
        """PDF結合ボタンクリック処理"""
        logger.info("PDF結合モードボタンがクリックされました") 
        self.on_combine_mode()
    
    def reset(self) -> None:
        """画面リセット（モード選択に戻った際の処理）"""
        logger.info("モード選択画面リセット")
        # 現在は特別な処理なし（将来的な拡張用）