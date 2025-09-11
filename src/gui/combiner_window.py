"""
PDF結合ウィンドウ
要件定義書 4.3 PDF結合モードの実装
"""

import customtkinter as ctk
from typing import Callable, Optional

from ..utils.logger import logger


class CombinerWindow(ctk.CTkToplevel):
    """PDF結合ウィンドウクラス"""
    
    def __init__(self, parent: ctk.CTk,
                 on_back: Callable[[], None],
                 initial_files: Optional[list[str]] = None):
        super().__init__(parent)
        
        self.on_back = on_back
        self.pdf_files: list[str] = initial_files or []
        
        self._setup_window()
        self._create_widgets()
        self._update_file_list()
        
        logger.info(f"PDF結合ウィンドウ初期化完了 - 初期ファイル数: {len(self.pdf_files)}")
    
    def _setup_window(self) -> None:
        """ウィンドウ設定"""
        self.title("PDF結合モード")
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
            text="PDF結合",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=(20, 0), pady=10)
        
        # ファイル数表示
        self.file_count_label = ctk.CTkLabel(
            header_frame,
            text="ファイル数: 0",
            font=ctk.CTkFont(size=14)
        )
        self.file_count_label.pack(side="right", padx=10, pady=10)
        
        # ドロップエリア/リストフレーム
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 説明ラベル
        instruction_label = ctk.CTkLabel(
            list_frame,
            text="PDFファイルをドラッグ&ドロップで追加 • ドラッグで順序変更 • 右クリックで削除",
            font=ctk.CTkFont(size=12)
        )
        instruction_label.pack(pady=(10, 5))
        
        # ファイルリスト（スクロール可能）
        self.file_listbox = ctk.CTkTextbox(
            list_frame,
            height=300,
            font=ctk.CTkFont(size=12)
        )
        self.file_listbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        # TODO: ドラッグ&ドロップ、順序変更機能実装（次のフェーズで実装）
        
        # ボタンフレーム
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # クリアボタン
        clear_button = ctk.CTkButton(
            button_frame,
            text="🗑️ 全クリア",
            height=40,
            command=self._clear_all_files
        )
        clear_button.pack(side="left", padx=10, pady=10)
        
        # ファイル追加ボタン（フォールバック用）
        add_button = ctk.CTkButton(
            button_frame,
            text="📂 PDFファイル追加",
            height=40,
            command=self._add_files
        )
        add_button.pack(side="left", padx=10, pady=10)
        
        # 結合ボタン
        self.combine_button = ctk.CTkButton(
            button_frame,
            text="📋 PDF結合実行",
            height=40,
            state="disabled" if len(self.pdf_files) == 0 else "normal",
            command=self._combine_files
        )
        self.combine_button.pack(side="right", padx=10, pady=10)
    
    def _update_file_list(self) -> None:
        """ファイルリスト表示更新"""
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("0.0", "end")
        
        if not self.pdf_files:
            self.file_listbox.insert("0.0", "PDFファイルがありません。\nファイルを追加してください。")
            self.file_count_label.configure(text="ファイル数: 0")
            self.combine_button.configure(state="disabled")
        else:
            content = "📋 結合順序:\n\n"
            for i, file_path in enumerate(self.pdf_files, 1):
                file_name = file_path.split("/")[-1].split("\\")[-1]  # ファイル名のみ表示
                content += f"{i}. {file_name}\n"
            
            self.file_listbox.insert("0.0", content)
            self.file_count_label.configure(text=f"ファイル数: {len(self.pdf_files)}")
            self.combine_button.configure(state="normal")
        
        self.file_listbox.configure(state="disabled")
    
    def _add_files(self) -> None:
        """ファイル追加ダイアログ"""
        # TODO: ファイル選択ダイアログの実装（次のフェーズで実装）
        logger.info("PDFファイル追加ダイアログ（未実装）")
        
        # デモ用: サンプルファイル追加
        sample_files = ["sample1.pdf", "sample2.pdf", "sample3.pdf"]
        self.pdf_files.extend(sample_files)
        self._update_file_list()
        logger.info(f"デモファイル追加: {sample_files}")
    
    def _clear_all_files(self) -> None:
        """全ファイルクリア（要件定義書 F-203）"""
        logger.info("ファイルリスト全クリア実行")
        self.pdf_files.clear()
        self._update_file_list()
    
    def _combine_files(self) -> None:
        """PDF結合実行"""
        if not self.pdf_files:
            logger.warning("結合対象ファイルなし")
            return
        
        # TODO: PDF結合処理の実装（次のフェーズで実装）
        logger.info(f"PDF結合処理開始 - 対象ファイル数: {len(self.pdf_files)}")
        
        # デモ用メッセージ
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("0.0", "end")
        self.file_listbox.insert("0.0", "PDF結合機能は次のフェーズで実装予定です。\n\n現在の結合対象:\n" + 
                                "\n".join([f"• {f}" for f in self.pdf_files]))
        self.file_listbox.configure(state="disabled")