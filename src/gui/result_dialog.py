"""
処理結果詳細ダイアログ
失敗ファイルの名前と理由を一覧表示する
"""

from pathlib import Path
from typing import List, Tuple

import customtkinter as ctk

from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT, CLR_RED_TEXT, CLR_DARK_TEXT, CLR_BORDER


class FailureDetailDialog(ctk.CTkToplevel):
    """失敗ファイルの名前と理由を一覧表示するダイアログ"""

    def __init__(self, parent, title: str, failed_files: List[Tuple[str, str]], **kwargs):
        super().__init__(parent, **kwargs)
        self.title(title)
        self.geometry("480x420")
        self.transient(parent)
        self.grab_set()
        self._center(parent)
        self._build(failed_files)

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 420) // 2
        self.geometry(f"480x420+{px}+{py}")

    def _build(self, failed_files: List[Tuple[str, str]]):
        ctk.CTkLabel(
            self, text=f"失敗したファイル: {len(failed_files)}件",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=CLR_RED_TEXT
        ).pack(anchor="w", padx=16, pady=(16, 8))

        list_frame = ctk.CTkScrollableFrame(self, fg_color=("white", "white"))
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        for path, reason in failed_files:
            row = ctk.CTkFrame(list_frame, fg_color="transparent", border_width=1,
                                border_color=CLR_BORDER, corner_radius=6)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=f"✕ {Path(path).name}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=CLR_DARK_TEXT, anchor="w", justify="left"
            ).pack(fill="x", padx=10, pady=(6, 0))
            ctk.CTkLabel(
                row, text=reason,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=CLR_RED_TEXT, anchor="w", justify="left", wraplength=420
            ).pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=self.destroy
        ).pack(pady=(0, 14))
