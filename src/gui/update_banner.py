"""
アップデート通知バナー
新バージョン検出 → アプリ内ダウンロード → インストーラー起動
"""

import sys
import threading
import webbrowser
from typing import Optional

import customtkinter as ctk

from ..config import APP_VERSION
from ..utils.updater import (
    check_latest_version,
    is_newer_version,
    download_new_installer,
    launch_updater,
)


class UpdateBanner(ctk.CTkFrame):
    """アップデート通知 + アプリ内ダウンロード・インストールバナー"""

    _BG      = "#FEF9C3"
    _BORDER  = "#FDE047"
    _TEXT    = "#713F12"
    _BTN_DL  = "#1565C0"
    _BTN_DLH = "#1976D2"
    _BTN_OK  = "#2E7D32"
    _BTN_OKH = "#388E3C"
    _HEIGHT  = 44

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=self._BG,
            border_color=self._BORDER,
            border_width=1,
            corner_radius=0,
            height=0,
            **kwargs,
        )
        self.pack_propagate(False)
        self._download_url: Optional[str] = None
        self._installer_path: Optional[str] = None
        self._build_widgets()
        self.pack(fill="x")
        threading.Thread(target=self._check, daemon=True).start()

    # ── UI構築 ──────────────────────────────────────────────────

    def _build_widgets(self):
        # メッセージ（左寄せ）
        self._msg = ctk.CTkLabel(
            self,
            text="",
            text_color=self._TEXT,
            font=ctk.CTkFont(size=13),
        )
        self._msg.pack(side="left", padx=(14, 8), pady=6)

        # 閉じるボタン（常に右端）
        self._close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=26, height=26,
            fg_color="transparent",
            hover_color=self._BORDER,
            text_color=self._TEXT,
            font=ctk.CTkFont(size=11),
            command=self._dismiss,
        )
        self._close_btn.pack(side="right", padx=10, pady=6)

        # ── 状態ごとのウィジェット（中央エリア） ──

        # [1] ダウンロードボタン
        self._dl_btn = ctk.CTkButton(
            self,
            text="ダウンロード",
            width=120, height=28,
            fg_color=self._BTN_DL,
            hover_color=self._BTN_DLH,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._start_download,
        )

        # [2] プログレス表示フレーム
        self._prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._prog_bar = ctk.CTkProgressBar(
            self._prog_frame, width=150, height=12, progress_color=self._BTN_DL
        )
        self._prog_bar.set(0)
        self._prog_bar.pack(side="left", padx=(0, 6))
        self._prog_label = ctk.CTkLabel(
            self._prog_frame,
            text="0.0 / ? MB",
            text_color=self._TEXT,
            font=ctk.CTkFont(size=11),
        )
        self._prog_label.pack(side="left")

        # [3] インストールボタン
        self._install_btn = ctk.CTkButton(
            self,
            text="今すぐ更新して再起動",
            width=180, height=28,
            fg_color=self._BTN_OK,
            hover_color=self._BTN_OKH,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._install,
        )

    # ── 状態遷移 ────────────────────────────────────────────────

    def _set_state(self, state: str):
        """'found' / 'downloading' / 'ready' のいずれか"""
        for w in (self._dl_btn, self._prog_frame, self._install_btn):
            w.pack_forget()

        if state == "found":
            self._dl_btn.pack(side="left", padx=4, pady=6)
        elif state == "downloading":
            self._prog_frame.pack(side="left", padx=4, pady=6)
        elif state == "ready":
            self._install_btn.pack(side="left", padx=4, pady=6)

    # ── バージョンチェック ───────────────────────────────────────

    def _check(self):
        info = check_latest_version()
        if info is None:
            return
        tag = info.get("tag_name", "")
        if not is_newer_version(APP_VERSION, tag):
            return

        self._download_url = info.get("download_url", "")
        html_url = info.get("html_url", "")

        def show():
            self._msg.configure(
                text=f"新しいバージョン {tag} があります  （現在: v{APP_VERSION}）"
            )
            if self._download_url:
                self._set_state("found")
            else:
                # アセットなし → GitHub を開くボタンに置き換え
                self._dl_btn.configure(
                    text="GitHubで確認",
                    command=lambda: webbrowser.open(html_url),
                )
                self._set_state("found")
            self.configure(height=self._HEIGHT)

        self.after(0, show)

    # ── ダウンロード ─────────────────────────────────────────────

    def _start_download(self):
        self._set_state("downloading")
        threading.Thread(target=self._do_download, daemon=True).start()

    def _do_download(self):
        def on_progress(received: int, total: int):
            mb_r = received / 1048576
            mb_t = total / 1048576 if total > 0 else 0
            frac = received / total if total > 0 else 0
            self.after(0, lambda: self._prog_bar.set(frac))
            label = f"{mb_r:.1f} / {mb_t:.1f} MB" if total > 0 else f"{mb_r:.1f} MB"
            self.after(0, lambda: self._prog_label.configure(text=label))

        path = download_new_installer(self._download_url, on_progress)

        if path:
            self._installer_path = path
            self.after(0, lambda: self._msg.configure(
                text="ダウンロード完了！インストールしてアプリを更新できます。"
            ))
            self.after(0, lambda: self._set_state("ready"))
        else:
            self.after(0, self._on_download_failed)

    def _on_download_failed(self):
        self._msg.configure(text="ダウンロードに失敗しました。後でもう一度お試しください。")
        self._set_state("found")
        self._dl_btn.configure(text="再試行")

    # ── インストール ─────────────────────────────────────────────

    def _install(self):
        if not self._installer_path:
            return
        if getattr(sys, "frozen", False):
            # インストーラーを起動してアプリを終了
            launch_updater(self._installer_path)
        else:
            # 開発環境: インストーラーを直接起動
            import subprocess
            subprocess.Popen([self._installer_path])

    # ── 閉じる ───────────────────────────────────────────────────

    def _dismiss(self):
        self.configure(height=0)
