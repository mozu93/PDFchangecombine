"""
処理完了通知バナー
モーダルダイアログではなくタブ内の帯で完了を知らせ、
フォルダを開く・次工程タブへ送るなどのアクションボタンを提供する。
"""

from pathlib import Path
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk

from .theme import FONT_FAMILY, CLR_DARK_TEXT, CLR_GRAY_TEXT


class CompletionBanner(ctk.CTkFrame):
    """タブ内に常駐し、処理完了時のみ表示されるバナー"""

    _BG_SUCCESS = "#F0FFF4"
    _BORDER_SUCCESS = "#38A169"
    _BG_WARN = "#FFFAF0"
    _BORDER_WARN = "#DD6B20"

    _HEIGHT_PLAIN = 44
    _HEIGHT_WITH_DEST = 76

    def __init__(self, parent, accent_color: str, accent_hover: str, **kwargs):
        super().__init__(
            parent, fg_color=self._BG_SUCCESS, border_color=self._BORDER_SUCCESS,
            border_width=1, corner_radius=6, height=0, **kwargs
        )
        self.pack_propagate(False)
        self._accent = accent_color
        self._accent_hover = accent_hover

        # pack()はside="right"側を先に確保した者勝ちのため、閉じるボタン・アクション
        # ボタンを可変長のメッセージ列より先にpackし、常に必要幅を確保する。
        # （逆順だとタブ幅が狭いときにボタン類の幅が0になり、操作不能になる）
        self._close_btn = ctk.CTkButton(
            self, text="✕", width=24, height=24,
            fg_color="transparent", hover_color="#E2E8F0", text_color=CLR_DARK_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self.hide,
        )
        self._close_btn.pack(side="right", padx=(0, 8), pady=6)

        self._btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._btn_frame.pack(side="right", padx=(0, 4), pady=4)

        text_col = ctk.CTkFrame(self, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=6)

        self._msg = ctk.CTkLabel(
            text_col, text="", text_color=CLR_DARK_TEXT, anchor="w", justify="left",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self._msg.pack(anchor="w")

        self._dest_label = ctk.CTkLabel(
            text_col, text="", text_color=CLR_GRAY_TEXT, anchor="w", justify="left",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )

    def show(self, message: str, success: bool = True,
              buttons: Optional[List[Tuple[str, Callable]]] = None,
              output_dir: Optional[str] = None) -> None:
        """バナーを表示する。

        buttons: [(ラベル, コールバック), ...]
        output_dir: 保存先フォルダの絶対パス。指定するとフォルダ名を
            太字強調した「保存先」行をメッセージの下に表示する。
        """
        for w in self._btn_frame.winfo_children():
            w.destroy()

        self.configure(
            fg_color=self._BG_SUCCESS if success else self._BG_WARN,
            border_color=self._BORDER_SUCCESS if success else self._BORDER_WARN,
        )
        self._msg.configure(text=message)

        if output_dir:
            folder_name = Path(output_dir).name or output_dir
            shown_path = self._shorten_path(output_dir)
            self._dest_label.configure(text=f"保存先：「{folder_name}」フォルダ（{shown_path}）")
            self._dest_label.pack(anchor="w")
            self.configure(height=self._HEIGHT_WITH_DEST)
        else:
            self._dest_label.pack_forget()
            self.configure(height=self._HEIGHT_PLAIN)

        for label, cmd in (buttons or []):
            ctk.CTkButton(
                self._btn_frame, text=label, height=28,
                fg_color=self._accent, hover_color=self._accent_hover,
                text_color="white",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=cmd,
            ).pack(side="left", padx=3)

    @staticmethod
    def _shorten_path(path: str, max_len: int = 40) -> str:
        """パス表示用の短縮（末尾を優先して残す）"""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len - 3):]

    def hide(self) -> None:
        self.configure(height=0)
        self._dest_label.pack_forget()
        for w in self._btn_frame.winfo_children():
            w.destroy()
