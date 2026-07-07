"""
「今後表示しない」チェック付き確認ダイアログ
"""

from typing import Callable

import customtkinter as ctk

from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT, CLR_BORDER, CLR_DARK_TEXT


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result_confirmed = False
        self.result_skip = False
        self._skip_var = ctk.BooleanVar(value=False)
        self._build(message)
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(False))
        self.update_idletasks()
        self._center(parent)
        self.grab_set()

    def _center(self, parent):
        w = max(self.winfo_reqwidth(), 380)
        h = self.winfo_reqheight()
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px, 0)}+{max(py, 0)}")

    def _build(self, message: str):
        ctk.CTkLabel(
            self, text=message, font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            justify="left", anchor="w", wraplength=360
        ).pack(padx=20, pady=(20, 12), fill="x")

        ctk.CTkCheckBox(
            self, text="今後この確認を表示しない", variable=self._skip_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        ).pack(padx=20, pady=(0, 16), anchor="w")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 18))
        ctk.CTkButton(
            btn_row, text="キャンセル", width=100,
            fg_color=CLR_BORDER, text_color=CLR_DARK_TEXT, hover_color="#CBD5E0",
            command=lambda: self._finish(False)
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row, text="実行する", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=lambda: self._finish(True)
        ).pack(side="left", padx=6)

    def _finish(self, confirmed: bool):
        self.result_confirmed = confirmed
        self.result_skip = self._skip_var.get()
        self.destroy()


def confirm_with_skip(parent, title: str, message: str,
                       skip_getter: Callable[[], bool],
                       skip_setter: Callable[[bool], None]) -> bool:
    """「今後表示しない」チェック付きの確認ダイアログ。

    skip_getter()がTrueを返す場合はダイアログを表示せずTrueを返す。
    ユーザーが「今後表示しない」にチェックすると skip_setter(True) を呼ぶ。
    """
    if skip_getter():
        return True

    dialog = _ConfirmDialog(parent, title, message)
    parent.wait_window(dialog)

    if dialog.result_skip:
        skip_setter(True)
    return dialog.result_confirmed
