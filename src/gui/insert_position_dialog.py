"""
ページ挿入位置（前／後）を選ばせる小さなダイアログ
"""

from typing import Optional

import customtkinter as ctk

from .theme import FONT_FAMILY, CLR_BORDER, CLR_DARK_TEXT, CLR_PE_PRIMARY, CLR_PE_HOVER


class _InsertPositionDialog(ctk.CTkToplevel):
    def __init__(self, parent, page_number: int):
        super().__init__(parent)
        self.title("挿入位置")
        self.resizable(False, False)
        self.transient(parent)
        self.result: Optional[str] = None
        self._build(page_number)
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(None))
        self.update_idletasks()
        self._center(parent)
        self.grab_set()

    def _center(self, parent):
        w = max(self.winfo_reqwidth(), 320)
        h = self.winfo_reqheight()
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px, 0)}+{max(py, 0)}")

    def _build(self, page_number: int) -> None:
        ctk.CTkLabel(
            self, text=f"{page_number}ページ目のどちらに挿入しますか？",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=CLR_DARK_TEXT
        ).pack(padx=20, pady=(20, 16))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 8))
        ctk.CTkButton(
            btn_row, text="前", width=90,
            fg_color=CLR_PE_PRIMARY, hover_color=CLR_PE_HOVER,
            command=lambda: self._finish("前")
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row, text="後", width=90,
            fg_color=CLR_PE_PRIMARY, hover_color=CLR_PE_HOVER,
            command=lambda: self._finish("後")
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            self, text="キャンセル", width=100,
            fg_color="transparent", text_color=CLR_DARK_TEXT,
            border_width=1, border_color=CLR_BORDER, hover_color=CLR_BORDER,
            command=lambda: self._finish(None)
        ).pack(pady=(0, 18))

    def _finish(self, result: Optional[str]) -> None:
        self.result = result
        self.destroy()


def ask_insert_position(parent, page_number: int) -> Optional[str]:
    """1ページ目基準（1始まり）の page_number に対して「前」「後」の選択を尋ねる。

    戻り値: "前" / "後" / None（キャンセル）
    """
    dialog = _InsertPositionDialog(parent, page_number)
    parent.wait_window(dialog)
    return dialog.result
