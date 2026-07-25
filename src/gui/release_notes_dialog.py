"""
バージョンアップ時に表示するリリースノートのポップアップダイアログ
"""

import customtkinter as ctk

from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT


class ReleaseNotesDialog(ctk.CTkToplevel):
    """新しいバージョンで何が変わったかを表示するダイアログ"""

    _WIDTH = 560
    _HEIGHT = 480

    def __init__(self, parent, version: str, content: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.title(f"更新内容（v{version}）")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.resizable(False, False)
        self.transient(parent)
        self._center(parent)
        self._build(version, content)
        self.grab_set()

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self._WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._HEIGHT) // 2
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}+{max(px, 0)}+{max(py, 0)}")

    def _build(self, version: str, content: str):
        ctk.CTkLabel(
            self, text=f"v{version} で更新されました",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
        ).pack(pady=(16, 8))

        textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            wrap="word",
            activate_scrollbars=True,
        )
        textbox.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        textbox.insert("0.0", content)
        textbox.configure(state="disabled")

        ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=self.destroy
        ).pack(pady=(0, 16))
