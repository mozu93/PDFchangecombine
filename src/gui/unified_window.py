"""
統合ウィンドウ - タブ形式UI
ユーザビリティ向上のための改善版
"""

import customtkinter as ctk
import tkinter as tk
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
    ALL_SUPPORTED_EXTENSIONS,
    CONVERSION_OUTPUT_FOLDER_NAME, DOCUMENT_OUTPUT_FOLDER_NAME,
    COMBINATION_OUTPUT_FOLDER_NAME, PAGENUMBER_OUTPUT_FOLDER_NAME,
)
from ..utils.logger import logger
from ..utils.drag_drop import drag_drop_handler
from ..utils.file_utils import FileScanner, OutputManager
from ..utils.security import SecurityValidator, InputValidator
from .draggable_list import DraggableFileList
from .update_banner import UpdateBanner
from .help_dialog import HelpDialog
from .preview_dialog import PDFPreviewDialog, render_doc_number_preview, render_page_number_preview
from .result_dialog import FailureDetailDialog
from .completion_banner import CompletionBanner
from .confirm_dialog import confirm_with_skip
from .theme import (
    CLR_PRIMARY, CLR_ACCENT, CLR_LIGHT_BG, CLR_LIGHT_BORDER,
    CLR_SEL_BORDER, CLR_TOOLBAR_BG, CLR_BORDER, CLR_RED_LIGHT,
    CLR_RED_TEXT, CLR_GRAY_TEXT, CLR_DARK_TEXT, CLR_LIST_HEADER,
    CLR_WHITE, get_file_type_badge,
    CLR_DISABLED_BG, CLR_DISABLED_TEXT,
    FONT_FAMILY,
    TAB_CONVERSION, TAB_COMBINATION, TAB_DOCUMENT, TAB_PAGENUMBER, TAB_INACTIVE,
    CLR_CONV_PRIMARY, CLR_CONV_HOVER,
    CLR_COMB_PRIMARY, CLR_COMB_HOVER,
    CLR_DOC_PRIMARY,  CLR_DOC_HOVER,
    CLR_PN_PRIMARY,   CLR_PN_HOVER,
)
from ..utils.error_handler import error_handler, ErrorSeverity
from ..utils.settings import load_settings, save_settings, DEFAULT_SETTINGS
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
        self._init_tooltip_manager()

        # コア機能
        self.pdf_converter = PDFConverter()
        self.pdf_combiner = PDFCombiner()
        
        # 状態管理
        self.conversion_files: List[str] = []
        self.combination_files: List[str] = []
        self.document_number_files: List[str] = []  # 資料NO挿入用ファイル（旧式、互換性のため残す）

        # PDF変換のキャンセル制御（ファイル境界で中断）
        self._conversion_cancel_event = threading.Event()

        # オプション管理
        self.split_excel_sheets_var = ctk.BooleanVar(value=False)
        self.pagenumber_files: List[str] = []

        # 完了後にフォルダを自動的に開くか（設定で永続化）
        self.auto_open_output_folder_var = ctk.BooleanVar(value=True)
        # 確認ダイアログの「今後表示しない」フラグ（設定で永続化）
        self.skip_confirm_document_number = False
        self.skip_confirm_pagenumber = False

        # 出力先ディレクトリ（各タブ）
        self.conversion_output_dir: str = ""
        self.document_output_dir: str = ""
        self.combination_output_dir: str = ""
        self.pagenumber_output_dir: str = ""

        # UI作成
        self._create_main_ui()
        self._setup_drag_drop()
        self._setup_keyboard_shortcuts()

        # 前回終了時の設定を復元
        self._load_user_settings()

        # エラーハンドラー設定
        error_handler.parent_window = self.root

        self._log_startup_time()
    
    def _setup_window(self) -> None:
        """ウィンドウ初期設定"""
        self.root.title(WINDOW_TITLE)

        # 画面サイズに合わせてウィンドウ高さを自動調整
        self.root.update_idletasks()
        screen_h = self.root.winfo_screenheight()
        # タスクバー・タイトルバー等を考慮して画面高さ - 80px を上限にする
        max_h = screen_h - 80
        win_h = min(WINDOW_HEIGHT, max_h)
        win_h = max(win_h, WINDOW_MIN_HEIGHT)  # 最小高さは保証

        # インスタンス変数に保存（_set_window_icon で再利用）
        self._win_h = win_h

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

        # ウィンドウを中央に配置（_setup_windowで計算済みのサイズを再利用）
        win_h = getattr(self, '_win_h', WINDOW_HEIGHT)
        x = (self.root.winfo_screenwidth() // 2) - (WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (win_h // 2)
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

        help_btn = ctk.CTkButton(
            header_frame,
            text="?",
            width=32, height=32,
            corner_radius=16,
            fg_color="#3D82C4",
            hover_color="#5494D6",
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            command=self._open_help,
        )
        help_btn.pack(side="right", padx=12, pady=10)
        self._attach_tooltip(help_btn, "使い方・バージョン情報を表示")

        settings_reset_btn = ctk.CTkButton(
            header_frame,
            text="⚙",
            width=32, height=32,
            corner_radius=16,
            fg_color="#3D82C4",
            hover_color="#5494D6",
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            command=self._reset_settings_to_default,
        )
        settings_reset_btn.pack(side="right", padx=(0, 4), pady=10)
        self._attach_tooltip(settings_reset_btn, "設定をデフォルトに戻す")

        auto_open_switch = ctk.CTkSwitch(
            header_frame, text="自動で開く",
            variable=self.auto_open_output_folder_var,
            onvalue=True, offvalue=False,
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            progress_color="#3D82C4"
        )
        auto_open_switch.pack(side="right", padx=(0, 12), pady=10)
        self._attach_tooltip(auto_open_switch, "処理完了後に出力フォルダを自動的に開く")

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
        self._current_tab = name
    
    def _create_conversion_ui(self) -> None:
        """PDF変換タブUI"""
        # 説明ラベル
        ctk.CTkLabel(
            self.conversion_tab,
            text="Office文書・画像ファイルをPDFに変換します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(pady=(10, 5))

        self.conversion_banner = CompletionBanner(self.conversion_tab, CLR_CONV_PRIMARY, CLR_CONV_HOVER)
        self.conversion_banner.pack(fill="x", padx=15, pady=(0, 4))

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
            toolbar, text="クリア",
            command=self._clear_all_conversion,
            height=32, width=80,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.conversion_clear_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_retry_failed_btn = ctk.CTkButton(
            toolbar, text="⟲ 失敗のみ再実行",
            command=self._retry_failed_conversion,
            height=32, width=130,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="disabled"
        )
        self.conversion_retry_failed_btn.pack(side="left", padx=(0, 4), pady=6)

        self.conversion_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
        )
        self.conversion_count_label.pack(side="right", padx=10, pady=6)

        # ── 出力先フォルダ行 ──
        conv_out_frame = ctk.CTkFrame(self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
                                      border_width=1, border_color=CLR_BORDER, corner_radius=6)
        conv_out_frame.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(conv_out_frame, text="出力先:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13)).pack(side="left", padx=(8, 4), pady=5)
        self.conversion_change_output_btn = ctk.CTkButton(
            conv_out_frame, text="📂 変更", command=self._change_conversion_output_dir,
            height=26, width=80, fg_color=CLR_CONV_PRIMARY, hover_color=CLR_CONV_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        # 右側のボタンを先にpackして幅を確保してから、残り幅を出力先ラベルに埋めさせる
        # （先にfill=x,expand=Trueのラベルをpackすると、後からpackする側のウィジェットが
        # 　幅0に押し潰されることがあるため）
        self.conversion_change_output_btn.pack(side="right", padx=(4, 8), pady=5)
        self.conversion_output_dir_label = ctk.CTkLabel(
            conv_out_frame, text="（最初のファイルと同じフォルダ）",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT, anchor="w"
        )
        self.conversion_output_dir_label.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self._attach_tooltip(self.conversion_output_dir_label,
            lambda: OutputManager.resolve_output_dir(
                self.conversion_output_dir, self.conversion_files, CONVERSION_OUTPUT_FOLDER_NAME))

        # ── 下部固定エリア（draggable_listより先にpackして画面下部に固定） ──

        # ステータスラベル（一番下）
        self.conversion_status = ctk.CTkLabel(
            self.conversion_tab,
            text="ファイルを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.conversion_status.pack(side="bottom", pady=(0, 8))

        # プログレスバー
        self.conversion_progress = ctk.CTkProgressBar(self.conversion_tab)
        self.conversion_progress.pack(side="bottom", fill="x", padx=15, pady=(0, 4))
        self.conversion_progress.set(0)

        # 変換実行ボタン
        self.conversion_convert_btn = ctk.CTkButton(
            self.conversion_tab,
            text="🔄 PDF変換実行",
            command=self._start_conversion,
            height=40, state="disabled",
            fg_color=CLR_DISABLED_BG, hover_color=CLR_DISABLED_BG,
            text_color="white", text_color_disabled=CLR_DISABLED_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.conversion_convert_btn.pack(side="bottom", pady=(6, 6))

        # Excelシート分割オプション
        self.excel_options_frame = ctk.CTkFrame(
            self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        self.excel_options_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 4))

        self.split_excel_sheets_switch = ctk.CTkSwitch(
            self.excel_options_frame,
            text="Excelシートが複数ある場合は、すべてのシートをそれぞれPDFに変換する",
            variable=self.split_excel_sheets_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_CONV_PRIMARY
        )
        self.split_excel_sheets_switch.pack(side="left", padx=(10, 8), pady=6)

        # ── ファイルリスト（残りのスペースを占有） ──
        self.conversion_draggable_list = DraggableFileList(
            self.conversion_tab,
            drag_enabled=False,
            height=200,
            label_text="📁 変換対象ファイルリスト"
        )
        self.conversion_draggable_list.pack(fill="both", expand=True, padx=15, pady=(0, 4))
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
    
    def _create_combination_ui(self) -> None:
        """PDF結合タブUI"""
        # 説明ラベル
        desc_label = ctk.CTkLabel(
            self.combination_tab,
            text="複数のPDFファイルを1つに結合します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        desc_label.pack(pady=(10, 5))

        self.combination_banner = CompletionBanner(self.combination_tab, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
        self.combination_banner.pack(fill="x", padx=15, pady=(0, 4))
        
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
        self._attach_tooltip(self.combination_move_up_btn, "選択したファイルを上に移動")

        self.combination_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_combination_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.combination_move_down_btn.pack(side="left", padx=(0, 4), pady=6)
        self._attach_tooltip(self.combination_move_down_btn, "選択したファイルを下に移動")

        self.combination_sort_btn = ctk.CTkButton(
            toolbar, text="Ａ↓",
            command=self._sort_combination_files,
            height=32, width=46,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.combination_sort_btn.pack(side="left", padx=(0, 4), pady=6)
        self._attach_tooltip(self.combination_sort_btn, "ファイル名の昇順（自然順）に並び替え")

        self.combination_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
        )
        self.combination_count_label.pack(side="right", padx=10, pady=6)

        # ── 出力先フォルダ行 ──
        comb_out_frame = ctk.CTkFrame(self.combination_tab, fg_color=CLR_TOOLBAR_BG,
                                      border_width=1, border_color=CLR_BORDER, corner_radius=6)
        comb_out_frame.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(comb_out_frame, text="出力先:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13)).pack(side="left", padx=(8, 4), pady=5)
        ctk.CTkButton(
            comb_out_frame, text="📂 変更", command=self._change_combination_output_dir,
            height=26, width=80, fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        ).pack(side="right", padx=(4, 8), pady=5)
        self.combination_output_dir_label = ctk.CTkLabel(
            comb_out_frame, text="（最初のファイルと同じフォルダ）",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT, anchor="w"
        )
        self.combination_output_dir_label.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self._attach_tooltip(self.combination_output_dir_label,
            lambda: OutputManager.resolve_output_dir(
                self.combination_output_dir, self.combination_files, COMBINATION_OUTPUT_FOLDER_NAME))

        # ── 下部固定エリア（draggable_listより先にpackして画面下部に固定） ──

        # ステータスラベル（一番下に固定）
        self.combination_status = ctk.CTkLabel(
            self.combination_tab,
            text="PDFファイルを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.combination_status.pack(side="bottom", pady=(0, 8))

        # プログレスバー
        self.combination_progress = ctk.CTkProgressBar(self.combination_tab)
        self.combination_progress.pack(side="bottom", fill="x", padx=15, pady=(0, 4))
        self.combination_progress.set(0)

        # 結合実行ボタン
        self.combination_combine_btn = ctk.CTkButton(
            self.combination_tab,
            text="📋 PDF結合実行",
            command=self._start_combination,
            height=40, state="disabled",
            fg_color=CLR_DISABLED_BG, hover_color=CLR_DISABLED_BG,
            text_color="white", text_color_disabled=CLR_DISABLED_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.combination_combine_btn.pack(side="bottom", pady=(6, 6))

        # オプションフレーム（白紙挿入 + ページ番号）
        self.add_blank_page_var = ctk.BooleanVar()
        self.add_page_number_var = ctk.BooleanVar()
        self.combine_pn_binding_compat_var = ctk.BooleanVar(value=False)

        options_frame = ctk.CTkFrame(
            self.combination_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        options_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 4))

        # 白紙挿入スイッチ
        blank_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        blank_row.pack(fill="x", padx=8, pady=(4, 2))

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
        sub_row.pack(fill="x", padx=(30, 8), pady=(0, 2))

        self.start_page_label = ctk.CTkLabel(
            sub_row, text="開始ページ:", font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self.start_page_label.pack(side="left", padx=(0, 4))

        self.start_page_var = ctk.StringVar(value="1")
        self.start_page_entry = ctk.CTkEntry(
            sub_row, textvariable=self.start_page_var, width=40
        )
        self.start_page_entry.pack(side="left")
        self._make_digits_only(self.start_page_entry)

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
        self._make_digits_only(self.start_number_entry)

        # 左綴じ対応スイッチ（ページ番号オプションの下）
        binding_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        binding_row.pack(fill="x", padx=(30, 8), pady=(0, 4))

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

        # ── ファイルリスト（残りのスペースを占有） ──
        self.combination_draggable_list = DraggableFileList(
            self.combination_tab,
            height=200,
            label_text="📋 PDFファイル結合リスト（ドラッグで並び替え可能）"
        )
        self.combination_draggable_list.pack(fill="both", expand=True, padx=15, pady=(0, 4))

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

    def _create_document_number_ui(self) -> None:
        """資料NO挿入タブUI"""
        ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルのヘッダー右上に、資料や参考などを挿入します",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(pady=(10, 5))

        self.document_banner = CompletionBanner(self.document_number_tab, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
        self.document_banner.pack(fill="x", padx=15, pady=(0, 4))

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
        self._attach_tooltip(self.document_move_up_btn, "選択したファイルを上に移動")

        self.document_move_down_btn = ctk.CTkButton(
            toolbar, text="↓", command=self._move_document_down,
            height=32, width=36,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.document_move_down_btn.pack(side="left", padx=(0, 4), pady=6)
        self._attach_tooltip(self.document_move_down_btn, "選択したファイルを下に移動")

        self.document_sort_btn = ctk.CTkButton(
            toolbar, text="Ａ↓",
            command=self._sort_document_files,
            height=32, width=46,
            fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
            hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self.document_sort_btn.pack(side="left", padx=(0, 4), pady=6)
        self._attach_tooltip(self.document_sort_btn, "ファイル名の昇順（自然順）に並び替え")

        self.document_count_label = ctk.CTkLabel(
            toolbar, text="ファイル数: 0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=CLR_GRAY_TEXT
        )
        self.document_count_label.pack(side="right", padx=10, pady=6)

        # ── 出力先フォルダ行 ──
        doc_out_frame = ctk.CTkFrame(self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
                                     border_width=1, border_color=CLR_BORDER, corner_radius=6)
        doc_out_frame.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(doc_out_frame, text="出力先:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13)).pack(side="left", padx=(8, 4), pady=5)
        ctk.CTkButton(
            doc_out_frame, text="📂 変更", command=self._change_document_output_dir,
            height=26, width=80, fg_color=CLR_DOC_PRIMARY, hover_color=CLR_DOC_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        ).pack(side="right", padx=(4, 8), pady=5)
        self.document_output_dir_label = ctk.CTkLabel(
            doc_out_frame, text="（最初のファイルと同じフォルダ）",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT, anchor="w"
        )
        self.document_output_dir_label.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self._attach_tooltip(self.document_output_dir_label,
            lambda: OutputManager.resolve_output_dir(
                self.document_output_dir, self.document_number_files, DOCUMENT_OUTPUT_FOLDER_NAME))

        # ── 下部固定エリア（draggable_listより先にpackして画面下部に固定） ──

        # ステータスラベル（一番下に固定）
        self.document_status = ctk.CTkLabel(
            self.document_number_tab,
            text="PDFファイルを選択して資料番号を入力してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.document_status.pack(side="bottom", pady=(0, 8))

        # プログレスバー
        self.document_progress = ctk.CTkProgressBar(self.document_number_tab)
        self.document_progress.pack(side="bottom", fill="x", padx=15, pady=(0, 4))
        self.document_progress.set(0)

        # 実行ボタン + プレビューボタン
        doc_btn_frame = ctk.CTkFrame(self.document_number_tab, fg_color="transparent")
        doc_btn_frame.pack(side="bottom", pady=(6, 6))

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
            fg_color=CLR_DISABLED_BG, hover_color=CLR_DISABLED_BG,
            text_color="white", text_color_disabled=CLR_DISABLED_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
        )
        self.document_execute_btn.pack(side="left")

        # ── 設定フレーム（ボタンの上に固定） ──
        settings_frame = ctk.CTkFrame(
            self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
            border_width=1, border_color=CLR_BORDER, corner_radius=6
        )
        settings_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 4))

        # 行1: 挿入文字 + 開始番号
        row1 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6, 3))

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

        # 行2.5: フォント選択 + サイズ選択
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
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            font_row_doc, text="サイズ:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=CLR_DARK_TEXT
        ).pack(side="left", padx=(0, 6))

        self.doc_font_size_var = ctk.StringVar(value="20")
        ctk.CTkSegmentedButton(
            font_row_doc,
            values=["20", "18", "16", "14", "12"],
            variable=self.doc_font_size_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        ).pack(side="left")

        # 行3: ファイル名変更オプション
        row3 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(0, 3))

        self.rename_file_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row3, text="ファイル名の先頭に資料番号を追加する（例: 【資料１】ファイル名.pdf）",
            variable=self.rename_file_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_DOC_PRIMARY
        ).pack(side="left")

        # 行4: A3縦ページ左綴じ対応オプション
        row4 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row4.pack(fill="x", padx=8, pady=(0, 3))

        self.a3_compat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row4, text="A3縦・A4横ページを左綴じ対応位置（右下）に挿入",
            variable=self.a3_compat_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_DOC_PRIMARY
        ).pack(side="left")

        # 行5: 全ページ挿入オプション
        row5 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row5.pack(fill="x", padx=8, pady=(0, 5))

        self.insert_all_pages_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row5, text="全ページに挿入（オフ: 表紙のみ）",
            variable=self.insert_all_pages_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=CLR_DOC_PRIMARY
        ).pack(side="left")

        # ── ファイルリスト（残りのスペースを占有） ──
        self.document_draggable_list = DraggableFileList(
            self.document_number_tab,
            height=200,
            label_text="📋 資料NO挿入対象ファイルリスト（ドラッグで並び替え可能）"
        )
        self.document_draggable_list.pack(fill="both", expand=True, padx=15, pady=(0, 4))

        self.document_draggable_list.on_selection_change = self._on_document_selection_change
        self.document_draggable_list.on_order_change = self._on_document_order_change

        self.document_list_msg = ctk.CTkLabel(
            self.document_draggable_list,
            text="📋 PDFファイルをここにドラッグ&ドロップしてください\n\n・連番で資料NO（資料1, 資料2...）を自動挿入\n・ドラッグで順序変更、↑↓ボタンでも調整可能",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            justify="left"
        )
        self.document_list_msg.pack(fill="both", expand=True, padx=20, pady=20)

    def _make_digits_only(self, entry: ctk.CTkEntry) -> None:
        """Entryを数字のみ入力可能にする（空文字は許可、それ以外の非数字は拒否）"""
        def _validate(proposed: str) -> bool:
            return proposed == "" or proposed.isdigit()
        vcmd = (entry.register(_validate), "%P")
        entry.configure(validate="key", validatecommand=vcmd)

    def _set_exec_btn_enabled(self, btn: ctk.CTkButton, enabled: bool,
                               active_fg: str, active_hover: str) -> None:
        """実行ボタンの有効/無効を切り替える。

        CTkButtonはdisabled時にfg_colorを変えないため、有効時とほぼ同じ見た目になり
        「押せそう」に見えてしまう。無効時は明示的にグレー系配色へ切り替える。
        """
        if enabled:
            btn.configure(state="normal", fg_color=active_fg, hover_color=active_hover)
        else:
            btn.configure(state="disabled", fg_color=CLR_DISABLED_BG, hover_color=CLR_DISABLED_BG)

    def _init_tooltip_manager(self) -> None:
        """ツールチップの一元管理を初期化し、常駐の監視ループを開始する。

        個々のウィジェットごとにafter()タイマーを持たせる方式は、複合ウィジェット
        （CTkSwitch/CTkButton等）で<Leave>が発火しない場合に取りこぼす恐れがある。
        代わりに単一の監視ループ（UpdateBannerの_pollと同じ方式）でポインタ位置を
        定期的に確認する。

        `fill="x", expand=True` の幅広ラベル（出力先パス等）は表示文字列より
        ウィジェット自体の当たり判定がはるかに広いため、ウィジェットの外に
        出たかどうかだけでは同じ行の余白にいる間ずっと消えない。
        そのため、表示開始位置からのポインタ移動量と経過時間でも閉じる。

        表示のたびにToplevelを作り直す（destroy）と、Windows上ではウィンドウを
        破棄してもその領域の再描画が行われず、見た目上ツールチップが消えない
        ことがある（overrideredirectウィンドウの既知の再描画不具合）。
        そのため単一のToplevelを使い回し、withdraw/deiconifyで表示を切り替える。
        """
        self._tooltip_widget = None
        self._tooltip_origin = (0, 0)
        self._tooltip_shown_at = 0.0

        self._tooltip_win = ctk.CTkToplevel(self.root)
        self._tooltip_win.overrideredirect(True)
        self._tooltip_win.attributes("-topmost", True)
        self._tooltip_label = ctk.CTkLabel(
            self._tooltip_win, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=("#2D3748", "#2D3748"), text_color="white",
            corner_radius=4, padx=8, pady=4
        )
        self._tooltip_label.pack()
        self._tooltip_win.withdraw()

        self._tooltip_watchdog()

    def _tooltip_watchdog(self) -> None:
        if self._tooltip_widget is not None:
            should_hide = True
            try:
                if self._tooltip_widget.winfo_exists():
                    x, y = self._tooltip_widget.winfo_pointerxy()
                    wx, wy = self._tooltip_widget.winfo_rootx(), self._tooltip_widget.winfo_rooty()
                    ww, wh = self._tooltip_widget.winfo_width(), self._tooltip_widget.winfo_height()
                    inside = (wx <= x <= wx + ww and wy <= y <= wy + wh)
                    ox, oy = self._tooltip_origin
                    moved = ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 > 20
                    timed_out = (time.time() - self._tooltip_shown_at) > 4.0
                    should_hide = (not inside) or moved or timed_out
            except Exception:
                should_hide = True
            if should_hide:
                self._hide_tooltip()
        try:
            self.root.after(150, self._tooltip_watchdog)
        except Exception:
            pass

    def _show_tooltip(self, widget, text_getter) -> None:
        text = text_getter() if callable(text_getter) else text_getter
        if not text:
            self._hide_tooltip()
            return
        self._tooltip_label.configure(text=text)
        x = widget.winfo_rootx() + 12
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        self._tooltip_win.geometry(f"+{x}+{y}")
        self._tooltip_win.deiconify()
        self._tooltip_win.lift()
        self._tooltip_widget = widget
        self._tooltip_origin = widget.winfo_pointerxy()
        self._tooltip_shown_at = time.time()

    def _hide_tooltip(self, widget=None) -> None:
        if widget is not None and self._tooltip_widget is not widget:
            return
        self._tooltip_win.withdraw()
        self._tooltip_widget = None

    def _attach_tooltip(self, widget, text_getter) -> None:
        """ウィジェットにホバーツールチップを付与する。

        text_getter: 呼び出し時に表示文字列を返すcallable、または固定文字列。
        """
        widget.bind("<Enter>", lambda e, w=widget, tg=text_getter: self._show_tooltip(w, tg), add="+")
        widget.bind("<Leave>", lambda e, w=widget: self._hide_tooltip(w), add="+")
        widget.bind("<Button-1>", lambda e, w=widget: self._hide_tooltip(w), add="+")

    def _send_files_to_document_tab(self, paths: List[str]) -> None:
        """処理結果を資料NO挿入タブへ送る"""
        existing = [p for p in paths if Path(p).exists()]
        if not existing:
            return
        self._add_document_number_files(existing)
        self._switch_tab("資料NO挿入")

    def _send_files_to_combination_tab(self, paths: List[str]) -> None:
        """処理結果をPDF結合タブへ送る"""
        existing = [p for p in paths if Path(p).exists()]
        if not existing:
            return
        self._add_combination_files(existing)
        self._switch_tab("PDF結合")

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

    # ════════════════════════════════════════════════════════════
    # キーボード操作（Delete / Ctrl+A / Esc）
    # ════════════════════════════════════════════════════════════

    def _active_draggable_list(self) -> Optional[DraggableFileList]:
        """現在表示中のタブに対応するファイルリストを返す（対象外タブはNone）"""
        mapping = {
            "PDF変換": self.conversion_draggable_list,
            "資料NO挿入": self.document_draggable_list,
            "PDF結合": self.combination_draggable_list,
        }
        return mapping.get(getattr(self, "_current_tab", None))

    def _is_text_input_focused(self) -> bool:
        """入力欄にフォーカスがある間はリスト操作用ショートカットを無効化する"""
        widget = self.root.focus_get()
        return isinstance(widget, (tk.Entry, tk.Text))

    def _setup_keyboard_shortcuts(self) -> None:
        """ファイルリスト共通のキーボード操作を設定する"""
        self.root.bind_all("<Delete>", self._on_key_delete_selected)
        self.root.bind_all("<Control-a>", self._on_key_select_all)
        self.root.bind_all("<Control-A>", self._on_key_select_all)
        self.root.bind_all("<Escape>", self._on_key_clear_selection)

    def _on_key_delete_selected(self, event=None) -> None:
        if self._is_text_input_focused():
            return
        tab = getattr(self, "_current_tab", None)
        if tab == "PDF変換":
            self._delete_selected_conversion()
        elif tab == "資料NO挿入":
            self._delete_selected_document()
        elif tab == "PDF結合":
            self._delete_selected_combination()

    def _on_key_select_all(self, event=None):
        if self._is_text_input_focused():
            return None
        lst = self._active_draggable_list()
        if lst:
            lst.select_all()
        return "break"

    def _on_key_clear_selection(self, event=None) -> None:
        lst = self._active_draggable_list()
        if lst:
            lst.clear_selection()
    
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

        self._set_exec_btn_enabled(self.document_execute_btn, False, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
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
        changed_notice = None
        if value == "その他":
            self.custom_prefix_entry.pack(side="left", padx=(0, 20))
            self.numbering_type_var.set("連番")
            self.number_var.set("1")
        else:
            self.custom_prefix_entry.pack_forget()
            if value == "参考":
                self.numbering_type_var.set("番号なし")
                self.number_var.set("0")
                changed_notice = "「参考」選択に伴い、番号方式を「番号なし」に切り替えました"
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
        if changed_notice:
            self.document_status.configure(text=changed_notice)

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
        self._set_exec_btn_enabled(self.document_execute_btn, ready, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
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
            self._set_exec_btn_enabled(self.document_execute_btn, False, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
            self.document_preview_btn.configure(state="disabled")
            self.document_clear_btn.configure(state="disabled")
            self.document_count_label.configure(text="ファイル数: 0")
            self.document_status.configure(text="PDFファイルを追加して連番設定を行ってください")

        self._update_document_output_dir_label()

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

            selected_font = self.doc_font_var.get()

            # 入力値のセキュリティ検証（番号なし以外）
            if number_value and not InputValidator.validate_document_number(number_value, font_name=selected_font):
                error_handler.handle_error(
                    ValueError("無効な資料番号"),
                    ErrorSeverity.WARNING,
                    "入力検証",
                    f"資料番号に無効な文字が含まれています。①やⅠ、㎡などの機種依存文字は「{selected_font}」では文字化けするため使用できません。半角数字や記号（-など）、ひらがな、カタカナ、漢字を使用するか、他のフォントを選択してください。"
                )
                return

            prefix = self._get_active_prefix()
            if not prefix:
                self.document_status.configure(text="挿入する文字を入力してください")
                return

            # 「その他」選択時はプレフィックス文字列を検証
            if self.prefix_var.get() == "その他":
                if not InputValidator.validate_prefix_text(prefix, font_name=selected_font):
                    error_handler.handle_error(
                        ValueError("無効なプレフィックス"),
                        ErrorSeverity.WARNING,
                        "入力検証",
                        f"入力した文字に使用できない文字が含まれています。記号（< > \" ' & ; ( ) {{ }}）や①、Ⅰ、㎡などの機種依存文字は「{selected_font}」では文字化けするため使用できません。10文字以内で入力するか、他のフォントを選択してください。"
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
            all_pages_str = "全ページ" if self.insert_all_pages_var.get() else "表紙（1ページ目）のみ"
            out_dir_disp = self.document_output_dir or "（元ファイルと同じフォルダ）"
            result = confirm_with_skip(
                self.root, "挿入の確認",
                f"以下の内容で挿入を実行しますか？\n\n"
                f"• 対象ファイル数: {len(self.document_number_files)}個\n"
                f"• 挿入文字: {prefix}\n"
                f"• 番号方式: {numbering_type}\n"
                f"• パターン: {preview}\n"
                f"• 挿入ページ: {all_pages_str}\n"
                f"• 出力先: {out_dir_disp}\n\n"
                f"元ファイルはそのまま残ります。",
                skip_getter=lambda: self.skip_confirm_document_number,
                skip_setter=lambda v: setattr(self, "skip_confirm_document_number", v)
            )

            if not result:
                return

            # UIを無効化
            self._set_exec_btn_enabled(self.document_execute_btn, False, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
            self.document_status.configure(text="資料NO挿入処理中...")
            self.document_progress.set(0)

            # 別スレッドで処理実行
            rename_file = self.rename_file_var.get()
            a3_compat = self.a3_compat_var.get()
            insert_all_pages = self.insert_all_pages_var.get()
            selected_font = self.doc_font_var.get()
            doc_font_size = int(self.doc_font_size_var.get())
            thread = threading.Thread(target=self._run_sequential_number_insertion, args=(prefix, numbering_type, number_value, rename_file, a3_compat, selected_font, insert_all_pages, doc_font_size))
            thread.daemon = True
            thread.start()

        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorSeverity.CRITICAL,
                "資料NO挿入開始",
                "資料NO挿入処理の開始中にエラーが発生しました。"
            )

    def _run_sequential_number_insertion(self, prefix: str, numbering_type: str, number_value: str, rename_file: bool = False, a3_portrait_compat: bool = False, selected_font: str = "メイリオ", insert_all_pages: bool = False, doc_font_size: int = 20) -> None:
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
                    insert_all_pages=insert_all_pages,
                    doc_font_size=doc_font_size,
                    output_dir=self.document_output_dir,
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
                    output_dir=self.document_output_dir,
                    numbering_type=internal_type,
                    start_number=start_number,
                    prefix_number=prefix_number,
                    document_prefix=prefix,
                    rename_file=rename_file,
                    a3_portrait_compat=a3_portrait_compat,
                    insert_all_pages=insert_all_pages,
                    doc_font_size=doc_font_size,
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

        # 各ファイルの処理結果をリストに反映（リストは自動クリアしない）
        if result.success or result.failed_files:
            failed_paths = {p for p, _ in result.failed_files}
            for fp in self.document_number_files:
                self.document_draggable_list.set_status(
                    fp, "failed" if fp in failed_paths else "success"
                )

        if result.success:
            self.document_status.configure(
                text=f"資料NO挿入完了: {result.total_pages}ページ ({len(result.processed_files)}ファイル)"
            )

            processed = result.processed_files[:]
            folder = str(Path(processed[0]).parent) if processed else None

            if folder and self.auto_open_output_folder_var.get():
                self._open_folder(folder)

            buttons = []
            if folder:
                buttons.append(("📂 フォルダを開く", lambda f=folder: self._open_folder(f)))
            buttons.append(("→ 結合タブへ送る",
                             lambda p=processed: self._send_files_to_combination_tab(p)))

            self.document_banner.show(
                f"資料NO挿入が完了しました（{len(result.processed_files)}個 / {result.total_pages}ページ）",
                success=(len(result.failed_files) == 0), buttons=buttons
            )
        else:
            message = f"資料NO挿入に失敗しました。\n\nエラー: {result.error_message}"
            self.document_status.configure(text=f"資料NO挿入失敗: {result.error_message}")
            messagebox.showerror("資料NO挿入失敗", message)

        if result.failed_files:
            FailureDetailDialog(self.root, "資料NO挿入失敗の詳細", result.failed_files)

        # UI有効化（リストは保持し、失敗ファイルの再確認・再実行に備える）
        self._set_exec_btn_enabled(self.document_execute_btn, True, CLR_DOC_PRIMARY, CLR_DOC_HOVER)

    def _reset_document_number_ui(self) -> None:
        """資料NO挿入UI リセット"""
        self._set_exec_btn_enabled(self.document_execute_btn, True, CLR_DOC_PRIMARY, CLR_DOC_HOVER)
        self.document_progress.set(0)
        self.document_status.configure(text="エラーが発生しました")
    
    def _update_conversion_display(self) -> None:
        """変換タブ表示更新"""
        current_files = self.conversion_draggable_list.get_files()
        self.conversion_files = current_files
        self.conversion_count_label.configure(text=f"ファイル数: {len(current_files)}")

        if current_files:
            self.initial_message_label.pack_forget()
            self._set_exec_btn_enabled(self.conversion_convert_btn, True, CLR_CONV_PRIMARY, CLR_CONV_HOVER)
            if hasattr(self, 'conversion_clear_btn'):
                self.conversion_clear_btn.configure(state="normal")
            self.conversion_status.configure(
                text=f"{len(current_files)}個のファイルが追加されました"
            )
        else:
            self.initial_message_label.pack(fill="both", expand=True, padx=20, pady=20)
            self._set_exec_btn_enabled(self.conversion_convert_btn, False, CLR_CONV_PRIMARY, CLR_CONV_HOVER)
            if hasattr(self, 'conversion_clear_btn'):
                self.conversion_clear_btn.configure(state="disabled")
            if hasattr(self, 'conversion_delete_btn'):
                self.conversion_delete_btn.configure(state="disabled")
            self.conversion_status.configure(text="変換するファイルを追加してください")

        self._update_conversion_output_dir_label()

    def _update_combination_display(self) -> None:
        """結合タブ表示更新"""
        # ドラッグリストと旧式リストを同期
        current_files = self.combination_draggable_list.get_files()
        self.combination_files = current_files

        if current_files:
            # メッセージを非表示にして、ファイル数を更新
            self.combination_list_msg.pack_forget()
            self._set_exec_btn_enabled(self.combination_combine_btn, True, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
            if hasattr(self, 'combination_clear_btn'):
                self.combination_clear_btn.configure(state="normal")
            self.combination_count_label.configure(text=f"ファイル数: {len(current_files)}")
            self.combination_status.configure(text=f"{len(current_files)}個のPDFファイルが追加されました")
        else:
            # ファイルがない場合は初期メッセージを表示
            self.combination_list_msg.pack(fill="both", expand=True, padx=20, pady=20)
            self._set_exec_btn_enabled(self.combination_combine_btn, False, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
            if hasattr(self, 'combination_clear_btn'):
                self.combination_clear_btn.configure(state="disabled")
            if hasattr(self, 'combination_delete_btn'):
                self.combination_delete_btn.configure(state="disabled")
            self.combination_count_label.configure(text="ファイル数: 0")
            self.combination_status.configure(text="PDFファイルを追加してください")

        self._update_combination_output_dir_label()

    def _clear_combination_files(self) -> None:
        """結合ファイルクリア"""
        # ドラッグリストをクリア
        self.combination_draggable_list.clear_files()

        # 旧式リストもクリア（互換性のため）
        self.combination_files.clear()

        self._update_combination_display()
        
        self._set_exec_btn_enabled(self.combination_combine_btn, False, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
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
    
    # ════════════════════════════════════════════════════════════
    # 出力先フォルダ関連メソッド
    # ════════════════════════════════════════════════════════════

    def _shorten_path(self, path: str, max_len: int = 55) -> str:
        """パス表示用の短縮"""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len - 3):]

    # ── 変換タブ ─────────────────────────────────────────────────
    def _change_conversion_output_dir(self) -> None:
        d = fd.askdirectory(title="変換ファイルの出力先フォルダを選択")
        if d:
            self.conversion_output_dir = d
            self._update_conversion_output_dir_label()

    def _update_conversion_output_dir_label(self) -> None:
        resolved = OutputManager.resolve_output_dir(
            self.conversion_output_dir, self.conversion_files, CONVERSION_OUTPUT_FOLDER_NAME)
        if resolved:
            self.conversion_output_dir_label.configure(
                text=self._shorten_path(resolved), text_color=CLR_DARK_TEXT)
        else:
            self.conversion_output_dir_label.configure(
                text="変換元フォルダ内に「PDF変換済」を作成（既定）", text_color=CLR_GRAY_TEXT)

    # ── 結合タブ ─────────────────────────────────────────────────
    def _change_combination_output_dir(self) -> None:
        d = fd.askdirectory(title="結合ファイルの出力先フォルダを選択")
        if d:
            self.combination_output_dir = d
            self._update_combination_output_dir_label()

    def _update_combination_output_dir_label(self) -> None:
        resolved = OutputManager.resolve_output_dir(
            self.combination_output_dir, self.combination_files, COMBINATION_OUTPUT_FOLDER_NAME)
        if resolved:
            self.combination_output_dir_label.configure(
                text=self._shorten_path(resolved), text_color=CLR_DARK_TEXT)
        else:
            self.combination_output_dir_label.configure(
                text="変換元フォルダ内に「PDF結合済」を作成（既定）", text_color=CLR_GRAY_TEXT)

    # ── 資料NO挿入タブ ────────────────────────────────────────────
    def _change_document_output_dir(self) -> None:
        d = fd.askdirectory(title="資料NO挿入ファイルの出力先フォルダを選択")
        if d:
            self.document_output_dir = d
            self._update_document_output_dir_label()

    def _update_document_output_dir_label(self) -> None:
        resolved = OutputManager.resolve_output_dir(
            self.document_output_dir, self.document_number_files, DOCUMENT_OUTPUT_FOLDER_NAME)
        if resolved:
            self.document_output_dir_label.configure(
                text=self._shorten_path(resolved), text_color=CLR_DARK_TEXT)
        else:
            self.document_output_dir_label.configure(
                text="変換元フォルダ内に「資料NO挿入済」を作成（既定）", text_color=CLR_GRAY_TEXT)

    # ── ページ番号挿入タブ ─────────────────────────────────────────
    def _change_pagenumber_output_dir(self) -> None:
        d = fd.askdirectory(title="ページ番号挿入ファイルの出力先フォルダを選択")
        if d:
            self.pagenumber_output_dir = d
            self._update_pagenumber_output_dir_label()

    def _update_pagenumber_output_dir_label(self) -> None:
        resolved = OutputManager.resolve_output_dir(
            self.pagenumber_output_dir, self.pagenumber_files, PAGENUMBER_OUTPUT_FOLDER_NAME)
        if resolved:
            self.pagenumber_output_dir_label.configure(
                text=self._shorten_path(resolved), text_color=CLR_DARK_TEXT)
        else:
            self.pagenumber_output_dir_label.configure(
                text="元ファイルのフォルダ内に「ページ番号挿入済」を作成（既定）", text_color=CLR_GRAY_TEXT)

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
        self.conversion_retry_failed_btn.configure(state="disabled")
        self._update_conversion_display()
        self.conversion_status.configure(text="ファイルリストをクリアしました")
        logger.info("変換ファイル全クリア")
    
    def _start_conversion(self, files_override: Optional[List[str]] = None) -> None:
        """PDF変換開始"""
        files_to_convert = files_override if files_override is not None else self.conversion_files
        if not files_to_convert:
            return

        # 再実行対象のステータス表示をリセット
        for fp in files_to_convert:
            self.conversion_draggable_list.set_status(fp, None)

        # UIを「実行中」表示に切り替え（キャンセル可能にする）
        self._conversion_cancel_event.clear()
        self._set_conversion_running_ui(True)
        self.conversion_status.configure(text="変換処理中...")
        self.conversion_progress.set(0)

        # 別スレッドで変換実行
        thread = threading.Thread(target=self._run_conversion, args=(list(files_to_convert),))
        thread.daemon = True
        thread.start()

    def _retry_failed_conversion(self) -> None:
        """失敗したファイルのみ再実行"""
        failed_files = self.conversion_draggable_list.get_files_by_status("failed")
        if not failed_files:
            return
        self._start_conversion(files_override=failed_files)

    def _set_conversion_running_ui(self, running: bool) -> None:
        """変換実行中/待機中でボタンの見た目・挙動を切り替える"""
        if running:
            self.conversion_convert_btn.configure(
                text="⏹ キャンセル", command=self._cancel_conversion,
                state="normal", fg_color=CLR_RED_TEXT, hover_color="#9B2C2C"
            )
            self.conversion_retry_failed_btn.configure(state="disabled")
        else:
            self.conversion_convert_btn.configure(text="🔄 PDF変換実行", command=self._start_conversion)
            self._set_exec_btn_enabled(self.conversion_convert_btn, True, CLR_CONV_PRIMARY, CLR_CONV_HOVER)

    def _cancel_conversion(self) -> None:
        """変換処理のキャンセルを要求する（現在処理中のファイル完了後に停止）"""
        self._conversion_cancel_event.set()
        self.conversion_convert_btn.configure(state="disabled")
        self.conversion_status.configure(text="キャンセル中...（現在のファイル完了後に停止します）")

    def _run_conversion(self, files_to_convert: List[str]) -> None:
        """変換実行（別スレッド） - 順次処理でRPCエラーを回避"""
        try:
            total_files = len(files_to_convert)
            results = []
            cancelled = False

            for index, file_path in enumerate(files_to_convert):
                if self._conversion_cancel_event.is_set():
                    cancelled = True
                    break

                # 進捗更新
                progress = (index + 0.5) / total_files  # 処理開始時の進捗
                status_text = f"変換中: {index + 1}/{total_files} - {Path(file_path).name}"
                self.root.after(0, lambda p=progress, s=status_text: self._update_conversion_progress(p, s))

                # 単一ファイル変換（順次処理）
                split_sheets = self.split_excel_sheets_var.get()
                result = self.pdf_converter._convert_single_file(file_path, split_sheets, self.conversion_output_dir)
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
            self.root.after(0, lambda: self._on_conversion_complete(results, cancelled))

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
    

    def _on_conversion_complete(self, results, cancelled: bool = False) -> None:
        """変換完了処理"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # 各行に成功/失敗ステータスを表示（リストは自動クリアしない。未処理分は未表示のまま）
        for r in results:
            self.conversion_draggable_list.set_status(
                r.source_path, "success" if r.success else "failed"
            )

        if cancelled:
            self.conversion_status.configure(
                text=f"キャンセルしました（処理済み {len(results)}件: 成功 {len(successful)}件 / 失敗 {len(failed)}件）"
            )
            self.conversion_banner.show(
                f"変換をキャンセルしました（処理済み {len(results)}件: 成功 {len(successful)}件 / 失敗 {len(failed)}件）",
                success=(len(failed) == 0), buttons=[]
            )
            self.conversion_retry_failed_btn.configure(state="normal" if failed else "disabled")
            self._set_conversion_running_ui(False)
            return

        self.conversion_progress.set(1.0)

        if successful:
            self.conversion_status.configure(text=f"変換完了: 成功 {len(successful)}個, 失敗 {len(failed)}個")

            all_successful_paths = [path for r in successful for path in r.target_paths]
            folder = str(Path(all_successful_paths[0]).parent) if all_successful_paths else None

            if folder and self.auto_open_output_folder_var.get():
                self._open_folder(folder)

            buttons = []
            if folder:
                buttons.append(("📂 フォルダを開く", lambda f=folder: self._open_folder(f)))
            buttons.append(("→ 資料NO挿入タブへ送る",
                             lambda p=all_successful_paths: self._send_files_to_document_tab(p)))
            buttons.append(("→ 結合タブへ送る",
                             lambda p=all_successful_paths: self._send_files_to_combination_tab(p)))

            self.conversion_banner.show(
                f"変換が完了しました（成功 {len(successful)}件 / 失敗 {len(failed)}件）",
                success=(len(failed) == 0), buttons=buttons
            )

        else:
            message = f"変換に失敗しました。\n\n失敗: {len(failed)}件"
            self.conversion_status.configure(text=f"変換失敗: {len(failed)}個のファイルで問題が発生")
            messagebox.showerror("変換失敗", message)

        if failed:
            self.conversion_retry_failed_btn.configure(state="normal")
            FailureDetailDialog(
                self.root, "変換失敗の詳細",
                [(r.source_path, r.error_message) for r in failed]
            )
        else:
            self.conversion_retry_failed_btn.configure(state="disabled")

        # UI有効化（リストは保持し、内容変更・設定変更後の再実行に備える）
        self._set_conversion_running_ui(False)

    def _start_combination(self) -> None:
        """PDF結合開始"""
        if not self.combination_files:
            return

        add_blank_page = self.add_blank_page_var.get()
        add_page_numbers = self.add_page_number_var.get()

        try:
            start_page = int(self.start_page_var.get())
            start_number = int(self.start_number_var.get())
        except ValueError:
            messagebox.showwarning("入力エラー", "開始ページと開始番号には数字を入力してください。")
            return

        # 出力先フォルダが未設定の場合は最初のファイルの親フォルダを使用
        out_dir = self.combination_output_dir or str(Path(self.combination_files[0]).parent)

        # タイムスタンプ付きファイル名を自動生成
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"結合_{timestamp}.pdf"
        output_path = OutputManager.get_unique_output_path(out_dir, filename)

        # UIを無効化
        self._set_exec_btn_enabled(self.combination_combine_btn, False, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
        self.combination_status.configure(text="結合処理中...")
        self.combination_progress.set(0)

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

        # 各ファイルの処理結果をリストに反映（リストは自動クリアしない）
        if result.success or result.failed_files:
            failed_paths = {p for p, _ in result.failed_files}
            for fp in self.combination_files:
                self.combination_draggable_list.set_status(
                    fp, "failed" if fp in failed_paths else "success"
                )

        if result.success:
            self.combination_status.configure(
                text=f"結合完了: {result.total_pages}ページ ({len(result.processed_files)}ファイル)"
            )

            folder = str(Path(result.output_path).parent)
            if self.auto_open_output_folder_var.get():
                self._open_folder(folder)

            self.combination_banner.show(
                f"PDF結合が完了しました（{Path(result.output_path).name} / {result.total_pages}ページ）",
                success=(len(result.failed_files) == 0),
                buttons=[("📂 フォルダを開く", lambda f=folder: self._open_folder(f))]
            )
        else:
            message = f"結合に失敗しました。\n\nエラー: {result.error_message}"
            self.combination_status.configure(text=f"結合失敗: {result.error_message}")
            messagebox.showerror("結合失敗", message)

        if result.failed_files:
            FailureDetailDialog(self.root, "PDF結合失敗の詳細", result.failed_files)

        # UI有効化（リストは保持し、設定変更後の再実行に備える）
        self._set_exec_btn_enabled(self.combination_combine_btn, True, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
    
    def _reset_conversion_ui(self) -> None:
        """変換UI リセット"""
        self._set_conversion_running_ui(False)
        self.conversion_progress.set(0)
        self.conversion_status.configure(text="エラーが発生しました")
    
    def _reset_combination_ui(self) -> None:
        """結合UI リセット"""
        self._set_exec_btn_enabled(self.combination_combine_btn, True, CLR_COMB_PRIMARY, CLR_COMB_HOVER)
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
            self._save_user_settings()
        except Exception as e:
            logger.warning(f"設定の保存に失敗しました: {e}")

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

        self.pagenumber_banner = CompletionBanner(self.pagenumber_tab, CLR_PN_PRIMARY, CLR_PN_HOVER)
        self.pagenumber_banner.pack(fill="x", padx=15, pady=(0, 4))

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

        # ── 出力先フォルダ行 ──
        pn_out_frame = ctk.CTkFrame(self.pagenumber_tab, fg_color=CLR_TOOLBAR_BG,
                                    border_width=1, border_color=CLR_BORDER, corner_radius=6)
        pn_out_frame.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkLabel(pn_out_frame, text="出力先:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13)).pack(side="left", padx=(8, 4), pady=5)
        ctk.CTkButton(
            pn_out_frame, text="📂 変更", command=self._change_pagenumber_output_dir,
            height=26, width=80, fg_color=CLR_PN_PRIMARY, hover_color=CLR_PN_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        ).pack(side="right", padx=(4, 8), pady=5)
        self.pagenumber_output_dir_label = ctk.CTkLabel(
            pn_out_frame, text="（元ファイルと同じフォルダ）",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT, anchor="w"
        )
        self.pagenumber_output_dir_label.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self._attach_tooltip(self.pagenumber_output_dir_label,
            lambda: OutputManager.resolve_output_dir(
                self.pagenumber_output_dir, self.pagenumber_files, PAGENUMBER_OUTPUT_FOLDER_NAME))

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
        self._attach_tooltip(
            self.pn_file_label,
            lambda: self.pagenumber_files[0] if self.pagenumber_files else ""
        )
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
        pn_start_page_entry = ctk.CTkEntry(opt_row, textvariable=self.pn_start_page_var, width=52,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        pn_start_page_entry.pack(side="left")
        self._make_digits_only(pn_start_page_entry)

        ctk.CTkLabel(opt_row, text="ページ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(4, 24))

        ctk.CTkLabel(opt_row, text="開始番号:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        ).pack(side="left", padx=(0, 4))

        self.pn_start_number_var = ctk.StringVar(value="1")
        pn_start_number_entry = ctk.CTkEntry(opt_row, textvariable=self.pn_start_number_var, width=52,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        pn_start_number_entry.pack(side="left")
        self._make_digits_only(pn_start_number_entry)

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
            fg_color=CLR_DISABLED_BG, hover_color=CLR_DISABLED_BG,
            text_color="white", text_color_disabled=CLR_DISABLED_TEXT,
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
            if len(pdf_files) > 1:
                self.pn_status.configure(
                    text=f"このタブは1ファイルのみ対応です。先頭の「{Path(pdf_files[0]).name}」を使用しました"
                )

    def _set_pagenumber_file(self, path: str) -> None:
        self.pagenumber_files = [path]
        name = Path(path).name
        display = name if len(name) <= 40 else name[:37] + "..."
        self.pn_file_label.configure(text=f"📄  {display}")
        self.pn_drop_label.pack_forget()
        self.pn_file_frame.pack(fill="x", padx=12, pady=12)
        self.pn_clear_btn.configure(state="normal")
        self._set_exec_btn_enabled(self.pn_execute_btn, True, CLR_PN_PRIMARY, CLR_PN_HOVER)
        self.pn_preview_btn.configure(state="normal")
        self.pn_status.configure(text=f"選択済み: {name}")
        self._update_pagenumber_output_dir_label()

    def _clear_pagenumber_file(self) -> None:
        self.pagenumber_files = []
        self.pn_file_frame.pack_forget()
        self.pn_drop_label.pack(expand=True)
        self.pn_clear_btn.configure(state="disabled")
        self._set_exec_btn_enabled(self.pn_execute_btn, False, CLR_PN_PRIMARY, CLR_PN_HOVER)
        self.pn_preview_btn.configure(state="disabled")
        self.pn_status.configure(text="PDFファイルを選択してください")
        self.pn_progress.set(0)
        self._update_pagenumber_output_dir_label()

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
        out_dir_disp = self.pagenumber_output_dir or str(Path(pdf_path).parent)
        confirmed = confirm_with_skip(
            self.root, "ページ番号挿入の確認",
            f"以下の内容でページ番号を挿入しますか？\n\n"
            f"• 対象ファイル: {Path(pdf_path).name}\n"
            f"• 開始ページ: {start_page}ページ目から\n"
            f"• 開始番号: {start_number}\n"
            f"• 出力先: {out_dir_disp}\n\n"
            f"元ファイルはそのまま残ります。",
            skip_getter=lambda: self.skip_confirm_pagenumber,
            skip_setter=lambda v: setattr(self, "skip_confirm_pagenumber", v)
        )
        if not confirmed:
            return

        self._set_exec_btn_enabled(self.pn_execute_btn, False, CLR_PN_PRIMARY, CLR_PN_HOVER)
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

            # 一時ファイルを tempdir に作成（クラウドパス対策）
            fd_tmp, tmp_path = tempfile.mkstemp(suffix=".pdf")
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
                # 出力先ディレクトリを決定（未設定なら元ファイルと同じフォルダ）
                effective_out_dir = self.pagenumber_output_dir or str(pdf_path_obj.parent)
                Path(effective_out_dir).mkdir(parents=True, exist_ok=True)
                output_path = OutputManager.get_unique_output_path(effective_out_dir, pdf_path_obj.name)
                # 一時ファイルを出力先へ移動（元ファイルは上書きしない）
                shutil.move(tmp_path, output_path)
                tmp_path = None
                result.output_path = output_path
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
            self.root.after(0, lambda: self._set_exec_btn_enabled(self.pn_execute_btn, True, CLR_PN_PRIMARY, CLR_PN_HOVER))
            self.root.after(0, lambda: self.pn_preview_btn.configure(
                state="normal" if self.pagenumber_files else "disabled"
            ))

    def _on_pagenumber_complete(self, result) -> None:
        self.pn_progress.set(1.0)
        if result.success:
            self.pn_status.configure(text=f"完了: {result.total_pages}ページ")

            folder = str(Path(result.output_path).parent)
            if self.auto_open_output_folder_var.get():
                self._open_folder(folder)

            self.pagenumber_banner.show(
                f"ページ番号挿入が完了しました（{Path(result.output_path).name} / {result.total_pages}ページ）",
                success=True,
                buttons=[("📂 フォルダを開く", lambda f=folder: self._open_folder(f))]
            )
            self._clear_pagenumber_file()
        else:
            messagebox.showerror("エラー", f"処理に失敗しました。\n\n{result.error_message}")
            self.pn_status.configure(text="エラーが発生しました")
            self._set_exec_btn_enabled(self.pn_execute_btn, True, CLR_PN_PRIMARY, CLR_PN_HOVER)
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

    # ════════════════════════════════════════════════════════════
    # 設定の永続化
    # ════════════════════════════════════════════════════════════

    def _load_user_settings(self) -> None:
        """前回終了時の設定を復元する"""
        s = load_settings()
        self._apply_settings(s)

    def _apply_settings(self, s: dict) -> None:
        """設定辞書の内容をUIへ反映する"""
        self._update_conversion_output_dir_label()
        self._update_document_output_dir_label()
        self._update_combination_output_dir_label()
        self._update_pagenumber_output_dir_label()

        self.split_excel_sheets_var.set(s.get("split_excel_sheets", False))
        self.doc_font_var.set(s.get("doc_font", "メイリオ"))
        self.doc_font_size_var.set(s.get("doc_font_size", "20"))
        self.rename_file_var.set(s.get("rename_file", False))
        self.a3_compat_var.set(s.get("a3_compat", False))
        self.insert_all_pages_var.set(s.get("insert_all_pages", False))
        self.add_blank_page_var.set(s.get("add_blank_page", False))
        self.add_page_number_var.set(s.get("add_page_number", False))
        self.combine_pn_binding_compat_var.set(s.get("combine_pn_binding_compat", False))
        self.pn_font_var.set(s.get("pn_font", "メイリオ"))
        self.pn_binding_compat_var.set(s.get("pn_binding_compat", False))
        self.auto_open_output_folder_var.set(s.get("auto_open_output_folder", True))
        self.skip_confirm_document_number = s.get("skip_confirm_document_number", False)
        self.skip_confirm_pagenumber = s.get("skip_confirm_pagenumber", False)
        self._toggle_page_number_options()

    def _collect_current_settings(self) -> dict:
        """現在のUI状態から設定辞書を作成する"""
        return {
            "split_excel_sheets": self.split_excel_sheets_var.get(),
            "doc_font": self.doc_font_var.get(),
            "doc_font_size": self.doc_font_size_var.get(),
            "rename_file": self.rename_file_var.get(),
            "a3_compat": self.a3_compat_var.get(),
            "insert_all_pages": self.insert_all_pages_var.get(),
            "add_blank_page": self.add_blank_page_var.get(),
            "add_page_number": self.add_page_number_var.get(),
            "combine_pn_binding_compat": self.combine_pn_binding_compat_var.get(),
            "pn_font": self.pn_font_var.get(),
            "pn_binding_compat": self.pn_binding_compat_var.get(),
            "auto_open_output_folder": self.auto_open_output_folder_var.get(),
            "skip_confirm_document_number": self.skip_confirm_document_number,
            "skip_confirm_pagenumber": self.skip_confirm_pagenumber,
        }

    def _save_user_settings(self) -> None:
        """現在の設定を保存する"""
        save_settings(self._collect_current_settings())

    def _reset_settings_to_default(self) -> None:
        """設定をデフォルトに戻す"""
        if not messagebox.askyesno("設定リセット", "すべての設定をデフォルトに戻しますか？\n（ファイルリストは変更されません）"):
            return
        self._apply_settings(DEFAULT_SETTINGS)
        save_settings(DEFAULT_SETTINGS.copy())
        messagebox.showinfo("設定リセット", "設定をデフォルトに戻しました。")

    def _open_help(self) -> None:
        """ヘルプダイアログを開く"""
        HelpDialog(self.root)

    def run(self) -> None:
        """アプリケーション実行"""
        logger.info("統合アプリケーション実行開始")
        self.root.mainloop()