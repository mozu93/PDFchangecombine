"""
アップデート通知バナー
新バージョンが GitHub Releases に存在する場合のみウィンドウ上部に表示する
"""

import threading
import webbrowser
from typing import Optional

import customtkinter as ctk

from ..config import APP_VERSION
from ..utils.updater import check_latest_version, is_newer_version


class UpdateBanner(ctk.CTkFrame):
    """新バージョン検出時のみ表示される通知バナー"""

    _BG     = "#FEF9C3"
    _BORDER = "#FDE047"
    _TEXT   = "#713F12"
    _BTN    = "#1565C0"
    _BTN_H  = "#1976D2"
    _HEIGHT = 40

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=self._BG,
            border_color=self._BORDER,
            border_width=1,
            corner_radius=0,
            height=0,       # 初期は高さ0で非表示
            **kwargs,
        )
        self.pack_propagate(False)
        self._release_url: Optional[str] = None
        self._visible = False
        self._build_widgets()
        # 最上部に pack しておく（高さ0なので見えない）
        self.pack(fill="x")
        # バックグラウンドでバージョンチェック開始
        threading.Thread(target=self._check, daemon=True).start()

    # ── UI構築 ──────────────────────────────────────────────────

    def _build_widgets(self):
        self._msg = ctk.CTkLabel(
            self,
            text="",
            text_color=self._TEXT,
            font=ctk.CTkFont(size=13),
        )
        self._msg.pack(side="left", padx=(14, 8), pady=6)

        self._open_btn = ctk.CTkButton(
            self,
            text="GitHubで確認",
            width=110,
            height=26,
            fg_color=self._BTN,
            hover_color=self._BTN_H,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_release,
        )
        self._open_btn.pack(side="left", padx=4, pady=6)

        self._close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=26,
            height=26,
            fg_color="transparent",
            hover_color=self._BORDER,
            text_color=self._TEXT,
            font=ctk.CTkFont(size=11),
            command=self._dismiss,
        )
        self._close_btn.pack(side="right", padx=10, pady=6)

    # ── バージョンチェック ───────────────────────────────────────

    def _check(self):
        """別スレッドでGitHub APIを呼び出す"""
        info = check_latest_version()
        if info is None:
            return
        tag = info.get("tag_name", "")
        if is_newer_version(APP_VERSION, tag):
            self._release_url = info.get("html_url")
            self.after(0, lambda: self._show(tag))

    # ── 表示 / 非表示 ────────────────────────────────────────────

    def _show(self, tag: str):
        """高さを40pxに変えてバナーを表示（先頭に pack 済みのため位置は変わらない）"""
        self._msg.configure(
            text=f"新しいバージョン {tag} があります  （現在: v{APP_VERSION}）"
        )
        self.configure(height=self._HEIGHT)
        self._visible = True

    def _open_release(self):
        if self._release_url:
            webbrowser.open(self._release_url)

    def _dismiss(self):
        self.configure(height=0)
        self._visible = False
