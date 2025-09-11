"""
統合ウィンドウ - タブ形式UI
ユーザビリティ向上のための改善版
"""

import customtkinter as ctk
from typing import Optional, List
import time
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import asyncio
import threading
from pathlib import Path

from ..config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, 
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    UI_THEME, UI_COLOR_THEME,
    MAX_STARTUP_TIME_SECONDS,
    ALL_SUPPORTED_EXTENSIONS
)
from ..utils.logger import logger
from ..utils.drag_drop import drag_drop_handler
from ..utils.file_utils import FileScanner
from ..core.converter import PDFConverter
from ..core.combiner import PDFCombiner
from ..utils.error_handler import error_handler, ErrorSeverity


class UnifiedWindow:
    """統合ウィンドウクラス - タブ形式UI"""
    
    def __init__(self):
        self.startup_time = time.time()
        
        # CustomTkinter設定
        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)
        
        # メインウィンドウ作成
        self.root = ctk.CTk()
        self._setup_window()
        
        # コア機能
        self.pdf_converter = PDFConverter()
        self.pdf_combiner = PDFCombiner()
        
        # 状態管理
        self.conversion_files: List[str] = []
        self.combination_files: List[str] = []
        self.combination_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        # チェックボックス管理
        self.file_checkboxes = {}  # 変換用ファイルチェックボックス
        self.combine_checkboxes = {}  # 結合用ファイルチェックボックス
        
        # UI作成
        self._create_main_ui()
        self._setup_drag_drop()
        
        # エラーハンドラー設定
        error_handler.parent_window = self.root
        
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
        
        logger.info("統合ウィンドウ初期化完了")
    
    def _create_main_ui(self) -> None:
        """メインUI作成"""
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # タイトルバー
        title_frame = ctk.CTkFrame(self.main_frame)
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="📄 PDF変換・結合ツール",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)
        
        # タブビュー作成（450×700縦長ウィンドウに最適化）
        self.tab_view = ctk.CTkTabview(self.main_frame, width=410, height=620)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=5)
        
        # タブ追加
        self.conversion_tab = self.tab_view.add("PDF変換")
        self.combination_tab = self.tab_view.add("PDF結合")
        
        # 各タブのUI作成
        self._create_conversion_ui()
        self._create_combination_ui()
        
        # 初期タブ選択
        self.tab_view.set("PDF変換")
    
    def _create_conversion_ui(self) -> None:
        """PDF変換タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.conversion_tab,
            text="Office文書・画像ファイルをPDFに変換します",
            font=ctk.CTkFont(size=14)
        )
        desc_label.pack(pady=(10, 5))
        
        # ボタンフレーム（上部左側）
        conversion_btn_frame = ctk.CTkFrame(self.conversion_tab)
        conversion_btn_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        # ファイル選択ボタン
        self.conversion_select_btn = ctk.CTkButton(
            conversion_btn_frame,
            text="📂 ファイル選択",
            command=self._select_conversion_files,
            height=35,
            width=120  # 縦長ウィンドウに合わせて幅を調整
        )
        self.conversion_select_btn.pack(side="left", padx=8, pady=10)
        
        # 変換実行ボタン
        self.conversion_convert_btn = ctk.CTkButton(
            conversion_btn_frame,
            text="🔄 PDF変換開始",
            command=self._start_conversion,
            height=35,
            width=130,  # 縦長ウィンドウに合わせて幅を調整
            state="disabled"
        )
        self.conversion_convert_btn.pack(side="left", padx=(8, 0), pady=10)
        
        # クリアボタン
        self.conversion_clear_btn = ctk.CTkButton(
            conversion_btn_frame,
            text="🗑️ 選択クリア",
            command=self._clear_files,
            height=35,
            width=90,
            state="disabled"
        )
        self.conversion_clear_btn.pack(side="left", padx=(8, 0), pady=10)
        
        
        # ファイル数表示
        self.conversion_count_label = ctk.CTkLabel(
            conversion_btn_frame,
            text="ファイル数: 0",
            font=ctk.CTkFont(size=12)
        )
        self.conversion_count_label.pack(side="right", padx=10, pady=10)
        
        # ファイルリストエリア（チェックボックス付き）
        self.file_list_frame = ctk.CTkScrollableFrame(
            self.conversion_tab,
            height=300,  # 450×700ウィンドウに最適な高さ
            label_text="📁 変換対象ファイルリスト"
        )
        self.file_list_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # ファイルチェックボックスの管理
        self.file_checkboxes = {}  # {file_path: checkbox_widget}
        
        # 初期表示メッセージ
        self.initial_message_label = ctk.CTkLabel(
            self.file_list_frame,
            text="📁 ファイルをここにドラッグ&ドロップしてください\n\n対応ファイル:\n• Word: .docx, .doc\n• Excel: .xlsx, .xls (最初のシートのみPDF化)\n• PowerPoint: .pptx, .ppt\n• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff\n• PDF: .pdf (変換済フォルダにコピー)\n\n複数ファイルやフォルダもドロップできます",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        self.initial_message_label.pack(pady=20)
        
        
        # プログレスバー
        self.conversion_progress = ctk.CTkProgressBar(self.conversion_tab)
        self.conversion_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.conversion_progress.set(0)
        
        # ステータスラベル
        self.conversion_status = ctk.CTkLabel(
            self.conversion_tab,
            text="ファイルを追加してください",
            font=ctk.CTkFont(size=12)
        )
        self.conversion_status.pack(pady=(0, 10))
    
    def _create_combination_ui(self) -> None:
        """PDF結合タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.combination_tab,
            text="複数のPDFファイルを1つに結合します",
            font=ctk.CTkFont(size=14)
        )
        desc_label.pack(pady=(10, 5))
        
        # ファイルリストフレーム
        list_frame = ctk.CTkFrame(self.combination_tab)
        list_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # リスト操作ボタン
        list_btn_frame = ctk.CTkFrame(list_frame)
        list_btn_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.combination_select_btn = ctk.CTkButton(
            list_btn_frame,
            text="📂 PDFファイル追加",
            command=self._select_combination_files,
            height=30,
            width=130  # 縦長ウィンドウに合わせて幅を調整
        )
        self.combination_select_btn.pack(side="left")
        
        self.combination_clear_btn = ctk.CTkButton(
            list_btn_frame,
            text="🗑️ クリア", 
            command=self._clear_combination_files,
            height=30,
            width=70
        )
        self.combination_clear_btn.pack(side="left", padx=(8, 0))
        
        # 順番操作ボタン
        self.combination_move_up_btn = ctk.CTkButton(
            list_btn_frame,
            text="↑",
            command=self._move_combination_up,
            height=30,
            width=40
        )
        self.combination_move_up_btn.pack(side="left", padx=(8, 0))
        
        self.combination_move_down_btn = ctk.CTkButton(
            list_btn_frame,
            text="↓", 
            command=self._move_combination_down,
            height=30,
            width=40
        )
        self.combination_move_down_btn.pack(side="left", padx=(4, 0))
        
        self.combination_delete_btn = ctk.CTkButton(
            list_btn_frame,
            text="✕",
            command=self._delete_selected_combination,
            height=30,
            width=40
        )
        self.combination_delete_btn.pack(side="left", padx=(4, 0))
        
        # ファイル数表示
        self.combination_count_label = ctk.CTkLabel(
            list_btn_frame,
            text="ファイル数: 0",
            font=ctk.CTkFont(size=12)
        )
        self.combination_count_label.pack(side="right")
        
        # スクロール可能なファイルリスト（チェックボックス付き）
        self.combination_list_frame = ctk.CTkScrollableFrame(
            list_frame,
            height=280,  # 450×700ウィンドウに最適な高さ
            label_text="📋 PDFファイル結合リスト"
        )
        self.combination_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 初期メッセージ
        self.combination_list_msg = ctk.CTkLabel(
            self.combination_list_frame,
            text="📋 PDFファイルをドラッグ&ドロップまたは選択してください",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.combination_list_msg.pack(pady=20)
        
        # 結合実行ボタン
        self.combination_combine_btn = ctk.CTkButton(
            self.combination_tab,
            text="📋 PDF結合実行",
            command=self._start_combination,
            height=40,
            state="disabled"
        )
        self.combination_combine_btn.pack(pady=(0, 10))
        
        # プログレスバー
        self.combination_progress = ctk.CTkProgressBar(self.combination_tab)
        self.combination_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.combination_progress.set(0)
        
        # ステータスラベル
        self.combination_status = ctk.CTkLabel(
            self.combination_tab,
            text="PDFファイルを追加してください",
            font=ctk.CTkFont(size=12)
        )
        self.combination_status.pack(pady=(0, 10))
    
    def _setup_drag_drop(self) -> None:
        """ドラッグ&ドロップ機能設定"""
        try:
            # tkinterdnd2を使用したドラッグ&ドロップ設定を試行
            if drag_drop_handler.is_dnd_available:
                # 変換タブのドラッグ&ドロップ設定
                office_filter = drag_drop_handler.create_office_image_filter()
                drag_drop_handler.setup_drag_drop(
                    self.file_list_frame, 
                    self._add_conversion_files, 
                    office_filter
                )
                
                # 結合タブのドラッグ&ドロップ設定
                pdf_filter = drag_drop_handler.create_pdf_filter()
                drag_drop_handler.setup_drag_drop(
                    self.combination_list_frame, 
                    self._add_combination_files, 
                    pdf_filter
                )
                
                logger.info("ドラッグ&ドロップ機能設定完了")
            else:
                # tkinterdnd2が利用できない場合の代替実装
                self._setup_fallback_drag_drop()
                
        except Exception as e:
            logger.warning(f"ドラッグ&ドロップ設定失敗: {e}")
            logger.info("ファイル選択ボタンを使用してください")
    
    def _setup_fallback_drag_drop(self) -> None:
        """代替ドラッグ&ドロップ実装"""
        try:
            # ドロップヒントのみを追加
            self._add_drop_hints()
            logger.info("代替ドラッグ&ドロップ機能設定完了")
        except Exception as e:
            logger.warning(f"代替ドラッグ&ドロップ設定失敗: {e}")
    
    def _add_drop_hints(self) -> None:
        """ドロップヒント表示"""
        # 変換タブにヒント表示
        conversion_hint = """📁 対応ファイル形式:
        
• Word文書 (.docx, .doc)
• Excel文書 (.xlsx, .xls)  
• PowerPoint文書 (.pptx, .ppt)
• 画像ファイル (.jpg, .png, .bmp, .gif, .tiff)

ファイル選択ボタンでファイルを追加してください"""
        
        # 結合タブにヒント表示
        combination_hint = """📋 PDFファイル結合:
        
• PDFファイルのみ対応 (.pdf)
• ファイルの順序が結合順序になります
• 複数ファイルの一括追加に対応

ファイル選択ボタンでPDFを追加してください"""
    
    
    def _add_conversion_files(self, paths: List[str]) -> None:
        """変換ファイル追加"""
        scan_result = FileScanner.scan_files_from_paths(paths)
        valid_files = scan_result['valid']
        
        if valid_files:
            # 重複を避けるために新しいファイルのみ追加
            new_files = [f for f in valid_files if f not in self.conversion_files]
            if new_files:
                self.conversion_files.extend(new_files)
                
                # 新しいファイルのチェックボックスを作成
                for file_path in new_files:
                    filename = Path(file_path).name
                    checkbox = ctk.CTkCheckBox(
                        self.file_list_frame,
                        text=filename,
                        font=ctk.CTkFont(size=11)
                    )
                    checkbox.pack(anchor="w", pady=2, padx=10)
                    self.file_checkboxes[file_path] = checkbox
                
                self._update_conversion_display()
                logger.info(f"変換ファイル追加: {len(new_files)}個")
            else:
                self.conversion_status.configure(text="選択されたファイルは既に追加済みです")
        else:
            self.conversion_status.configure(text="対応ファイルが見つかりませんでした")
    
    def _add_combination_files(self, paths: List[str]) -> None:
        """結合ファイル追加（PDF専用）"""
        pdf_files = [p for p in paths if Path(p).suffix.lower() == '.pdf' and Path(p).is_file()]
        
        if pdf_files:
            # 重複を避けるために新しいファイルのみ追加
            new_files = [f for f in pdf_files if f not in self.combination_files]
            if new_files:
                self.combination_files.extend(new_files)
                
                # 新しいファイルのチェックボックスを作成
                for file_path in new_files:
                    filename = Path(file_path).name
                    checkbox = ctk.CTkCheckBox(
                        self.combination_list_frame,
                        text=filename,
                        font=ctk.CTkFont(size=11)
                    )
                    checkbox.pack(anchor="w", pady=2, padx=10)
                    self.combination_checkboxes[file_path] = checkbox
                
                self._update_combination_display()
                logger.info(f"結合ファイル追加: {len(new_files)}個")
            else:
                logger.info("重複ファイルのため追加されませんでした")
        else:
            self.combination_status.configure(text="PDFファイルが見つかりませんでした")
    
    def _select_conversion_files(self) -> None:
        """変換ファイル選択ダイアログ"""
        filetypes = [
            ("対応ファイル", " ".join([f"*{ext}" for ext in ALL_SUPPORTED_EXTENSIONS])),
            ("Word文書", "*.docx *.doc"),
            ("Excel文書", "*.xlsx *.xls"),
            ("PowerPoint文書", "*.pptx *.ppt"),
            ("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("すべてのファイル", "*.*")
        ]
        
        files = fd.askopenfilenames(
            title="変換するファイルを選択",
            filetypes=filetypes
        )
        
        if files:
            self._add_conversion_files(list(files))
    
    def _select_combination_files(self) -> None:
        """結合ファイル選択ダイアログ"""
        files = fd.askopenfilenames(
            title="結合するPDFファイルを選択",
            filetypes=[("PDFファイル", "*.pdf"), ("すべてのファイル", "*.*")]
        )
        
        if files:
            self._add_combination_files(list(files))
    
    def _update_conversion_display(self) -> None:
        """変換タブ表示更新"""
        # ファイル数表示更新
        self.conversion_count_label.configure(text=f"ファイル数: {len(self.conversion_files)}")
        
        if self.conversion_files:
            # 初期メッセージを非表示にして、ファイルリストを表示
            self.initial_message_label.configure(text=f"📁 変換対象ファイル ({len(self.conversion_files)}個)")
            self.conversion_convert_btn.configure(state="normal")
            self.conversion_clear_btn.configure(state="normal")
            self.conversion_status.configure(text=f"{len(self.conversion_files)}個のファイルが追加されました")
        else:
            # ファイルがない場合は初期メッセージを表示
            self.initial_message_label.configure(text="📁 ファイルをここにドラッグ&ドロップしてください\n\n対応ファイル:\n• Word: .docx, .doc\n• Excel: .xlsx, .xls (最初のシートのみPDF化)\n• PowerPoint: .pptx, .ppt\n• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff\n• PDF: .pdf (変換済フォルダにコピー)\n\n複数ファイルやフォルダもドロップできます")
            self.conversion_convert_btn.configure(state="disabled")
            self.conversion_clear_btn.configure(state="disabled")
            
            # ファイルがない場合は全てのチェックボックスを削除
            if hasattr(self, 'file_checkboxes') and self.file_checkboxes:
                for checkbox in self.file_checkboxes.values():
                    checkbox.destroy()
                self.file_checkboxes.clear()
            self.conversion_status.configure(text="変換するファイルを追加してください")
    
    def _update_combination_display(self) -> None:
        """結合タブ表示更新"""
        if self.combination_files:
            # メッセージを非表示にして、ファイル数を更新
            self.combination_list_msg.configure(text=f"📋 {len(self.combination_files)}個のPDFファイルが選択されています")
            self.combination_combine_btn.configure(state="normal")
            self.combination_count_label.configure(text=f"ファイル数: {len(self.combination_files)}")
            self.combination_status.configure(text=f"{len(self.combination_files)}個のPDFファイルが追加されました")
        else:
            # ファイルがない場合は初期メッセージを表示
            self.combination_list_msg.configure(text="📋 PDFファイルをドラッグ&ドロップまたは選択してください")
            # 全てのチェックボックスを削除
            for checkbox in self.combination_checkboxes.values():
                checkbox.destroy()
            self.combination_checkboxes.clear()
            self.combination_combine_btn.configure(state="disabled")
            self.combination_count_label.configure(text="ファイル数: 0")
            self.combination_status.configure(text="PDFファイルを追加してください")
    
    def _clear_combination_files(self) -> None:
        """結合ファイルクリア"""
        self.combination_files.clear()
        # 全てのチェックボックスを削除
        for checkbox in self.combination_checkboxes.values():
            checkbox.destroy()
        self.combination_checkboxes.clear()
        self._update_combination_display()
        
        self.combination_combine_btn.configure(state="disabled")
        self.combination_count_label.configure(text="ファイル数: 0")
        self.combination_status.configure(text="PDFファイルを追加してください")
        
        logger.info("結合ファイルリストクリア")
    
    def _move_combination_up(self) -> None:
        """選択したPDFファイルを上に移動"""
        try:
            selected_files = []
            for file_path, checkbox in self.combination_checkboxes.items():
                if checkbox.get():
                    selected_files.append(file_path)
            
            if not selected_files:
                self.combination_status.configure(text="移動するファイルを選択してください")
                return
            
            moved = False
            for file_path in selected_files:
                current_index = self.combination_files.index(file_path)
                if current_index > 0:
                    # ファイルリスト内で上に移動
                    self.combination_files[current_index], self.combination_files[current_index - 1] = \
                        self.combination_files[current_index - 1], self.combination_files[current_index]
                    moved = True
            
            if moved:
                self._refresh_combination_checkboxes()
                self.combination_status.configure(text="ファイルを上に移動しました")
                logger.info(f"{len(selected_files)}件のファイルを上に移動")
            else:
                self.combination_status.configure(text="これ以上上に移動できません")
                
        except Exception as e:
            logger.error(f"ファイル上移動中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="移動中にエラーが発生しました")
    
    def _move_combination_down(self) -> None:
        """選択したPDFファイルを下に移動"""
        try:
            selected_files = []
            for file_path, checkbox in self.combination_checkboxes.items():
                if checkbox.get():
                    selected_files.append(file_path)
            
            if not selected_files:
                self.combination_status.configure(text="移動するファイルを選択してください")
                return
            
            moved = False
            # 下に移動する場合は逆順で処理（後ろから前へ）
            for file_path in reversed(selected_files):
                current_index = self.combination_files.index(file_path)
                if current_index < len(self.combination_files) - 1:
                    # ファイルリスト内で下に移動
                    self.combination_files[current_index], self.combination_files[current_index + 1] = \
                        self.combination_files[current_index + 1], self.combination_files[current_index]
                    moved = True
            
            if moved:
                self._refresh_combination_checkboxes()
                self.combination_status.configure(text="ファイルを下に移動しました")
                logger.info(f"{len(selected_files)}件のファイルを下に移動")
            else:
                self.combination_status.configure(text="これ以上下に移動できません")
                
        except Exception as e:
            logger.error(f"ファイル下移動中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="移動中にエラーが発生しました")
    
    def _delete_selected_combination(self) -> None:
        """選択したPDFファイルを削除"""
        try:
            selected_files = []
            for file_path, checkbox in self.combination_checkboxes.items():
                if checkbox.get():
                    selected_files.append(file_path)
            
            if not selected_files:
                self.combination_status.configure(text="削除するファイルを選択してください")
                return
            
            # 確認ダイアログ
            import tkinter.messagebox as messagebox
            if messagebox.askyesno("確認", f"{len(selected_files)}件の選択されたファイルを削除しますか？"):
                # 選択されたファイルを削除
                for file_path in selected_files:
                    if file_path in self.combination_files:
                        self.combination_files.remove(file_path)
                    if file_path in self.combination_checkboxes:
                        self.combination_checkboxes[file_path].destroy()
                        del self.combination_checkboxes[file_path]
                
                self._update_combination_display()
                self.combination_status.configure(text=f"{len(selected_files)}件のファイルを削除しました")
                logger.info(f"{len(selected_files)}件のPDFファイルを削除しました")
            
        except Exception as e:
            logger.error(f"ファイル削除中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="削除中にエラーが発生しました")
    
    def _refresh_combination_checkboxes(self) -> None:
        """PDFファイルのチェックボックス表示順を更新"""
        try:
            # 全てのチェックボックスを一時的に削除
            checkbox_states = {}
            for file_path, checkbox in self.combination_checkboxes.items():
                checkbox_states[file_path] = checkbox.get()  # 状態を保存
                checkbox.destroy()
            
            self.combination_checkboxes.clear()
            
            # ファイルリストの順序に従って再作成
            for file_path in self.combination_files:
                filename = Path(file_path).name
                checkbox = ctk.CTkCheckBox(
                    self.combination_list_frame,
                    text=filename,
                    font=ctk.CTkFont(size=11)
                )
                checkbox.pack(anchor="w", pady=2, padx=10)
                
                # 以前の状態を復元
                if file_path in checkbox_states and checkbox_states[file_path]:
                    checkbox.select()
                    
                self.combination_checkboxes[file_path] = checkbox
            
        except Exception as e:
            logger.error(f"チェックボックス更新中にエラーが発生: {str(e)}")
    
    def _clear_files(self) -> None:
        """変換ファイルクリア（選択削除機能付き）"""
        try:
            # チェックボックスが存在する場合の選択削除機能
            if hasattr(self, 'file_checkboxes') and self.file_checkboxes:
                selected_files = []
                for file_path, checkbox in self.file_checkboxes.items():
                    if checkbox.get():
                        selected_files.append(file_path)
                
                if selected_files:
                    # 選択されたファイルのみ削除
                    for file_path in selected_files:
                        if file_path in self.conversion_files:
                            self.conversion_files.remove(file_path)
                        if file_path in self.file_checkboxes:
                            self.file_checkboxes[file_path].destroy()
                            del self.file_checkboxes[file_path]
                    logger.info(f"選択ファイル削除: {len(selected_files)}個")
                else:
                    # 全ファイルクリア（確認ダイアログ付き）
                    if self.conversion_files:
                        result = self._show_confirmation_dialog("全ファイルクリア", 
                            f"全{len(self.conversion_files)}件のファイルをクリアしますか？")
                        if result:
                            self.conversion_files.clear()
                            if hasattr(self, 'file_checkboxes'):
                                for checkbox in self.file_checkboxes.values():
                                    checkbox.destroy()
                                self.file_checkboxes.clear()
                            logger.info("全変換ファイルをクリア")
                        else:
                            return
            else:
                # チェックボックスがない場合は全クリア
                if self.conversion_files:
                    result = self._show_confirmation_dialog("ファイルクリア", 
                        f"{len(self.conversion_files)}件のファイルをクリアしますか？")
                    if result:
                        self.conversion_files.clear()
                        logger.info("変換ファイル全クリア")
                    else:
                        return
            
            # UI更新
            self._update_conversion_display()
            self.conversion_status.configure(text="ファイルリストをクリアしました")
            
        except Exception as e:
            logger.error(f"ファイルクリア中にエラー: {str(e)}")
            error_handler.handle_error(e, ErrorSeverity.WARNING, "ファイルクリア処理")
    
    def _start_conversion(self) -> None:
        """PDF変換開始"""
        if not self.conversion_files:
            return
        
        # UIを無効化
        self.conversion_convert_btn.configure(state="disabled")
        self.conversion_status.configure(text="変換処理中...")
        self.conversion_progress.set(0)
        
        # 別スレッドで変換実行
        thread = threading.Thread(target=self._run_conversion)
        thread.daemon = True
        thread.start()
    
    def _run_conversion(self) -> None:
        """変換実行（別スレッド） - 順次処理でRPCエラーを回避"""
        try:
            files_to_convert = self.conversion_files.copy()
            total_files = len(files_to_convert)
            results = []
            
            for index, file_path in enumerate(files_to_convert):
                # 進捗更新
                progress = (index + 0.5) / total_files  # 処理開始時の進捗
                status_text = f"変換中: {index + 1}/{total_files} - {Path(file_path).name}"
                self.root.after(0, lambda p=progress, s=status_text: self._update_conversion_progress(p, s))
                
                # 単一ファイル変換（順次処理）
                result = self.pdf_converter._convert_single_file(file_path)
                results.append(result)
                
                # 完了時の進捗更新
                progress = (index + 1) / total_files
                success_status = "● 成功" if result.success else "× 失敗"
                status_text = f"{success_status}: {Path(file_path).name}"
                self.root.after(0, lambda p=progress, s=status_text: self._update_conversion_progress(p, s))
                
                # COM APIリソースの適切な解放のための待機
                import time
                time.sleep(0.5)  # RPCエラー防止のための適切な間隔
            
            # UI更新（メインスレッドで実行）
            self.root.after(0, lambda: self._on_conversion_complete(results))
            
        except Exception as e:
            logger.error(f"変換処理中のエラー: {str(e)}", exc_info=True)
            self.root.after(0, lambda: error_handler.handle_error(
                e, ErrorSeverity.CRITICAL, "PDF変換", f"変換処理中にエラーが発生しました: {str(e)}"
            ))
            self.root.after(0, self._reset_conversion_ui)
    
    def _update_conversion_progress(self, progress: float, status: str) -> None:
        """変換進捗の更新"""
        self.conversion_progress.set(progress)
        self.conversion_status.configure(text=status)
        self.root.update_idletasks()  # UI即座更新
    
    def _on_conversion_complete(self, results) -> None:
        """変換完了処理"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        self.conversion_progress.set(1.0)
        
        if successful:
            message = f"変換完了: 成功 {len(successful)}個"
            if failed:
                message += f", 失敗 {len(failed)}個"
            
            self.conversion_status.configure(text=message)
            
            # 結合確認ダイアログ（2つ以上成功した場合）
            if len(successful) >= 2:
                self._show_combination_offer([r.target_path for r in successful])
        else:
            self.conversion_status.configure(text=f"変換失敗: {len(failed)}個のファイルで問題が発生")
        
        # UI有効化
        self.conversion_convert_btn.configure(state="normal")
    
    def _show_combination_offer(self, pdf_files: List[str]) -> None:
        """結合提案ダイアログ"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("PDF結合")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 中央配置
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        dialog.geometry(f"350x150+{x}+{y}")
        
        # メッセージ
        msg_label = ctk.CTkLabel(
            dialog,
            text=f"変換したPDFファイル({len(pdf_files)}個)を\n結合しますか？",
            font=ctk.CTkFont(size=14)
        )
        msg_label.pack(pady=20)
        
        # ボタンフレーム
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        def on_yes():
            dialog.destroy()
            self.combination_files.extend(pdf_files)
            self._update_combination_display()
            self.tab_view.set("PDF結合")
        
        def on_no():
            dialog.destroy()
        
        yes_btn = ctk.CTkButton(btn_frame, text="はい", command=on_yes, width=80)
        yes_btn.pack(side="left", padx=10)
        
        no_btn = ctk.CTkButton(btn_frame, text="いいえ", command=on_no, width=80)
        no_btn.pack(side="left", padx=10)
    
    def _start_combination(self) -> None:
        """PDF結合開始"""
        if not self.combination_files:
            return
        
        # 保存先選択
        output_path = fd.asksaveasfilename(
            title="結合PDFの保存先を選択",
            filetypes=[("PDFファイル", "*.pdf")],
            defaultextension=".pdf"
        )
        
        if not output_path:
            return
        
        # UIを無効化
        self.combination_combine_btn.configure(state="disabled")
        self.combination_status.configure(text="結合処理中...")
        self.combination_progress.set(0)
        
        # 別スレッドで結合実行
        thread = threading.Thread(target=self._run_combination, args=(output_path,))
        thread.daemon = True
        thread.start()
    
    def _run_combination(self, output_path: str) -> None:
        """結合実行（別スレッド）"""
        try:
            def progress_callback(message, progress):
                self.root.after(0, lambda: self.combination_progress.set(progress / 100))
                self.root.after(0, lambda: self.combination_status.configure(text=message))
            
            result = self.pdf_combiner.combine_pdfs(
                self.combination_files.copy(),
                output_path,
                progress_callback
            )
            
            # UI更新
            self.root.after(0, lambda: self._on_combination_complete(result))
            
        except Exception as e:
            self.root.after(0, lambda: error_handler.handle_error(
                e, ErrorSeverity.CRITICAL, "PDF結合"
            ))
            self.root.after(0, self._reset_combination_ui)
    
    def _on_combination_complete(self, result) -> None:
        """結合完了処理"""
        self.combination_progress.set(1.0)
        
        if result.success:
            self.combination_status.configure(
                text=f"結合完了: {result.total_pages}ページ ({len(result.processed_files)}ファイル)"
            )
        else:
            self.combination_status.configure(text=f"結合失敗: {result.error_message}")
        
        # UI有効化
        self.combination_combine_btn.configure(state="normal")
    
    def _reset_conversion_ui(self) -> None:
        """変換UI リセット"""
        self.conversion_convert_btn.configure(state="normal")
        self.conversion_progress.set(0)
        self.conversion_status.configure(text="エラーが発生しました")
    
    def _reset_combination_ui(self) -> None:
        """結合UI リセット"""
        self.combination_combine_btn.configure(state="normal")
        self.combination_progress.set(0)
        self.combination_status.configure(text="エラーが発生しました")
    
    def _log_startup_time(self) -> None:
        """起動時間ログ"""
        startup_duration = time.time() - self.startup_time
        
        if startup_duration <= MAX_STARTUP_TIME_SECONDS:
            logger.info(f"起動時間: {startup_duration:.2f}秒 (要件内)")
        else:
            logger.warning(f"起動時間超過: {startup_duration:.2f}秒")
    
    def _show_confirmation_dialog(self, title: str, message: str) -> bool:
        """確認ダイアログ表示"""
        return messagebox.askyesno(title, message)
    
    def _on_closing(self) -> None:
        """アプリケーション終了処理"""
        logger.info("アプリケーション終了処理開始")
        
        if hasattr(self, 'pdf_converter'):
            self.pdf_converter.cleanup()
        
        self.root.quit()
        self.root.destroy()
    
    def run(self) -> None:
        """アプリケーション実行"""
        logger.info("統合アプリケーション実行開始")
        self.root.mainloop()