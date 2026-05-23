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
import shutil
import tempfile

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
from .update_banner import UpdateBanner
from .help_dialog import HelpDialog
from .preview_dialog import PDFPreviewDialog, render_doc_number_preview, render_page_number_preview
from .theme import (
    CLR_PRIMARY, CLR_ACCENT, CLR_LIGHT_BG, CLR_LIGHT_BORDER,
    CLR_SEL_BORDER, CLR_TOOLBAR_BG, CLR_BORDER, CLR_RED_LIGHT,
    CLR_RED_TEXT, CLR_GRAY_TEXT, CLR_DARK_TEXT, CLR_LIST_HEADER,
    CLR_WHITE, get_file_type_badge,
    FONT_FAMILY,
    TAB_CONVERSION, TAB_COMBINATION, TAB_DOCUMENT, TAB_PAGENUMBER, TAB_INACTIVE,
    CLR_CONV_PRIMARY, CLR_CONV_HOVER,
    CLR_COMB_PRIMARY, CLR_COMB_HOVER,
    CLR_DOC_PRIMARY,  CLR_DOC_HOVER,
    CLR_PN_PRIMARY,   CLR_PN_HOVER,
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
        self.pagenumber_files: List[str] = []

        # UI作成
        self._create_main_ui()
        self._setup_drag_drop()
        
        # エラーハンドラー設定
        error_handler.parent_window = self.root
        
        self._log_startup_time()
    
    def _setup_window(self) -> None:
        """ウィンドウ初期設定"""
        self.root.title(WINDOW_TITLE)

        # 画面サイズに合わせてウィンドウ高さを自動調整
        self.root.update_idletasks()
        screen_h = self.root.winfo_screenheight()
        # タスクバー等を考慮して画面高さの90%を上限にする
        max_h = int(screen_h * 0.90)
        win_h = min(WINDOW_HEIGHT, max_h)
        win_h = max(win_h, WINDOW_MIN_HEIGHT)  # 最小高さは保証

        self.root.geometry(f"{WINDOW_WIDTH}x{win_h}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        logger.info(f"ウィンドウサイズ設定: {WINDOW_WIDTH}x{win_h} (画面高さ: {screen_h}px)")
        # CustomTkinter 初期化完了後にアイコンを設定（即時だと上書きされる）
        self.root.after(200, self._set_window_icon)
        
    def _set_window_icon(self) -> None:
        """ウィンドウアイコン設定（after() で遅延呼び出し）"""
        try:
            import sys
            from pathlib import Path
            if getattr(sys, 'frozen', False):
                base = Path(sys._MEIPASS)
            else:
                base = Path(__file__).parent.parent.parent
            ico = base / "assets" / "icon.ico"
            png = base / "assets" / "icon.png"
            if ico.exists():
                self.root.wm_iconbitmap(str(ico))
            elif png.exists():
                from PIL import Image, ImageTk
                img = ImageTk.PhotoImage(Image.open(str(png)).resize((256, 256)))
                self.root.wm_iconphoto(True, img)
                self.root._icon_ref = img  # GC防止
        except Exception as e:
            logger.debug(f"アイコン設定スキップ: {e}")

        # ウィンドウを中央に配置（横幅は WINDOW_WIDTH 固定、縦のみ実寸を使用）
        self.root.update_idletasks()
        win_h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
        # 画面上端より上にはみ出さないよう保護
        y = max(0, y)
        self.root.geometry(f"{WINDOW_WIDTH}x{win_h}+{x}+{y}")
        
        # アプリ終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("統合ウィンドウ初期化完了")
    
    def _create_main_ui(self) -> None:
        """メインUI作成"""
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray10"))
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # ── アップデートバナー（新バージョン検出時のみ表示） ──
        UpdateBanner(self.main_frame)

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

        ctk.CTkButton(
            header_frame,
            text="?",
            width=32, height=32,
            corner_radius=16,
            fg_color="#3D82C4",
            hover_color="#5494D6",
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            command=self._open_help,
        ).pack(side="right", padx=12, pady=10)

        # ── カスタムタブバー ──
        _TAB_DEFS = [
            ("PDF変換",    TAB_CONVERSION),
            ("資料NO挿入",  TAB_DOCUMENT),
            ("PDF結合",    TAB_COMBINATION),
            ("ページ番号挿入", TAB_PAGENUMBER),
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
        self.pagenumber_tab      = self._tab_frames["ページ番号挿入"]

        # 各タブのUI作成
        self._create_conversion_ui()
        self._create_document_number_ui()
        self._create_combination_ui()
        self._create_pagenumber_ui()

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
        ctk.CTkLabel(
            self.conversion_tab,
            text="Office文書・画像ファイルをPDFに変換します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(pady=(10, 5))

        # ── ツールバー ──
        toolbar = ctk.CTkFrame(self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
                                border_width=1, border_color=CLR_BORDER, corner_radius=6)
        toolbar.pack(fill="x", padx=15, pady=(0, 5))

        self.conversion_select_btn = ctk.CTkButton(
            toolbar, text="ファイル選択",
            command=self._select_conversion_files,
            height=32, width=100,
            fg_color=CLR_CONV_PRIMARY, hover_color=CLR_CONV_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        )
        self.conversion_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.conversion_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_conversion,
            height=32, width=90,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.conversion_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_clear_btn = ctk.CTkButton(
            toolbar, text="全クリア",
            command=self._clear_all_conversion,
            height=32, width=80,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.conversion_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
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

        # Excelシート分割オプション（ファイルリスト下）
        self.excel_options_frame = ctk.CTkFrame(
            self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        self.excel_options_frame.pack(fill="x", padx=15, pady=(0, 5))

        self.split_excel_sheets_switch = ctk.CTkSwitch(
            self.excel_options_frame,
            text="Excelシートが複数ある場合は、すべてのシートをそれぞれPDFに変換する",
            variable=self.split_excel_sheets_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_CONV_PRIMARY
        )
        self.split_excel_sheets_switch.pack(side="left", padx=(10, 8), pady=6)

        # 変換実行ボタン
        self.conversion_convert_btn = ctk.CTkButton(
            self.conversion_tab,
            text="🔄 PDF変換実行",
            command=self._start_conversion,
            height=40, state="disabled",
            fg_color=CLR_CONV_PRIMARY, hover_color=CLR_CONV_HOVER,
            text_color="white", text_color_disabled="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.conversion_convert_btn.pack(pady=(8, 8))

        # プログレスバー
        self.conversion_progress = ctk.CTkProgressBar(self.conversion_tab)
        self.conversion_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.conversion_progress.set(0)

        # ステータスラベル
        self.conversion_status = ctk.CTkLabel(
            self.conversion_tab,
            text="ファイルを選択してください",
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
            toolbar, text="PDF選択",
            command=self._select_combination_files,
            height=32, width=90,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        )
        self.combination_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.combination_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_combination,
            height=32, width=80,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.combination_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_clear_btn = ctk.CTkButton(
            toolbar, text="クリア",
            command=self._clear_combination_files,
            height=32, width=70,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.combination_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_move_up_btn = ctk.CTkButton(
            toolbar, text="↑", command=self._move_combination_up,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.combination_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

        self.combination_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_combination_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.combination_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_sort_btn = ctk.CTkButton(
            toolbar, text="Ａ↓",
            command=self._sort_combination_files,
            height=32, width=46,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.combination_sort_btn.pack(side="left", padx=(0, 4), pady=6)

        self.combination_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
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
        self.combine_pn_binding_compat_var = ctk.BooleanVar(value=False)

        options_frame = ctk.CTkFrame(
            self.combination_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        options_frame.pack(fill="x", padx=15, pady=(0, 5))

        # 白紙挿入スイッチ
        blank_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        blank_row.pack(fill="x", padx=8, pady=(6, 2))

        self.add_blank_page_switch = ctk.CTkSwitch(
            blank_row,
            text="奇数ページのPDF末尾に白紙ページを挿入する",
            variable=self.add_blank_page_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            progress_color=CLR_COMB_PRIMARY
        )
        self.add_blank_page_switch.pack(side="left")

        # ページ番号スイッチ
        page_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        page_row.pack(fill="x", padx=8, pady=(2, 2))

        self.add_page_number_switch = ctk.CTkSwitch(
            page_row,
            text="フッター中央にページ番号を挿入する",
            variable=self.add_page_number_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            progress_color=CLR_COMB_PRIMARY,
            command=self._toggle_page_number_options
        )
        self.add_page_number_switch.pack(side="left")

        # 開始ページ・開始番号（別行）
        sub_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        sub_row.pack(fill="x", padx=(30, 8), pady=(0, 6))

        self.start_page_label = ctk.CTkLabel(
            sub_row, text="開始ページ:", font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.start_page_label.pack(side="left", padx=(0, 4))

        self.start_page_var = ctk.StringVar(value="1")
        self.start_page_entry = ctk.CTkEntry(
            sub_row, textvariable=self.start_page_var, width=40
        )
        self.start_page_entry.pack(side="left")

        self.start_page_unit = ctk.CTkLabel(
            sub_row, text="ページ", font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.start_page_unit.pack(side="left", padx=(2, 20))

        self.start_number_label = ctk.CTkLabel(
            sub_row, text="開始番号:", font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.start_number_label.pack(side="left", padx=(0, 4))

        self.start_number_var = ctk.StringVar(value="1")
        self.start_number_entry = ctk.CTkEntry(
            sub_row, textvariable=self.start_number_var, width=40
        )
        self.start_number_entry.pack(side="left")

        # 左綴じ対応スイッチ（ページ番号オプションの下）
        binding_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        binding_row.pack(fill="x", padx=(30, 8), pady=(0, 6))

        self.combine_pn_binding_switch = ctk.CTkSwitch(
            binding_row,
            text="左綴じ対応（A3横Z折り・A3縦・A4横ページのみ位置変更）",
            variable=self.combine_pn_binding_compat_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_COMB_PRIMARY
        )
        self.combine_pn_binding_switch.pack(side="left")

        self._toggle_page_number_options()
        
        # 結合実行ボタン
        self.combination_combine_btn = ctk.CTkButton(
            self.combination_tab,
            text="📋 PDF結合実行",
            command=self._start_combination,
            height=40, state="disabled",
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            text_color="white", text_color_disabled="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.combination_combine_btn.pack(pady=(10, 10))
        
        # プログレスバー
        self.combination_progress = ctk.CTkProgressBar(self.combination_tab)
        self.combination_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.combination_progress.set(0)
        
        # ステータスラベル
        self.combination_status = ctk.CTkLabel(
            self.combination_tab,
            text="PDFファイルを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.combination_status.pack(pady=(0, 10))

    def _create_document_number_ui(self) -> None:
        """資料NO挿入タブUI"""
        ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルのヘッダー右上に、資料や参考などを挿入します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(pady=(10, 5))

        # ── ツールバー ──
        toolbar = ctk.CTkFrame(self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
                                border_width=1, border_color=CLR_BORDER, corner_radius=6)
        toolbar.pack(fill="x", padx=15, pady=(0, 5))

        self.document_select_btn = ctk.CTkButton(
            toolbar, text="PDF選択",
            command=self._select_document_number_files,
            height=32, width=90,
            fg_color=CLR_DOC_PRIMARY, hover_color=CLR_DOC_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        )
        self.document_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.document_delete_btn = ctk.CTkButton(
            toolbar, text="選択削除",
            command=self._delete_selected_document,
            height=32, width=80,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.document_delete_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_clear_btn = ctk.CTkButton(
            toolbar, text="クリア",
            command=self._clear_document_number_files,
            height=32, width=70,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.document_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_move_up_btn = ctk.CTkButton(
            toolbar, text="↑", command=self._move_document_up,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.document_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

        self.document_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_document_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.document_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_sort_btn = ctk.CTkButton(
            toolbar, text="Ａ↓",
            command=self._sort_document_files,
            height=32, width=46,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.document_sort_btn.pack(side="left", padx=(0, 4), pady=6)

        self.document_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
        )
        self.document_count_label.pack(side="right", padx=10, pady=6)

        # ドラッグアンドドロップ対応ファイルリスト
        self.document_draggable_list = DraggableFileList(
            self.document_number_tab,
            height=200,
            label_text="📋 資料NO挿入対象ファイルリスト（ドラッグで並び替え可能）"
        )
        self.document_draggable_list.pack(fill="both", expand=True, padx=15, pady=8)

        self.document_draggable_list.on_selection_change = self._on_document_selection_change
        self.document_draggable_list.on_order_change = self._on_document_order_change

        self.document_list_msg = ctk.CTkLabel(
            self.document_draggable_list,
            text="📋 PDFファイルをここにドラッグ&ドロップしてください\n\n・連番で資料NO（資料1, 資料2...）を自動挿入\n・ドラッグで順序変更、↑↓ボタンでも調整可能",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            justify="left"
        )
        self.document_list_msg.pack(fill="both", expand=True, padx=20, pady=20)

        # ── 設定フレーム（ファイルリスト下） ──
        settings_frame = ctk.CTkFrame(
            self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        settings_frame.pack(fill="x", padx=15, pady=(0, 5))

        # 行1: 挿入文字 + 開始番号
        row1 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            row1, text="文字選択:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=CLR_DARK_TEXT
        ).pack(side="left", padx=(0, 6))

        self.prefix_var = ctk.StringVar(value="資料")
        self.prefix_btn = ctk.CTkSegmentedButton(
            row1, values=["資料", "参考", "その他"],
            variable=self.prefix_var,
            command=self._on_prefix_changed,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.prefix_btn.pack(side="left", padx=(0, 8))

        self.custom_prefix_var = ctk.StringVar(value="")
        self.custom_prefix_entry = ctk.CTkEntry(
            row1, textvariable=self.custom_prefix_var,
            placeholder_text="例：別紙", width=100,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        # 初期状態は非表示（「資料」がデフォルト）
        self.custom_prefix_var.trace("w", self._on_numbering_settings_changed)

        self.number_label = ctk.CTkLabel(
            row1, text="開始番号:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=CLR_DARK_TEXT
        )
        self.number_label.pack(side="left", padx=(0, 6))

        self.number_var = ctk.StringVar(value="1")
        self.number_entry = ctk.CTkEntry(
            row1, textvariable=self.number_var,
            placeholder_text="1", width=70,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.number_entry.pack(side="left")
        self.number_var.trace("w", self._on_numbering_settings_changed)

        # 行2: 番号方式 + プレビュー
        row2 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkLabel(
            row2, text="番号方式:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=CLR_DARK_TEXT
        ).pack(side="left", padx=(0, 6))

        self.numbering_type_var = ctk.StringVar(value="連番")
        self.numbering_type_menu = ctk.CTkOptionMenu(
            row2,
            variable=self.numbering_type_var,
            values=["連番", "ハイフン連番", "固定番号", "番号なし"],
            width=140,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            command=self._on_numbering_type_changed
        )
        self.numbering_type_menu.pack(side="left", padx=(0, 16))

        self.preview_label = ctk.CTkLabel(
            row2, text="→ 「資料1, 資料2, 資料3...」",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=CLR_GRAY_TEXT
        )
        self.preview_label.pack(side="left")

        # 行2.5: フォント選択
        font_row_doc = ctk.CTkFrame(settings_frame, fg_color="transparent")
        font_row_doc.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(
            font_row_doc, text="フォント:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=CLR_DARK_TEXT
        ).pack(side="left", padx=(0, 6))

        self.doc_font_var = ctk.StringVar(value="メイリオ")
        ctk.CTkOptionMenu(
            font_row_doc,
            variable=self.doc_font_var,
            values=["メイリオ", "MSゴシック", "MS明朝", "游ゴシック", "BIZ UDPゴシック"],
            width=180,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        ).pack(side="left")

        # 行3: ファイル名変更オプション
        row3 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(0, 4))

        self.rename_file_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row3, text="ファイル名の先頭に資料番号を追加する（例: 【資料１】ファイル名.pdf）",
            variable=self.rename_file_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_DOC_PRIMARY
        ).pack(side="left")

        # 行4: A3縦ページ左綴じ対応オプション
        row4 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row4.pack(fill="x", padx=8, pady=(0, 8))

        self.a3_compat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row4, text="A3縦・A4横ページを左綴じ対応位置（右下）に挿入",
            variable=self.a3_compat_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_DOC_PRIMARY
        ).pack(side="left")

        # 実行ボタン + プレビューボタン
        doc_btn_frame = ctk.CTkFrame(self.document_number_tab, fg_color="transparent")
        doc_btn_frame.pack(pady=(8, 8))

        self.document_preview_btn = ctk.CTkButton(
            doc_btn_frame,
            text="🔍 プレビュー",
            command=self._show_document_number_preview,
            height=40, width=130, state="disabled",
            fg_color="transparent", border_width=1,
            text_color=CLR_DOC_PRIMARY,
            hover_color=CLR_LIGHT_BG,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        )
        self.document_preview_btn.pack(side="left", padx=(0, 8))

        self.document_execute_btn = ctk.CTkButton(
            doc_btn_frame,
            text="📄 資料NO挿入実行",
            command=self._start_document_number_insertion,
            height=40, state="disabled",
            fg_color=CLR_DOC_PRIMARY, hover_color=CLR_DOC_HOVER,
            text_color="white", text_color_disabled="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.document_execute_btn.pack(side="left")

        # プログレスバー
        self.document_progress = ctk.CTkProgressBar(self.document_number_tab)
        self.document_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.document_progress.set(0)

        # ステータスラベル
        self.document_status = ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルを選択して資料番号を入力してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.document_status.pack(pady=(0, 10))

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
        self.start_page_unit.configure(state=state)
        self.start_number_label.configure(state=state)
        self.start_number_entry.configure(state=state)
        self.combine_pn_binding_switch.configure(state=state)
    
    def _setup_drag_drop(self) -> None:
        """ドラッグ&ドロップ機能設定"""
        try:
            office_filter = drag_drop_handler.create_office_image_filter()
            pdf_filter = drag_drop_handler.create_pdf_filter()

            # 変換タブ全体をドロップターゲットに（タブ内どこでもD&D可能）
            drag_drop_handler.setup_drag_drop_recursive(
                self.conversion_tab,
                self._add_conversion_files,
                office_filter
            )
            self.conversion_draggable_list.set_external_drop(
                self._add_conversion_files,
                office_filter
            )

            # 結合タブ全体をドロップターゲットに
            drag_drop_handler.setup_drag_drop_recursive(
                self.combination_tab,
                self._add_combination_files,
                pdf_filter
            )
            self.combination_draggable_list.set_external_drop(
                self._add_combination_files,
                pdf_filter
            )

            # 資料NO挿入タブ全体をドロップターゲットに
            drag_drop_handler.setup_drag_drop_recursive(
                self.document_number_tab,
                self._add_document_number_files,
                pdf_filter
            )
            self.document_draggable_list.set_external_drop(
                self._add_document_number_files,
                pdf_filter
            )

            # ページ番号挿入タブ全体をドロップターゲットに
            drag_drop_handler.setup_drag_drop_recursive(
                self.pagenumber_tab,
                self._add_pagenumber_files,
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

    def _sort_document_files(self) -> None:
        """資料NO挿入リストをファイル名順に並び替え"""
        self.document_draggable_list.sort_by_filename()
        self._update_document_number_display()

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

    def _get_active_prefix(self) -> str:
        """現在有効なプレフィックス文字列を返す"""
        if self.prefix_var.get() == "その他":
            return self.custom_prefix_var.get().strip()
        return self.prefix_var.get()

    def _on_prefix_changed(self, value: str) -> None:
        """挿入文字変更時の処理"""
        if value == "その他":
            self.custom_prefix_entry.pack(side="left", padx=(0, 20))
            self.numbering_type_var.set("連番")
            self.number_var.set("1")
        else:
            self.custom_prefix_entry.pack_forget()
            if value == "参考":
                self.numbering_type_var.set("番号なし")
                self.number_var.set("0")
            else:
                self.numbering_type_var.set("連番")
                self.number_var.set("1")
        numbering_type = self.numbering_type_var.get()
        if numbering_type == "番号なし":
            self.number_label.configure(state="disabled")
            self.number_entry.configure(state="disabled")
        else:
            self.number_label.configure(state="normal")
            self.number_entry.configure(state="normal")
        self._update_numbering_preview()
        self._update_execute_button_state()

    def _on_numbering_type_changed(self, value: str) -> None:
        """番号方式変更時の処理"""
        if value == "番号なし":
            self.number_label.configure(state="disabled")
            self.number_entry.configure(state="disabled")
        else:
            self.number_label.configure(state="normal")
            self.number_entry.configure(state="normal")
            if value == "ハイフン連番":
                self.number_entry.configure(placeholder_text="1")
            else:
                self.number_entry.configure(placeholder_text="1")
        self._update_numbering_preview()
        self._update_execute_button_state()

    def _on_numbering_settings_changed(self, *args) -> None:
        """設定変更時の処理"""
        self._update_numbering_preview()
        self._update_execute_button_state()

    def _update_numbering_preview(self) -> None:
        """プレビュー更新"""
        prefix = self._get_active_prefix()
        numbering_type = self.numbering_type_var.get()
        number_value = self.number_var.get().strip()

        if numbering_type == "番号なし":
            preview_text = f"→ 「{prefix}」（全ファイル共通）"
        elif numbering_type == "固定番号":
            n = number_value if number_value else "5-3"
            preview_text = f"→ 「{prefix}{n}」（全ファイル共通）"
        elif numbering_type == "連番":
            if number_value and number_value.isdigit():
                s = int(number_value)
                if s == 0:
                    preview_text = f"→ 「{prefix}, {prefix}1, {prefix}2...」"
                else:
                    preview_text = f"→ 「{prefix}{s}, {prefix}{s+1}, {prefix}{s+2}...」"
            else:
                preview_text = f"→ 「{prefix}1, {prefix}2, {prefix}3...」"
        elif numbering_type == "ハイフン連番":
            p = number_value if number_value else "1"
            preview_text = f"→ 「{prefix}{p}-1, {prefix}{p}-2, {prefix}{p}-3...」"
        else:
            preview_text = f"→ 「{prefix}1, {prefix}2, {prefix}3...」"

        self.preview_label.configure(text=preview_text)

    def _update_execute_button_state(self) -> None:
        """実行ボタンの状態更新"""
        numbering_type = self.numbering_type_var.get()
        prefix_ok = bool(self._get_active_prefix())

        if numbering_type == "番号なし":
            ready = bool(self.document_number_files) and prefix_ok
        else:
            ready = bool(self.document_number_files and self.number_var.get().strip()) and prefix_ok
        state = "normal" if ready else "disabled"
        self.document_execute_btn.configure(state=state)
        self.document_preview_btn.configure(state="normal" if self.document_number_files else "disabled")

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
            self.document_preview_btn.configure(state="disabled")
            self.document_clear_btn.configure(state="disabled")
            self.document_count_label.configure(text="ファイル数: 0")
            self.document_status.configure(text="PDFファイルを追加して連番設定を行ってください")


    def _start_document_number_insertion(self) -> None:
        """連番資料NO挿入開始"""
        try:
            if not self.document_number_files:
                return

            number_value = self.number_var.get().strip()
            numbering_type_check = self.numbering_type_var.get()
            if not number_value and numbering_type_check != "番号なし":
                self.document_status.configure(text="番号を入力してください")
                return

            # 入力値のセキュリティ検証（番号なし以外）
            if number_value and not InputValidator.validate_document_number(number_value):
                error_handler.handle_error(
                    ValueError("無効な資料番号"),
                    ErrorSeverity.WARNING,
                    "入力検証",
                    "資料番号に無効な文字が含まれています。英数字、ひらがな、カタカナ、漢字のみ使用してください。"
                )
                return

            prefix = self._get_active_prefix()
            if not prefix:
                self.document_status.configure(text="挿入する文字を入力してください")
                return

            # 「その他」選択時はプレフィックス文字列を検証
            if self.prefix_var.get() == "その他":
                if not InputValidator.validate_prefix_text(prefix):
                    error_handler.handle_error(
                        ValueError("無効なプレフィックス"),
                        ErrorSeverity.WARNING,
                        "入力検証",
                        "入力した文字に使用できない文字が含まれています。記号（< > \" ' & ; ( ) { }）は使用不可です。10文字以内で入力してください。"
                    )
                    return
            numbering_type = self.numbering_type_var.get()

            # 確認メッセージを生成
            if numbering_type == "番号なし":
                preview = f"{prefix}（全ファイル共通）"
            elif numbering_type == "固定番号":
                preview = f"{prefix}{number_value}（全ファイル共通）"
            elif numbering_type == "連番":
                s = int(number_value) if number_value.isdigit() else 1
                preview = f"{prefix}{s}, {prefix}{s+1}, {prefix}{s+2}..."
            elif numbering_type == "ハイフン連番":
                preview = f"{prefix}{number_value}-1, {prefix}{number_value}-2, {prefix}{number_value}-3..."
            else:
                preview = f"{prefix}1, {prefix}2, {prefix}3..."

            # 確認メッセージ
            result = messagebox.askyesno(
                "挿入の確認",
                f"以下の内容で挿入を実行しますか？\n\n"
                f"• 対象ファイル数: {len(self.document_number_files)}個\n"
                f"• 挿入文字: {prefix}\n"
                f"• 番号方式: {numbering_type}\n"
                f"• パターン: {preview}\n\n"
                f"注意: 元ファイルは「元ファイル」フォルダに自動バックアップされ、\n"
                f"同じファイル名で挿入済みファイルが保存されます。"
            )

            if not result:
                return

            # UIを無効化
            self.document_execute_btn.configure(state="disabled")
            self.document_status.configure(text="資料NO挿入処理中...")
            self.document_progress.set(0)

            # 別スレッドで処理実行
            rename_file = self.rename_file_var.get()
            a3_compat = self.a3_compat_var.get()
            selected_font = self.doc_font_var.get()
            thread = threading.Thread(target=self._run_sequential_number_insertion, args=(prefix, numbering_type, number_value, rename_file, a3_compat, selected_font))
            thread.daemon = True
            thread.start()

        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorSeverity.CRITICAL,
                "資料NO挿入開始",
                "資料NO挿入処理の開始中にエラーが発生しました。"
            )

    def _run_sequential_number_insertion(self, prefix: str, numbering_type: str, number_value: str, rename_file: bool = False, a3_portrait_compat: bool = False, selected_font: str = "メイリオ") -> None:
        """挿入実行（別スレッド）"""
        try:
            self.pdf_combiner.set_user_font(selected_font)

            def progress_callback(message, progress):
                self.root.after(0, lambda: self.document_progress.set(progress / 100))
                self.root.after(0, lambda: self.document_status.configure(text=message))

            # 固定番号モードは add_document_numbers を使用
            if numbering_type == "固定番号":
                result = self.pdf_combiner.add_document_numbers(
                    pdf_paths=self.document_number_files.copy(),
                    output_path="",
                    document_number=number_value,
                    document_prefix=prefix,
                    rename_file=rename_file,
                    a3_portrait_compat=a3_portrait_compat,
                    progress_callback=progress_callback
                )
            else:
                # 番号方式をバックエンド内部名に変換
                if numbering_type == "番号なし":
                    internal_type = "none"
                elif numbering_type == "連番":
                    internal_type = "start_at"
                elif numbering_type == "ハイフン連番":
                    internal_type = "hyphen"
                else:
                    internal_type = "start_at"

                start_number = int(number_value) if number_value.isdigit() else 1
                prefix_number = number_value if number_value else "1"

                result = self.pdf_combiner.add_sequential_document_numbers(
                    pdf_paths=self.document_number_files.copy(),
                    output_dir="",
                    numbering_type=internal_type,
                    start_number=start_number,
                    prefix_number=prefix_number,
                    document_prefix=prefix,
                    rename_file=rename_file,
                    a3_portrait_compat=a3_portrait_compat,
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
            messagebox.showinfo("資料NO挿入完了", message)

            processed = result.processed_files[:]

            def open_folder():
                if processed:
                    self._open_folder(str(Path(processed[0]).parent))

            if len(processed) >= 2:
                self._show_combination_offer(processed, on_no_callback=open_folder)
            else:
                open_folder()
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

    def _sort_combination_files(self) -> None:
        """PDF結合リストをファイル名順に並び替え"""
        self.combination_draggable_list.sort_by_filename()
        self._update_combination_display()

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

            # 資料NO挿入提案ダイアログ
            if len(all_successful_paths) >= 1:
                self._show_document_number_offer(all_successful_paths, on_no_callback=open_folder_callback)
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
    
    def _show_document_number_offer(self, pdf_files: List[str], on_no_callback=None) -> None:
        """資料NO挿入提案ダイアログ"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("資料NO挿入")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()

        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        dialog.geometry(f"350x150+{x}+{y}")

        msg_label = ctk.CTkLabel(
            dialog,
            text=f"変換したPDFファイル({len(pdf_files)}個)に\n資料NOを挿入しますか？",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        msg_label.pack(pady=20)

        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)

        def on_yes():
            dialog.destroy()
            self._clear_document_number_files()
            if len(pdf_files) > 1:
                self.numbering_type_var.set("連番")
                self._on_numbering_type_changed("連番")
            self._add_document_number_files(pdf_files)
            self._switch_tab("資料NO挿入")

        def on_no():
            dialog.destroy()
            if on_no_callback:
                on_no_callback()

        yes_btn = ctk.CTkButton(btn_frame, text="はい", command=on_yes, width=80)
        yes_btn.pack(side="left", padx=10)

        no_btn = ctk.CTkButton(btn_frame, text="いいえ", command=on_no, width=80)
        no_btn.pack(side="left", padx=10)

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
            text=f"PDFファイル({len(pdf_files)}個)を\n結合しますか？",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        msg_label.pack(pady=20)

        # ボタンフレーム
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)

        def on_yes():
            dialog.destroy()
            self._clear_combination_files()
            self._add_combination_files(pdf_files)
            self._switch_tab("PDF結合")

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
        pn_binding_compat = self.combine_pn_binding_compat_var.get() if add_page_numbers else False

        # 別スレッドで結合実行
        thread = threading.Thread(target=self._run_combination, args=(output_path, add_blank_page, add_page_numbers, start_page, start_number, pn_binding_compat))
        thread.daemon = True
        thread.start()
    
    def _run_combination(self, output_path: str, add_blank_page: bool, add_page_numbers: bool, start_page: int, start_number: int, pn_binding_compat: bool = False) -> None:
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
                progress_callback,
                page_number_binding_compat=pn_binding_compat
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
    
    # ════════════════════════════════════════════════════════════
    # ページ番号挿入タブ
    # ════════════════════════════════════════════════════════════

    def _create_pagenumber_ui(self) -> None:
        """ページ番号挿入タブUI（1ファイル専用・シンプル）"""
        ctk.CTkLabel(
            self.pagenumber_tab,
            text="1つのPDFファイルにページ番号を挿入します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(pady=(10, 5))

        # ── ツールバー ──
        pn_toolbar = ctk.CTkFrame(self.pagenumber_tab, fg_color=CLR_TOOLBAR_BG,
                                  border_width=1, border_color=CLR_BORDER, corner_radius=6)
        pn_toolbar.pack(fill="x", padx=15, pady=(0, 5))

        self.pn_select_btn = ctk.CTkButton(
            pn_toolbar, text="PDF選択",
            command=self._select_pagenumber_file,
            height=32, width=90,
            fg_color=CLR_PN_PRIMARY, hover_color=CLR_PN_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        )
        self.pn_select_btn.pack(side="left", padx=(8, 4), pady=6)

        self.pn_clear_btn = ctk.CTkButton(
            pn_toolbar, text="クリア",
            command=self._clear_pagenumber_file,
            height=32, width=70,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.pn_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        # ── ファイル選択エリア ──
        self.pn_drop_frame = ctk.CTkFrame(
            self.pagenumber_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=2, border_color=CLR_BORDER, corner_radius=8
        )
        self.pn_drop_frame.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        self.pn_drop_label = ctk.CTkLabel(
            self.pn_drop_frame,
            text="📄 PDFファイルをここにドラッグ&ドロップ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=CLR_GRAY_TEXT, justify="center"
        )
        self.pn_drop_label.pack(expand=True)

        # 選択済みファイル表示（初期は非表示）
        self.pn_file_frame = ctk.CTkFrame(
            self.pn_drop_frame, fg_color=CLR_LIGHT_BG,
            border_width=1, border_color=CLR_SEL_BORDER, corner_radius=6
        )
        self.pn_file_label = ctk.CTkLabel(
            self.pn_file_frame, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=CLR_DARK_TEXT
        )
        self.pn_file_label.pack(side="left", padx=12, pady=8)
        self.pn_clear_file_btn = ctk.CTkButton(
            self.pn_file_frame, text="✕", width=26, height=26,
            fg_color="transparent", hover_color=CLR_RED_LIGHT,
            text_color=CLR_RED_TEXT, font=ctk.CTkFont(size=11),
            command=self._clear_pagenumber_file
        )
        self.pn_clear_file_btn.pack(side="right", padx=8, pady=8)

        # ── オプション ──
        opt_frame = ctk.CTkFrame(
            self.pagenumber_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        opt_frame.pack(fill="x", padx=15, pady=(0, 8))

        opt_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(opt_row, text="開始ページ:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(0, 4))

        self.pn_start_page_var = ctk.StringVar(value="1")
        ctk.CTkEntry(opt_row, textvariable=self.pn_start_page_var, width=52,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left")

        ctk.CTkLabel(opt_row, text="ページ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(4, 24))

        ctk.CTkLabel(opt_row, text="開始番号:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(0, 4))

        self.pn_start_number_var = ctk.StringVar(value="1")
        ctk.CTkEntry(opt_row, textvariable=self.pn_start_number_var, width=52,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left")

        # フォント選択
        pn_font_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        pn_font_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            pn_font_row, text="フォント:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(0, 6))

        self.pn_font_var = ctk.StringVar(value="メイリオ")
        ctk.CTkOptionMenu(
            pn_font_row,
            variable=self.pn_font_var,
            values=["メイリオ", "MSゴシック", "MS明朝", "游ゴシック", "BIZ UDPゴシック"],
            width=180,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        ).pack(side="left")

        # 左綴じ対応スイッチ
        binding_row2 = ctk.CTkFrame(opt_frame, fg_color="transparent")
        binding_row2.pack(fill="x", padx=12, pady=(0, 8))

        self.pn_binding_compat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            binding_row2,
            text="左綴じ対応（A3横Z折り・A3縦・A4横ページのみ位置変更）",
            variable=self.pn_binding_compat_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color="#553C9A"
        ).pack(side="left")

        # ── 実行ボタン + プレビューボタン ──
        pn_btn_frame = ctk.CTkFrame(self.pagenumber_tab, fg_color="transparent")
        pn_btn_frame.pack(pady=(4, 8))

        self.pn_preview_btn = ctk.CTkButton(
            pn_btn_frame,
            text="🔍 プレビュー",
            command=self._show_page_number_preview,
            height=40, width=130, state="disabled",
            fg_color="transparent", border_width=1,
            text_color="#553C9A",
            hover_color=CLR_LIGHT_BG,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        )
        self.pn_preview_btn.pack(side="left", padx=(0, 8))

        self.pn_execute_btn = ctk.CTkButton(
            pn_btn_frame,
            text="📄 ページ番号挿入実行",
            command=self._start_pagenumber_insertion,
            height=40, state="disabled",
            fg_color=CLR_PN_PRIMARY, hover_color=CLR_PN_HOVER,
            text_color="white", text_color_disabled="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.pn_execute_btn.pack(side="left")

        self.pn_progress = ctk.CTkProgressBar(self.pagenumber_tab)
        self.pn_progress.pack(fill="x", padx=15, pady=(0, 8))
        self.pn_progress.set(0)

        self.pn_status = ctk.CTkLabel(
            self.pagenumber_tab, text="PDFファイルを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.pn_status.pack(pady=(0, 10))

    # ── ファイル操作 ─────────────────────────────────────────────

    def _select_pagenumber_file(self) -> None:
        file = fd.askopenfilename(
            title="ページ番号を挿入するPDFを選択",
            filetypes=[("PDFファイル", "*.pdf"), ("すべてのファイル", "*.*")]
        )
        if file:
            self._set_pagenumber_file(file)

    def _add_pagenumber_files(self, paths: List[str]) -> None:
        """D&Dコールバック（最初のPDFのみ使用）"""
        pdf_files = [p for p in paths if Path(p).suffix.lower() == '.pdf' and Path(p).is_file()]
        if pdf_files:
            self._set_pagenumber_file(pdf_files[0])

    def _set_pagenumber_file(self, path: str) -> None:
        self.pagenumber_files = [path]
        name = Path(path).name
        display = name if len(name) <= 40 else name[:37] + "..."
        self.pn_file_label.configure(text=f"📄  {display}")
        self.pn_drop_label.pack_forget()
        self.pn_file_frame.pack(fill="x", padx=12, pady=12)
        self.pn_clear_btn.configure(state="normal")
        self.pn_execute_btn.configure(state="normal")
        self.pn_preview_btn.configure(state="normal")
        self.pn_status.configure(text=f"選択済み: {name}")

    def _clear_pagenumber_file(self) -> None:
        self.pagenumber_files = []
        self.pn_file_frame.pack_forget()
        self.pn_drop_label.pack(expand=True)
        self.pn_clear_btn.configure(state="disabled")
        self.pn_execute_btn.configure(state="disabled")
        self.pn_preview_btn.configure(state="disabled")
        self.pn_status.configure(text="PDFファイルを選択してください")
        self.pn_progress.set(0)

    # ── 実行 ────────────────────────────────────────────────────

    def _start_pagenumber_insertion(self) -> None:
        if not self.pagenumber_files:
            return
        try:
            start_page   = int(self.pn_start_page_var.get())
            start_number = int(self.pn_start_number_var.get())
        except ValueError:
            messagebox.showwarning("入力エラー", "開始ページと開始番号には数字を入力してください。")
            return

        pdf_path = self.pagenumber_files[0]
        confirmed = messagebox.askyesno(
            "ページ番号挿入の確認",
            f"以下の内容でページ番号を挿入しますか？\n\n"
            f"• 対象ファイル: {Path(pdf_path).name}\n"
            f"• 開始ページ: {start_page}ページ目から\n"
            f"• 開始番号: {start_number}\n\n"
            f"注意: 元ファイルは「元ファイル」フォルダに自動バックアップされ、\n"
            f"同じファイル名で挿入済みファイルが保存されます。"
        )
        if not confirmed:
            return

        self.pn_execute_btn.configure(state="disabled")
        self.pn_preview_btn.configure(state="disabled")
        self.pn_status.configure(text="処理中...")
        self.pn_progress.set(0)

        binding_compat = self.pn_binding_compat_var.get()
        selected_font = self.pn_font_var.get()
        threading.Thread(
            target=self._run_pagenumber_insertion,
            args=(pdf_path, start_page, start_number, binding_compat, selected_font),
            daemon=True
        ).start()

    def _run_pagenumber_insertion(self, pdf_path: str, start_page: int, start_number: int, binding_compat: bool = False, selected_font: str = "メイリオ") -> None:
        tmp_path = None
        try:
            self.pdf_combiner.set_user_font(selected_font)

            def on_progress(message, progress):
                self.root.after(0, lambda: self.pn_progress.set(progress / 100))
                self.root.after(0, lambda: self.pn_status.configure(text=message))

            pdf_path_obj = Path(pdf_path)

            # 同ディレクトリに一時ファイルを作成
            fd_tmp, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=pdf_path_obj.parent)
            os.close(fd_tmp)

            result = self.pdf_combiner.combine_pdfs(
                [pdf_path],
                tmp_path,
                add_blank_page=False,
                add_page_numbers=True,
                start_page=start_page,
                start_number=start_number,
                progress_callback=on_progress,
                page_number_binding_compat=binding_compat
            )

            if result.success:
                # 元ファイルをバックアップ
                backup_dir = pdf_path_obj.parent / "元ファイル"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / pdf_path_obj.name
                if backup_path.exists():
                    backup_path.unlink()
                shutil.copy2(pdf_path, backup_path)
                # 一時ファイルで元ファイルを上書き
                shutil.move(tmp_path, pdf_path)
                tmp_path = None
                result.output_path = pdf_path
            else:
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass
                tmp_path = None

            self.root.after(0, lambda: self._on_pagenumber_complete(result))

        except Exception as e:
            if tmp_path:
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass
            from ..utils.error_handler import ErrorSeverity
            self.root.after(0, lambda: error_handler.handle_error(
                e, ErrorSeverity.CRITICAL, "ページ番号挿入"
            ))
            self.root.after(0, lambda: self.pn_execute_btn.configure(state="normal"))
            self.root.after(0, lambda: self.pn_preview_btn.configure(
                state="normal" if self.pagenumber_files else "disabled"
            ))

    def _on_pagenumber_complete(self, result) -> None:
        self.pn_progress.set(1.0)
        if result.success:
            msg = (f"ページ番号挿入が完了しました！\n\n"
                   f"• 総ページ数: {result.total_pages}ページ\n"
                   f"• 出力ファイル: {Path(result.output_path).name}\n"
                   f"• 処理時間: {result.processing_time:.1f}秒\n\n"
                   f"元ファイルは「元ファイル」フォルダに保存されました。")
            self.pn_status.configure(text=f"完了: {result.total_pages}ページ")
            self._show_and_open_results("ページ番号挿入完了", msg, [result.output_path])
            self._clear_pagenumber_file()
        else:
            messagebox.showerror("エラー", f"処理に失敗しました。\n\n{result.error_message}")
            self.pn_status.configure(text="エラーが発生しました")
            self.pn_execute_btn.configure(state="normal")
            self.pn_preview_btn.configure(
                state="normal" if self.pagenumber_files else "disabled"
            )

    # ── プレビュー ──────────────────────────────────────────────────

    def _show_document_number_preview(self) -> None:
        """資料NO挿入のプレビューダイアログを開く"""
        if not self.document_number_files:
            return
        pdf_path = self.document_number_files[0]
        prefix = self.prefix_var.get()
        number_value = self.number_var.get().strip()
        numbering_type = self.numbering_type_var.get()
        a3_compat = self.a3_compat_var.get()

        # 最初のファイルに付く資料番号テキストを構築
        if numbering_type == "番号なし":
            doc_text = prefix
        elif numbering_type == "固定番号":
            doc_text = f"{prefix}{number_value}"
        elif numbering_type == "ハイフン連番":
            doc_text = f"{prefix}{number_value}-1"
        else:  # 連番
            start = number_value if number_value else "1"
            doc_text = f"{prefix}{start}"

        render_fn = lambda: render_doc_number_preview(pdf_path, doc_text, a3_compat)
        PDFPreviewDialog(self.root, f"プレビュー（資料番号: {doc_text}）", render_fn)

    def _show_page_number_preview(self) -> None:
        """ページ番号挿入のプレビューダイアログを開く"""
        if not self.pagenumber_files:
            return
        pdf_path = self.pagenumber_files[0]
        try:
            start_number = int(self.pn_start_number_var.get())
        except ValueError:
            start_number = 1
        binding_compat = self.pn_binding_compat_var.get()
        page_number_text = str(start_number)

        render_fn = lambda: render_page_number_preview(pdf_path, page_number_text, binding_compat)
        PDFPreviewDialog(self.root, f"プレビュー（ページ番号: {page_number_text}）", render_fn)

    def _open_help(self) -> None:
        """ヘルプダイアログを開く"""
        HelpDialog(self.root)

    def run(self) -> None:
        """アプリケーション実行"""
        logger.info("統合アプリケーション実行開始")
        self.root.mainloop()