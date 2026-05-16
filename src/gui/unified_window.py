"""
統合ウィンドウ - タブ形式UI
ユーザビリティ向上のための改善版
"""

import customtkinter as ctk
from typing import Optional, List, Dict
import time
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import asyncio
import threading
from pathlib import Path
import sys
import subprocess
import os

try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None

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
from ..utils.security import SecurityValidator, InputValidator
from .draggable_list import DraggableFileList
from .theme import (
    CLR_PRIMARY, CLR_ACCENT, CLR_LIGHT_BG, CLR_LIGHT_BORDER,
    CLR_SEL_BORDER, CLR_TOOLBAR_BG, CLR_BORDER, CLR_RED_LIGHT,
    CLR_RED_TEXT, CLR_GRAY_TEXT, CLR_DARK_TEXT, CLR_LIST_HEADER,
    CLR_WHITE, get_file_type_badge,
    FONT_FAMILY,
    TAB_CONVERSION, TAB_COMBINATION, TAB_DOCUMENT, TAB_INACTIVE,
)
from ..utils.error_handler import error_handler, ErrorSeverity
from ..core.converter import PDFConverter
from ..core.combiner import PDFCombiner


class DndCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if TkinterDnD is not None:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception as e:
                logger.error(f"TkinterDnD初期化エラー: {e}")
                self.TkdndVersion = None
        else:
            self.TkdndVersion = None


class UnifiedWindow:
    """統合ウィンドウクラス - タブ形式UI"""

    def __init__(self):
        self.startup_time = time.time()

        # CustomTkinter設定
        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)

        # メインウィンドウ作成
        self.root = DndCTk()
        self._setup_window()

        # コア機能
        self.pdf_converter = PDFConverter()
        self.pdf_combiner = PDFCombiner()
        
        # 状態管理
        self.conversion_files: List[str] = []
        self.combination_files: List[str] = []
        self.document_number_files: List[str] = []  # 資料NO挿入用ファイル（旧式、互換性のため残す）

        # オプション管理
        self.split_excel_sheets_var = ctk.BooleanVar(value=False)

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
        self.main_frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray10"))
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # ── ヘッダー ──
        header_frame = ctk.CTkFrame(
            self.main_frame, fg_color=CLR_PRIMARY, corner_radius=8
        )
        header_frame.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            header_frame,
            text="PDF変換・結合ツール",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=10)

        # ── カスタムタブバー ──
        _TAB_DEFS = [
            ("PDF変換",   TAB_CONVERSION),
            ("PDF結合",   TAB_COMBINATION),
            ("資料NO挿入", TAB_DOCUMENT),
        ]
        self._tab_active_colors = {name: colors for name, colors in _TAB_DEFS}
        self._tab_buttons: dict = {}
        self._tab_frames: dict = {}

        tab_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        tab_bar.pack(fill="x", padx=8, pady=(0, 0))

        for name, (active, hover) in _TAB_DEFS:
            btn = ctk.CTkButton(
                tab_bar, text=name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                height=46, corner_radius=0,
                fg_color=TAB_INACTIVE[0], hover_color=TAB_INACTIVE[1],
                border_spacing=0,
                command=lambda n=name: self._switch_tab(n)
            )
            btn.pack(side="left", fill="x", expand=True, padx=1, pady=0)
            self._tab_buttons[name] = btn

        # ── コンテンツエリア ──
        content_outer = ctk.CTkFrame(
            self.main_frame, fg_color=CLR_BORDER, corner_radius=0,
            border_width=0
        )
        content_outer.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for name, _ in _TAB_DEFS:
            frame = ctk.CTkFrame(
                content_outer, fg_color=("gray97", "gray15"),
                corner_radius=0
            )
            frame.pack_forget()
            self._tab_frames[name] = frame

        self.conversion_tab      = self._tab_frames["PDF変換"]
        self.combination_tab     = self._tab_frames["PDF結合"]
        self.document_number_tab = self._tab_frames["資料NO挿入"]

        # 各タブのUI作成
        self._create_conversion_ui()
        self._create_combination_ui()
        self._create_document_number_ui()

        # 初期タブ選択
        self._switch_tab("PDF変換")

    def _switch_tab(self, name: str) -> None:
        """タブ切り替え"""
        colors = self._tab_active_colors
        inactive_c, inactive_h = TAB_INACTIVE
        for n, btn in self._tab_buttons.items():
            if n == name:
                active_c, active_h = colors[n]
                btn.configure(fg_color=active_c, hover_color=active_h)
            else:
                btn.configure(fg_color=inactive_c, hover_color=inactive_h)
        for n, frame in self._tab_frames.items():
            if n == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
    
    def _create_conversion_ui(self) -> None:
        """PDF変換タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.conversion_tab,
            text="Office文書・画像ファイルをPDFに変換します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        desc_label.pack(pady=(10, 5))
        
        # ── ツールバー ──
        toolbar = ctk.CTkFrame(self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
                                border_width=1, border_color=CLR_BORDER, corner_radius=6)
        toolbar.pack(fill="x", padx=15, pady=(8, 5))

        self.conversion_select_btn = ctk.CTkButton(
            toolbar, text="ファイル追加",
            command=self._select_conversion_files,
            height=32, width=110,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        self.conversion_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.conversion_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_conversion,
            height=32, width=90,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            state="disabled"
        )
        self.conversion_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_clear_btn = ctk.CTkButton(
            toolbar, text="全クリア",
            command=self._clear_all_conversion,
            height=32, width=80,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            state="disabled"
        )
        self.conversion_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_GRAY_TEXT
        )
        self.conversion_count_label.pack(side="right", padx=10, pady=6)
        
        # ファイルリスト（DraggableFileList・ドラッグ無効）
        self.conversion_draggable_list = DraggableFileList(
            self.conversion_tab,
            drag_enabled=False,
            height=200,
            label_text="📁 変換対象ファイルリスト"
        )
        self.conversion_draggable_list.pack(fill="both", expand=True, padx=15, pady=8)
        self.conversion_draggable_list.on_selection_change = self._on_conversion_selection_change

        # 初期表示メッセージ
        self.initial_message_label = ctk.CTkLabel(
            self.conversion_draggable_list,
            text=(
                "📁 ファイルをここにドラッグ&ドロップしてください\n\n"
                "対応ファイル:\n"
                "• Word: .docx, .doc\n"
                "• Excel: .xlsx, .xls\n"
                "• PowerPoint: .pptx, .ppt\n"
                "• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff\n"
                "• PDF: .pdf （変換済フォルダにコピー）\n\n"
                "複数ファイルやフォルダもドロップできます"
            ),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            justify="left"
        )
        self.initial_message_label.pack(fill="both", expand=True, padx=20, pady=20)

        # Excelシート分割オプション
        self.excel_options_frame = ctk.CTkFrame(
            self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        self.excel_options_frame.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(
            self.excel_options_frame,
            text="Excelのシートを個別のPDFに分割する",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_DARK_TEXT
        ).pack(side="left", padx=(10, 8), pady=6)

        self.split_excel_sheets_switch = ctk.CTkSwitch(
            self.excel_options_frame, text="",
            variable=self.split_excel_sheets_var,
            onvalue=True, offvalue=False,
            progress_color=CLR_PRIMARY
        )
        self.split_excel_sheets_switch.pack(side="right", padx=10, pady=6)
        
        



        # 変換実行ボタン
        self.conversion_convert_btn = ctk.CTkButton(
            self.conversion_tab,
            text="🔄 PDF変換開始",
            command=self._start_conversion,
            height=40,
            state="disabled"
        )
        self.conversion_convert_btn.pack(pady=(10, 10))

        # プログレスバー
        self.conversion_progress = ctk.CTkProgressBar(self.conversion_tab)
        self.conversion_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.conversion_progress.set(0)
        
        # ステータスラベル
        self.conversion_status = ctk.CTkLabel(
            self.conversion_tab,
            text="ファイルを追加してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.conversion_status.pack(pady=(0, 10))
    
    def _create_combination_ui(self) -> None:
        """PDF結合タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.combination_tab,
            text="複数のPDFファイルを1つに結合します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        desc_label.pack(pady=(10, 5))
        
        # ── ツールバー ──
        toolbar = ctk.CTkFrame(self.combination_tab, fg_color=CLR_TOOLBAR_BG,
                                border_width=1, border_color=CLR_BORDER, corner_radius=6)
        toolbar.pack(fill="x", padx=15, pady=(8, 5))

        self.combination_select_btn = ctk.CTkButton(
            toolbar, text="PDF追加",
            command=self._select_combination_files,
            height=32, width=90,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        self.combination_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.combination_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_combination,
            height=32, width=80,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            state="disabled"
        )
        self.combination_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_clear_btn = ctk.CTkButton(
            toolbar, text="クリア",
            command=self._clear_combination_files,
            height=32, width=70,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            state="disabled"
        )
        self.combination_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_move_up_btn = ctk.CTkButton(
            toolbar, text="↑", command=self._move_combination_up,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
        )
        self.combination_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

        self.combination_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_combination_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
        )
        self.combination_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_GRAY_TEXT
        )
        self.combination_count_label.pack(side="right", padx=10, pady=6)
        
        # ドラッグアンドドロップ対応ファイルリスト
        self.combination_draggable_list = DraggableFileList(
            self.combination_tab,
            height=200,
            label_text="📋 PDFファイル結合リスト（ドラッグで並び替え可能）"
        )
        self.combination_draggable_list.pack(fill="both", expand=True, padx=15, pady=8)

        # ドラッグリストのコールバック設定
        self.combination_draggable_list.on_selection_change = self._on_combination_selection_change
        self.combination_draggable_list.on_order_change = self._on_combination_order_change

        # 初期メッセージ（空の時に表示）
        self.combination_list_msg = ctk.CTkLabel(
            self.combination_draggable_list,
            text="📋 PDFファイルをここにドラッグ&ドロップしてください\n\n・複数PDFファイルの結合に対応\n・ファイルリストの順序で結合されます\n・ドラッグで順序変更、↑↓ボタンでも調整可能",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            justify="left"
        )
        self.combination_list_msg.pack(fill="both", expand=True, padx=20, pady=20)

        # オプションフレーム（白紙挿入 + ページ番号）
        self.add_blank_page_var = ctk.BooleanVar()
        self.add_page_number_var = ctk.BooleanVar()

        options_frame = ctk.CTkFrame(
            self.combination_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        options_frame.pack(fill="x", padx=15, pady=(0, 5))

        # 白紙挿入スイッチ
        blank_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        blank_row.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(
            blank_row, text="奇数ページのPDF末尾に白紙ページを挿入する",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_DARK_TEXT
        ).pack(side="left")

        self.add_blank_page_switch = ctk.CTkSwitch(
            blank_row, text="", variable=self.add_blank_page_var,
            onvalue=True, offvalue=False, progress_color=CLR_PRIMARY
        )
        self.add_blank_page_switch.pack(side="right")

        # ページ番号スイッチ
        page_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        page_row.pack(fill="x", padx=8, pady=(2, 6))

        ctk.CTkLabel(
            page_row, text="フッター中央にページ番号を挿入する",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_DARK_TEXT
        ).pack(side="left")

        self.add_page_number_switch = ctk.CTkSwitch(
            page_row, text="", variable=self.add_page_number_var,
            onvalue=True, offvalue=False, progress_color=CLR_PRIMARY,
            command=self._toggle_page_number_options
        )
        self.add_page_number_switch.pack(side="right", padx=(8, 0))

        # 開始ページ・開始番号（インライン）
        self.start_page_label = ctk.CTkLabel(
            page_row, text="開始ページ:", font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.start_page_label.pack(side="right", padx=(8, 2))

        self.start_page_var = ctk.StringVar(value="1")
        self.start_page_entry = ctk.CTkEntry(
            page_row, textvariable=self.start_page_var, width=40
        )
        self.start_page_entry.pack(side="right")

        self.start_number_label = ctk.CTkLabel(
            page_row, text="開始番号:", font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.start_number_label.pack(side="right", padx=(8, 2))

        self.start_number_var = ctk.StringVar(value="1")
        self.start_number_entry = ctk.CTkEntry(
            page_row, textvariable=self.start_number_var, width=40
        )
        self.start_number_entry.pack(side="right")

        self._toggle_page_number_options()
        
        # 結合実行ボタン
        self.combination_combine_btn = ctk.CTkButton(
            self.combination_tab,
            text="📋 PDF結合実行",
            command=self._start_combination,
            height=40,
            state="disabled"
        )
        self.combination_combine_btn.pack(pady=(10, 10))
        
        # プログレスバー
        self.combination_progress = ctk.CTkProgressBar(self.combination_tab)
        self.combination_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.combination_progress.set(0)
        
        # ステータスラベル
        self.combination_status = ctk.CTkLabel(
            self.combination_tab,
            text="PDFファイルを追加してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.combination_status.pack(pady=(0, 10))

    def _create_document_number_ui(self) -> None:
        """資料NO挿入タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルのヘッダー右上に「資料〇」を挿入します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        desc_label.pack(pady=(10, 5))

        # 連番設定フレーム
        numbering_frame = ctk.CTkFrame(self.document_number_tab)
        numbering_frame.pack(fill="x", padx=15, pady=(10, 5))

        # 連番タイプ選択
        type_label = ctk.CTkLabel(
            numbering_frame,
            text="連番タイプ:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        )
        type_label.pack(side="left", padx=(10, 5), pady=10)

        self.numbering_type_var = ctk.StringVar(value="任意No")
        self.numbering_type_menu = ctk.CTkOptionMenu(
            numbering_frame,
            variable=self.numbering_type_var,
            values=["任意No", "連番", "ハイフン連番"],
            width=150,
            command=self._on_numbering_type_changed
        )
        self.numbering_type_menu.pack(side="left", padx=(0, 10), pady=10)

        # 開始番号/プレフィックス入力
        self.number_label = ctk.CTkLabel(
            numbering_frame,
            text="開始番号:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.number_label.pack(side="left", padx=(10, 5), pady=10)

        self.number_var = ctk.StringVar(value="1")
        self.number_entry = ctk.CTkEntry(
            numbering_frame,
            textvariable=self.number_var,
            placeholder_text="1",
            width=80,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.number_entry.pack(side="left", padx=(0, 10), pady=10)

        # 入力値が変更された時の処理
        self.number_var.trace("w", self._on_numbering_settings_changed)

        # プレビューラベル
        self.preview_label = ctk.CTkLabel(
            numbering_frame,
            text="→ 「資料1, 資料2, 資料3...」",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="gray"
        )
        self.preview_label.pack(side="left", padx=(0, 10), pady=10)

        # ── ツールバー ──
        toolbar = ctk.CTkFrame(self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
                                border_width=1, border_color=CLR_BORDER, corner_radius=6)
        toolbar.pack(fill="x", padx=15, pady=(8, 5))

        self.document_select_btn = ctk.CTkButton(
            toolbar, text="PDFファイル選択",
            command=self._select_document_number_files,
            height=32, width=120,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        self.document_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.document_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_document,
            height=32, width=80,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            state="disabled"
        )
        self.document_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_clear_btn = ctk.CTkButton(
            toolbar, text="クリア",
            command=self._clear_document_number_files,
            height=32, width=70,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            state="disabled"
        )
        self.document_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_move_up_btn = ctk.CTkButton(
            toolbar, text="↑", command=self._move_document_up,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
        )
        self.document_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

        self.document_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_document_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
        )
        self.document_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=CLR_GRAY_TEXT
        )
        self.document_count_label.pack(side="right", padx=10, pady=6)

        # ドラッグアンドドロップ対応ファイルリスト
        self.document_draggable_list = DraggableFileList(
            self.document_number_tab,
            height=200,
            label_text="📋 資料NO挿入対象ファイルリスト（ドラッグで並び替え可能）"
        )
        self.document_draggable_list.pack(fill="both", expand=True, padx=15, pady=8)

        # ドラッグリストのコールバック設定
        self.document_draggable_list.on_selection_change = self._on_document_selection_change
        self.document_draggable_list.on_order_change = self._on_document_order_change

        # 初期メッセージ（空の時に表示）
        self.document_list_msg = ctk.CTkLabel(
            self.document_draggable_list,
            text="📋 PDFファイルをここにドラッグ&ドロップしてください\n\n・連番で資料NO（資料1, 資料2...）を自動挿入\n・フォント: Meiryo、四角囲い文字で表示\n・全ての回転角度（0°, 90°, 180°, 270°）に対応\n・ドラッグで順序変更、↑↓ボタンでも調整可能",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            justify="left"
        )
        self.document_list_msg.pack(fill="both", expand=True, padx=20, pady=20)

        # 実行ボタン
        self.document_execute_btn = ctk.CTkButton(
            self.document_number_tab,
            text="📄 資料NO挿入実行",
            command=self._start_document_number_insertion,
            height=40,
            state="disabled"
        )
        self.document_execute_btn.pack(pady=(10, 10))

        # プログレスバー
        self.document_progress = ctk.CTkProgressBar(self.document_number_tab)
        self.document_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.document_progress.set(0)

        # ステータスラベル
        self.document_status = ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルを追加して資料番号を入力してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.document_status.pack(pady=(0, 10))

        # 入力フィールドの変更監視は新しいメソッドで処理

    def _open_folder(self, folder_path: str):
        """指定されたフォルダをエクスプローラーで開く"""
        import os
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            logger.error(f"フォルダを開けませんでした: {folder_path} - {e}")
            messagebox.showwarning("エラー", f"フォルダを開けませんでした。\n{folder_path}")

    def _toggle_page_number_options(self) -> None:
        """ページ番号オプションの有効/無効を切り替える"""
        state = "normal" if self.add_page_number_var.get() else "disabled"
        self.start_page_label.configure(state=state)
        self.start_page_entry.configure(state=state)
        self.start_number_label.configure(state=state)
        self.start_number_entry.configure(state=state)
    
    def _setup_drag_drop(self) -> None:
        """ドラッグ&ドロップ機能設定"""
        try:
            # 変換タブのドラッグ&ドロップ設定
            office_filter = drag_drop_handler.create_office_image_filter()
            drag_drop_handler.setup_drag_drop(
                self.conversion_draggable_list,
                self._add_conversion_files,
                office_filter
            )
            
            # 結合タブのドラッグ&ドロップ設定
            pdf_filter = drag_drop_handler.create_pdf_filter()
            drag_drop_handler.setup_drag_drop(
                self.combination_draggable_list,
                self._add_combination_files,
                pdf_filter
            )

            # 資料NO挿入タブのドラッグ&ドロップ設定
            drag_drop_handler.setup_drag_drop(
                self.document_draggable_list,
                self._add_document_number_files,
                pdf_filter
            )
            
            logger.info("ドラッグ&ドロップ機能設定完了")
            
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
    
    def _add_conversion_files(self, paths: List[str]) -> None:
        """変換ファイル追加"""
        scan_result = FileScanner.scan_files_from_paths(paths)
        valid_files = scan_result['valid']

        if valid_files:
            new_files = [f for f in valid_files if f not in self.conversion_files]
            if new_files:
                self.conversion_files.extend(new_files)
                self.conversion_draggable_list.add_files(new_files)
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
                # ドラッグアンドドロップリストにファイルを追加
                self.combination_draggable_list.add_files(new_files)

                # 旧式リストも互換性のため更新
                self.combination_files.extend(new_files)

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

    def _on_conversion_selection_change(self, selected_files: List[str]) -> None:
        """変換リストの選択変更時のコールバック"""
        has_selection = len(selected_files) > 0
        if hasattr(self, 'conversion_delete_btn'):
            self.conversion_delete_btn.configure(
                state="normal" if has_selection else "disabled"
            )

    def _on_combination_selection_change(self, selected_files: List[str]) -> None:
        """結合リストの選択変更時のコールバック"""
        # ボタンの有効/無効を更新
        has_selection = len(selected_files) > 0
        self.combination_move_up_btn.configure(state="normal" if has_selection else "disabled")
        self.combination_move_down_btn.configure(state="normal" if has_selection else "disabled")
        self.combination_delete_btn.configure(state="normal" if has_selection else "disabled")

        # ステータス更新
        if has_selection:
            self.combination_status.configure(text=f"{len(selected_files)}個のファイルを選択中")
        else:
            self.combination_status.configure(text="ファイルを選択してボタン操作するか、ドラッグで並び替えてください")

    def _on_combination_order_change(self, file_paths: List[str]) -> None:
        """結合リストの順序変更時のコールバック"""
        # 旧式リストも同期
        self.combination_files = file_paths.copy()
        self._update_combination_display()
        self.combination_status.configure(text="ファイル順序を変更しました")
        logger.info(f"ドラッグでファイル順序変更: {len(file_paths)}個")

    def _select_document_number_files(self) -> None:
        """資料NO挿入ファイル選択ダイアログ"""
        files = fd.askopenfilenames(
            title="資料NO挿入するPDFファイルを選択",
            filetypes=[("PDFファイル", "*.pdf"), ("すべてのファイル", "*.*")]
        )

        if files:
            self._add_document_number_files(list(files))

    def _add_document_number_files(self, paths: List[str]) -> None:
        """資料NO挿入ファイル追加（PDF専用）"""
        try:
            # セキュリティ検証
            validated_paths = SecurityValidator.validate_multiple_paths(paths)
            if len(validated_paths) < len(paths):
                error_handler.handle_error(
                    ValueError("一部のファイルがセキュリティ検証に失敗しました"),
                    ErrorSeverity.WARNING,
                    "ファイル選択",
                    "一部のファイルが安全でないため除外されました。"
                )

            pdf_files = [p for p in validated_paths if Path(p).suffix.lower() == '.pdf' and Path(p).is_file()]

            if pdf_files:
                # 重複を避けるために新しいファイルのみ追加
                new_files = [f for f in pdf_files if f not in self.document_number_files]
                if new_files:
                    # 任意Noモードでは1ファイルのみ許可
                    if self.numbering_type_var.get() == "任意No":
                        if self.document_number_files:
                            # 既にファイルがある場合は追加不可
                            self.document_status.configure(text="任意Noモードでは1ファイルのみ対応です")
                            return
                        else:
                            # 複数ファイルが選択された場合は最初の1つのみ
                            new_files = new_files[:1]

                    # ドラッグアンドドロップリストにファイルを追加
                    self.document_draggable_list.add_files(new_files)

                    # 旧式リストも互換性のため更新
                    self.document_number_files.extend(new_files)

                    self._update_document_number_display()
                    logger.info(f"資料NO挿入ファイル追加: {len(new_files)}個")
                else:
                    logger.info("重複ファイルのため追加されませんでした")
            else:
                self.document_status.configure(text="PDFファイルが見つかりませんでした")

        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorSeverity.CRITICAL,
                "ファイル追加",
                "ファイルの追加中にエラーが発生しました。"
            )

    def _on_document_selection_change(self, selected_files: List[str]) -> None:
        """ドラッグリストの選択変更時のコールバック"""
        # ボタンの有効/無効を更新
        has_selection = len(selected_files) > 0
        self.document_move_up_btn.configure(state="normal" if has_selection else "disabled")
        self.document_move_down_btn.configure(state="normal" if has_selection else "disabled")
        self.document_delete_btn.configure(state="normal" if has_selection else "disabled")

        # ステータス更新
        if has_selection:
            self.document_status.configure(text=f"{len(selected_files)}個のファイルを選択中")
        else:
            self.document_status.configure(text="ファイルを選択してボタン操作するか、ドラッグで並び替えてください")

    def _on_document_order_change(self, file_paths: List[str]) -> None:
        """ドラッグリストの順序変更時のコールバック"""
        # 旧式リストも同期
        self.document_number_files = file_paths.copy()
        self._update_document_number_display()
        self.document_status.configure(text="ファイル順序を変更しました")
        logger.info(f"ドラッグでファイル順序変更: {len(file_paths)}個")

    def _clear_document_number_files(self) -> None:
        """資料NO挿入ファイルクリア"""
        # ドラッグリストをクリア
        self.document_draggable_list.clear_files()

        # 旧式リストもクリア（互換性のため）
        self.document_number_files.clear()

        self._update_document_number_display()

        self.document_execute_btn.configure(state="disabled")
        self.document_clear_btn.configure(state="disabled")
        self.document_count_label.configure(text="ファイル数: 0")
        self.document_status.configure(text="PDFファイルを追加して資料番号を入力してください")

        # 初期メッセージを表示
        self.document_list_msg.pack(fill="both", expand=True, padx=20, pady=20)

        logger.info("資料NO挿入ファイルリストクリア")

    def _move_document_up(self) -> None:
        """選択した資料NO挿入ファイルを上に移動"""
        try:
            # ドラッグリストの移動メソッドを使用
            moved = self.document_draggable_list.move_selected_up()

            if moved:
                self.document_status.configure(text="選択したファイルを上に移動しました")
                logger.info("ボタンでファイルを上に移動")
            else:
                selected_files = self.document_draggable_list.get_selected_files()
                if not selected_files:
                    self.document_status.configure(text="移動するファイルを選択してください")
                else:
                    self.document_status.configure(text="これ以上上に移動できません")

        except Exception as e:
            logger.error(f"ファイル移動中にエラーが発生: {str(e)}")
            self.document_status.configure(text="移動中にエラーが発生しました")

    def _move_document_down(self) -> None:
        """選択した資料NO挿入ファイルを下に移動"""
        try:
            # ドラッグリストの移動メソッドを使用
            moved = self.document_draggable_list.move_selected_down()

            if moved:
                self.document_status.configure(text="選択したファイルを下に移動しました")
                logger.info("ボタンでファイルを下に移動")
            else:
                selected_files = self.document_draggable_list.get_selected_files()
                if not selected_files:
                    self.document_status.configure(text="移動するファイルを選択してください")
                else:
                    self.document_status.configure(text="これ以上下に移動できません")

        except Exception as e:
            logger.error(f"ファイル移動中にエラーが発生: {str(e)}")
            self.document_status.configure(text="移動中にエラーが発生しました")

    def _delete_selected_document(self) -> None:
        """選択した資料NO挿入ファイルを削除"""
        try:
            selected_files = self.document_draggable_list.get_selected_files()

            if not selected_files:
                self.document_status.configure(text="削除するファイルを選択してください")
                return

            if messagebox.askyesno("確認", f"{len(selected_files)}件の選択されたファイルを削除しますか？"):
                # ドラッグリストから削除
                self.document_draggable_list.remove_selected_files()

                self._update_document_number_display()
                self.document_status.configure(text=f"{len(selected_files)}件のファイルを削除しました")
                logger.info(f"{len(selected_files)}件のファイルを削除しました")

        except Exception as e:
            logger.error(f"ファイル削除中にエラーが発生: {str(e)}")
            self.document_status.configure(text="削除中にエラーが発生しました")

    def _on_numbering_type_changed(self, value: str) -> None:
        """連番タイプ変更時の処理"""
        if value == "任意No":
            self.number_label.configure(text="資料番号:")
            self.number_entry.configure(placeholder_text="1 または 1-1")
            # 任意Noモードでは複数ファイル選択を無効化
            self._check_file_limit_for_arbitrary()
        elif value == "連番":
            self.number_label.configure(text="開始番号:")
            self.number_entry.configure(placeholder_text="1")
        elif value == "ハイフン連番":
            self.number_label.configure(text="プレフィックス:")
            self.number_entry.configure(placeholder_text="1")

        self._update_numbering_preview()
        self._update_execute_button_state()

    def _on_numbering_settings_changed(self, *args) -> None:
        """連番設定変更時の処理"""
        self._update_numbering_preview()
        self._update_execute_button_state()

    def _update_numbering_preview(self) -> None:
        """連番プレビュー更新"""
        numbering_type = self.numbering_type_var.get()
        number_value = self.number_var.get().strip()

        if numbering_type == "任意No":
            if number_value:
                preview_text = f"→ 「資料{number_value}」（単一ファイルのみ）"
            else:
                preview_text = "→ 「資料〇」（任意の番号を入力）"
        elif numbering_type == "連番":
            if number_value and number_value.isdigit():
                start_num = int(number_value)
                preview_text = f"→ 「資料{start_num}, 資料{start_num+1}, 資料{start_num+2}...」"
            else:
                preview_text = "→ 「資料1, 資料2, 資料3...」"
        elif numbering_type == "ハイフン連番":
            if number_value:
                prefix = number_value
                preview_text = f"→ 「資料{prefix}-1, 資料{prefix}-2, 資料{prefix}-3...」"
            else:
                preview_text = "→ 「資料1-1, 資料1-2, 資料1-3...」"
        else:
            preview_text = "→ 「資料1, 資料2, 資料3...」"

        self.preview_label.configure(text=preview_text)

    def _check_file_limit_for_arbitrary(self) -> None:
        """任意Noモードでのファイル数制限チェック"""
        if self.numbering_type_var.get() == "任意No" and len(self.document_number_files) > 1:
            files_to_remove = self.document_number_files[1:]
            for file_path in files_to_remove:
                self.document_draggable_list.remove_file(file_path)
            self._update_document_number_display()
            self.document_status.configure(text="任意Noモードでは1ファイルのみ対応です")

    def _update_execute_button_state(self) -> None:
        """実行ボタンの状態更新"""
        numbering_type = self.numbering_type_var.get()

        # 任意Noモードでは1ファイルのみ許可
        if numbering_type == "任意No" and len(self.document_number_files) > 1:
            self.document_execute_btn.configure(state="disabled")
            return

        if self.document_number_files and self.number_var.get().strip():
            self.document_execute_btn.configure(state="normal")
        else:
            self.document_execute_btn.configure(state="disabled")

    def _update_document_number_display(self) -> None:
        """資料NO挿入タブ表示更新"""
        # ドラッグリストと旧式リストを同期
        current_files = self.document_draggable_list.get_files()
        self.document_number_files = current_files

        if current_files:
            # メッセージを非表示にして、ファイル数を更新
            self.document_list_msg.pack_forget()
            self.document_clear_btn.configure(state="normal")
            self.document_count_label.configure(text=f"ファイル数: {len(current_files)}")
            self.document_status.configure(text=f"{len(current_files)}個のPDFファイルが追加されました")

            # 実行ボタンの状態更新
            self._update_execute_button_state()
        else:
            # ファイルがない場合は初期メッセージを表示
            self.document_list_msg.pack(fill="both", expand=True, padx=20, pady=20)
            self.document_execute_btn.configure(state="disabled")
            self.document_clear_btn.configure(state="disabled")
            self.document_count_label.configure(text="ファイル数: 0")
            self.document_status.configure(text="PDFファイルを追加して連番設定を行ってください")


    def _start_document_number_insertion(self) -> None:
        """連番資料NO挿入開始"""
        try:
            if not self.document_number_files:
                return

            number_value = self.number_var.get().strip()
            if not number_value:
                self.document_status.configure(text="番号を入力してください")
                return

            # 入力値のセキュリティ検証
            if not InputValidator.validate_document_number(number_value):
                error_handler.handle_error(
                    ValueError("無効な資料番号"),
                    ErrorSeverity.WARNING,
                    "入力検証",
                    "資料番号に無効な文字が含まれています。英数字、ひらがな、カタカナ、漢字のみ使用してください。"
                )
                return

            numbering_type = self.numbering_type_var.get()

            # 確認メッセージを生成
            if numbering_type == "任意No":
                preview = f"資料{number_value}"
            elif numbering_type == "連番":
                start_num = int(number_value) if number_value.isdigit() else 1
                preview = f"資料{start_num}, 資料{start_num+1}, 資料{start_num+2}..."
            elif numbering_type == "ハイフン連番":
                preview = f"資料{number_value}-1, 資料{number_value}-2, 資料{number_value}-3..."
            else:
                preview = "資料1, 資料2, 資料3..."

            # 確認メッセージ
            result = messagebox.askyesno(
                "連番資料NO挿入の確認",
                f"以下の内容で連番資料NO挿入を実行しますか？\n\n"
                f"• 対象ファイル数: {len(self.document_number_files)}個\n"
                f"• 連番タイプ: {numbering_type}\n"
                f"• 番号パターン: {preview}\n\n"
                f"注意: 元ファイルは「元ファイル」フォルダに自動バックアップされ、\n"
                f"同じファイル名で資料NO挿入済みファイルが保存されます。"
            )

            if not result:
                return

            # UIを無効化
            self.document_execute_btn.configure(state="disabled")
            self.document_status.configure(text="資料NO挿入処理中...")
            self.document_progress.set(0)

            # 別スレッドで処理実行
            thread = threading.Thread(target=self._run_sequential_number_insertion, args=(numbering_type, number_value))
            thread.daemon = True
            thread.start()

        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorSeverity.CRITICAL,
                "資料NO挿入開始",
                "資料NO挿入処理の開始中にエラーが発生しました。"
            )

    def _run_sequential_number_insertion(self, numbering_type: str, number_value: str) -> None:
        """連番資料NO挿入実行（別スレッド）"""
        try:
            def progress_callback(message, progress):
                self.root.after(0, lambda: self.document_progress.set(progress / 100))
                self.root.after(0, lambda: self.document_status.configure(text=message))

            # 任意Noモードの場合は従来の単一番号挿入を使用
            if numbering_type == "任意No":
                result = self.pdf_combiner.add_document_numbers(
                    pdf_paths=self.document_number_files.copy(),
                    output_path="",  # 空文字列で元フォルダに保存
                    document_number=number_value,
                    progress_callback=progress_callback
                )
            else:
                # パラメータ準備
                # GUI表示名をシステム内部名に変換
                if numbering_type == "連番":
                    internal_type = "start_at"
                elif numbering_type == "ハイフン連番":
                    internal_type = "hyphen"
                else:
                    internal_type = "start_at"  # フォールバック

                start_number = int(number_value) if number_value.isdigit() else 1
                prefix_number = number_value

                result = self.pdf_combiner.add_sequential_document_numbers(
                    pdf_paths=self.document_number_files.copy(),
                    output_dir="",  # 空文字列で元フォルダに保存
                    numbering_type=internal_type,
                    start_number=start_number,
                    prefix_number=prefix_number,
                    progress_callback=progress_callback
                )

            # UI更新
            self.root.after(0, lambda: self._on_document_number_complete(result))

        except Exception as e:
            self.root.after(0, lambda: error_handler.handle_error(
                e, ErrorSeverity.CRITICAL, "資料NO挿入"
            ))
            self.root.after(0, self._reset_document_number_ui)

    def _on_document_number_complete(self, result) -> None:
        """資料NO挿入完了処理"""
        self.document_progress.set(1.0)

        if result.success:
            message = (f"資料NO挿入が完了しました！\n\n"
                       f"• 処理ファイル数: {len(result.processed_files)}個\n"
                       f"• 総ページ数: {result.total_pages}ページ\n"
                       f"• 元ファイルは「元ファイル」フォルダにバックアップされました\n"
                       f"• 処理時間: {result.processing_time:.1f}秒\n\n"
                       f"各ファイルに資料NOが正しく挿入されました。")
            self.document_status.configure(
                text=f"資料NO挿入完了: {result.total_pages}ページ ({len(result.processed_files)}ファイル)"
            )
            self._show_and_open_results("資料NO挿入完了", message, result.processed_files)
        else:
            message = f"資料NO挿入に失敗しました。\n\nエラー: {result.error_message}"
            self.document_status.configure(text=f"資料NO挿入失敗: {result.error_message}")
            messagebox.showerror("資料NO挿入失敗", message)

        # ファイルリストをクリア
        self._clear_document_number_files()

        # UI有効化
        self.document_execute_btn.configure(state="normal")

    def _reset_document_number_ui(self) -> None:
        """資料NO挿入UI リセット"""
        self.document_execute_btn.configure(state="normal")
        self.document_progress.set(0)
        self.document_status.configure(text="エラーが発生しました")
    
    def _update_conversion_display(self) -> None:
        """変換タブ表示更新"""
        current_files = self.conversion_draggable_list.get_files()
        self.conversion_files = current_files
        self.conversion_count_label.configure(text=f"ファイル数: {len(current_files)}")

        if current_files:
            self.initial_message_label.pack_forget()
            self.conversion_convert_btn.configure(state="normal")
            if hasattr(self, 'conversion_clear_btn'):
                self.conversion_clear_btn.configure(state="normal")
            self.conversion_status.configure(
                text=f"{len(current_files)}個のファイルが追加されました"
            )
        else:
            self.initial_message_label.pack(fill="both", expand=True, padx=20, pady=20)
            self.conversion_convert_btn.configure(state="disabled")
            if hasattr(self, 'conversion_clear_btn'):
                self.conversion_clear_btn.configure(state="disabled")
            if hasattr(self, 'conversion_delete_btn'):
                self.conversion_delete_btn.configure(state="disabled")
            self.conversion_status.configure(text="変換するファイルを追加してください")
    
    def _update_combination_display(self) -> None:
        """結合タブ表示更新"""
        # ドラッグリストと旧式リストを同期
        current_files = self.combination_draggable_list.get_files()
        self.combination_files = current_files

        if current_files:
            # メッセージを非表示にして、ファイル数を更新
            self.combination_list_msg.pack_forget()
            self.combination_combine_btn.configure(state="normal")
            if hasattr(self, 'combination_clear_btn'):
                self.combination_clear_btn.configure(state="normal")
            self.combination_count_label.configure(text=f"ファイル数: {len(current_files)}")
            self.combination_status.configure(text=f"{len(current_files)}個のPDFファイルが追加されました")
        else:
            # ファイルがない場合は初期メッセージを表示
            self.combination_list_msg.pack(fill="both", expand=True, padx=20, pady=20)
            self.combination_combine_btn.configure(state="disabled")
            if hasattr(self, 'combination_clear_btn'):
                self.combination_clear_btn.configure(state="disabled")
            if hasattr(self, 'combination_delete_btn'):
                self.combination_delete_btn.configure(state="disabled")
            self.combination_count_label.configure(text="ファイル数: 0")
            self.combination_status.configure(text="PDFファイルを追加してください")

    def _clear_combination_files(self) -> None:
        """結合ファイルクリア"""
        # ドラッグリストをクリア
        self.combination_draggable_list.clear_files()

        # 旧式リストもクリア（互換性のため）
        self.combination_files.clear()

        self._update_combination_display()
        
        self.combination_combine_btn.configure(state="disabled")
        self.combination_count_label.configure(text="ファイル数: 0")
        self.combination_status.configure(text="PDFファイルを追加してください")
        
        logger.info("結合ファイルリストクリア")
    
    def _move_combination_up(self) -> None:
        """選択したPDFファイルを上に移動"""
        try:
            # ドラッグリストの移動メソッドを使用
            moved = self.combination_draggable_list.move_selected_up()

            if moved:
                self.combination_status.configure(text="選択したファイルを上に移動しました")
                logger.info("ボタンでファイルを上に移動")
            else:
                selected_files = self.combination_draggable_list.get_selected_files()
                if not selected_files:
                    self.combination_status.configure(text="移動するファイルを選択してください")
                else:
                    self.combination_status.configure(text="これ以上上に移動できません")

        except Exception as e:
            logger.error(f"ファイル上移動中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="移動中にエラーが発生しました")

    def _move_combination_down(self) -> None:
        """選択したPDFファイルを下に移動"""
        try:
            # ドラッグリストの移動メソッドを使用
            moved = self.combination_draggable_list.move_selected_down()

            if moved:
                self.combination_status.configure(text="選択したファイルを下に移動しました")
                logger.info("ボタンでファイルを下に移動")
            else:
                selected_files = self.combination_draggable_list.get_selected_files()
                if not selected_files:
                    self.combination_status.configure(text="移動するファイルを選択してください")
                else:
                    self.combination_status.configure(text="これ以上下に移動できません")

        except Exception as e:
            logger.error(f"ファイル下移動中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="移動中にエラーが発生しました")

    def _delete_selected_combination(self) -> None:
        """選択したPDFファイルを削除"""
        try:
            selected_files = self.combination_draggable_list.get_selected_files()
            
            if not selected_files:
                self.combination_status.configure(text="削除するファイルを選択してください")
                return
            
            if messagebox.askyesno("確認", f"{len(selected_files)}件の選択されたファイルを削除しますか？"):
                # ドラッグリストから削除
                self.combination_draggable_list.remove_selected_files()

                self._update_combination_display()
                self.combination_status.configure(text=f"{len(selected_files)}件のファイルを削除しました")
                logger.info(f"{len(selected_files)}件のPDFファイルを削除しました")
            
        except Exception as e:
            logger.error(f"ファイル削除中にエラーが発生: {str(e)}")
            self.combination_status.configure(text="削除中にエラーが発生しました")
    
    def _delete_selected_conversion(self) -> None:
        """選択中の変換ファイルを削除"""
        selected = self.conversion_draggable_list.get_selected_files()
        if not selected:
            return
        for fp in selected:
            if fp in self.conversion_files:
                self.conversion_files.remove(fp)
        self.conversion_draggable_list.remove_selected_files()
        self._update_conversion_display()
        logger.info(f"変換ファイル削除: {len(selected)}個")

    def _clear_all_conversion(self, force: bool = False) -> None:
        """変換ファイルを全クリア"""
        if not self.conversion_files:
            return
        if not force and not self._show_confirmation_dialog(
            "全ファイルクリア", f"全{len(self.conversion_files)}件をクリアしますか？"
        ):
            return
        self.conversion_files.clear()
        self.conversion_draggable_list.clear_files()
        self._update_conversion_display()
        self.conversion_status.configure(text="ファイルリストをクリアしました")
        logger.info("変換ファイル全クリア")
    
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
                split_sheets = self.split_excel_sheets_var.get()
                result = self.pdf_converter._convert_single_file(file_path, split_sheets)
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
    
    def _show_and_open_results(self, title: str, message: str, output_paths: List[str]):
        """処理完了メッセージとフォルダ表示"""
        messagebox.showinfo(title, message)
        if output_paths:
            folder_to_open = str(Path(output_paths[0]).parent)
            self._open_folder(folder_to_open)


    def _on_conversion_complete(self, results) -> None:
        """変換完了処理"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        self.conversion_progress.set(1.0)
        
        if successful:
            message = f"変換が完了しました。\n\n成功: {len(successful)}件\n失敗: {len(failed)}件"
            self.conversion_status.configure(text=f"変換完了: 成功 {len(successful)}個, 失敗 {len(failed)}個")
            
            all_successful_paths = [path for r in successful for path in r.target_paths]
            
            def open_folder_callback():
                if all_successful_paths:
                    self._open_folder(str(Path(all_successful_paths[0]).parent))

            # 結合提案ダイアログ
            if len(all_successful_paths) >= 2:
                self._show_combination_offer(all_successful_paths, on_no_callback=open_folder_callback)
            else:
                open_folder_callback()

            messagebox.showinfo("変換完了", message)

        else:
            message = f"変換に失敗しました。\n\n失敗: {len(failed)}件"
            self.conversion_status.configure(text=f"変換失敗: {len(failed)}個のファイルで問題が発生")
            messagebox.showerror("変換失敗", message)
        
        # ファイルリストをクリア
        self._clear_all_conversion(force=True)

        # UI有効化
        self.conversion_convert_btn.configure(state="normal")
    
    def _show_combination_offer(self, pdf_files: List[str], on_no_callback=None) -> None:
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        msg_label.pack(pady=20)
        
        # ボタンフレーム
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        def on_yes():
            dialog.destroy()
            # 既存の結合ファイルリストをクリア
            self._clear_combination_files()
            self._add_combination_files(pdf_files)
            self.tab_view.set("PDF結合")
        
        def on_no():
            dialog.destroy()
            if on_no_callback:
                on_no_callback()
        
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

        add_blank_page = self.add_blank_page_var.get()
        add_page_numbers = self.add_page_number_var.get()
        start_page = int(self.start_page_var.get())
        start_number = int(self.start_number_var.get())

        # 別スレッドで結合実行
        thread = threading.Thread(target=self._run_combination, args=(output_path, add_blank_page, add_page_numbers, start_page, start_number))
        thread.daemon = True
        thread.start()
    
    def _run_combination(self, output_path: str, add_blank_page: bool, add_page_numbers: bool, start_page: int, start_number: int) -> None:
        """結合実行（別スレッド）"""
        try:
            def progress_callback(message, progress):
                self.root.after(0, lambda: self.combination_progress.set(progress / 100))
                self.root.after(0, lambda: self.combination_status.configure(text=message))
            
            result = self.pdf_combiner.combine_pdfs(
                self.combination_files.copy(),
                output_path,
                add_blank_page,
                add_page_numbers,
                start_page,
                start_number,
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
            message = (f"PDF結合が完了しました！\n\n"
                       f"• 結合ファイル数: {len(result.processed_files)}個\n"
                       f"• 総ページ数: {result.total_pages}ページ\n"
                       f"• 出力ファイル: {Path(result.output_path).name}\n"
                       f"• 処理時間: {result.processing_time:.1f}秒")
            self.combination_status.configure(
                text=f"結合完了: {result.total_pages}ページ ({len(result.processed_files)}ファイル)"
            )
            self._show_and_open_results("PDF結合完了", message, [result.output_path])
        else:
            message = f"結合に失敗しました。\n\nエラー: {result.error_message}"
            self.combination_status.configure(text=f"結合失敗: {result.error_message}")
            messagebox.showerror("結合失敗", message)

        # ファイルリストをクリア
        self._clear_combination_files()

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

        try:
            # PDF変換器のクリーンアップ
            if hasattr(self, 'pdf_converter'):
                self.pdf_converter.cleanup()

            # PDF結合器のクリーンアップ
            if hasattr(self, 'pdf_combiner'):
                # 実行中の処理を停止
                self.pdf_combiner = None

            # Office COMオブジェクトの強制クリーンアップ
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except:
                pass

            # 一時ファイルの削除
            try:
                import tempfile
                temp_dir = tempfile.gettempdir()
                for temp_file in Path(temp_dir).glob("*.tmp"):
                    if temp_file.name.endswith('.pdf.tmp'):
                        temp_file.unlink(missing_ok=True)
            except:
                pass

        except Exception as e:
            logger.warning(f"終了処理中にエラー: {e}")

        finally:
            self.root.quit()
            self.root.destroy()
            logger.info("PDF変換・結合ツール 正常終了")
    
    def run(self) -> None:
        """アプリケーション実行"""
        logger.info("統合アプリケーション実行開始")
        self.root.mainloop()