"""
アップデート通知バナー
新バージョン検出 → アプリ内ダウンロード → インストーラー起動

スレッド設計:
  バックグラウンドスレッドは queue.Queue にコールバックを積む。
  メインスレッドが _poll() (100ms ごと) でキューを消費して UI を更新する。
  tkinter は非スレッドセーフなので、UI 操作はすべてメインスレッドで行う。
"""

import queue
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
        self._ui_queue: queue.Queue = queue.Queue()
        self._build_widgets()
        self.pack(fill="x")
        threading.Thread(target=self._check, daemon=True).start()
        self._poll()

    # ── メインスレッドキューポーリング ───────────────────────────

    def _poll(self):
        """100ms ごとにキューを処理する（すべての UI 更新はここで実行）"""
        try:
            while True:
                cb = self._ui_queue.get_nowait()
                cb()
        except queue.Empty:
            pass
        try:
            self.after(100, self._poll)
        except Exception:
            pass

    # ── UI 構築 ──────────────────────────────────────────────────

    def _build_widgets(self):
        self._msg = ctk.CTkLabel(
            self,
            text="",
            text_color=self._TEXT,
            font=ctk.CTkFont(size=13),
        )
        self._msg.pack(side="left", padx=(14, 8), pady=6)

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

    # ── 状態遷移（メインスレッドのみ） ───────────────────────────

    def _set_state(self, state: str):
        for w in (self._dl_btn, self._prog_frame, self._install_btn):
            w.pack_forget()
        if state == "found":
            self._dl_btn.pack(side="left", padx=4, pady=6)
        elif state == "downloading":
            self._prog_frame.pack(side="left", padx=4, pady=6)
        elif state == "ready":
            self._install_btn.pack(side="left", padx=4, pady=6)

    # ── バージョンチェック（バックグラウンドスレッド） ───────────

    def _check(self):
        """バックグラウンドで実行。UI 操作はキュー経由でのみ行う。"""
        info = check_latest_version()
        if info is None:
            return
        tag = info.get("tag_name", "")
        if not is_newer_version(APP_VERSION, tag):
            return
        download_url = info.get("download_url", "")
        html_url = info.get("html_url", "")
        self._ui_queue.put(
            lambda t=tag, u=download_url, h=html_url: self._show_found(t, u, h)
        )

    def _show_found(self, tag: str, download_url: str, html_url: str):
        """メインスレッドで実行 - バナーを表示する"""
        self._download_url = download_url
        self._msg.configure(
            text=f"新しいバージョン {tag} があります  （現在: v{APP_VERSION}）"
        )
        if download_url:
            self._set_state("found")
        else:
            self._dl_btn.configure(
                text="GitHubで確認",
                command=lambda: webbrowser.open(html_url),
            )
            self._set_state("found")
        self.configure(height=self._HEIGHT)

    # ── ダウンロード ─────────────────────────────────────────────

    def _start_download(self):
        self._set_state("downloading")
        threading.Thread(target=self._do_download, daemon=True).start()

    def _do_download(self):
        def on_progress(received: int, total: int):
            frac = received / total if total > 0 else 0
            mb_r = received / 1048576
            label = (
                f"{mb_r:.1f} / {total / 1048576:.1f} MB"
                if total > 0
                else f"{mb_r:.1f} MB"
            )
            self._ui_queue.put(
                lambda f=frac, l=label: self._update_progress(f, l)
            )

        path = download_new_installer(self._download_url, on_progress)
        if path:
            self._installer_path = path
            self._ui_queue.put(self._show_ready)
        else:
            self._ui_queue.put(self._show_download_failed)

    def _update_progress(self, frac: float, label: str):
        self._prog_bar.set(frac)
        self._prog_label.configure(text=label)

    def _show_ready(self):
        self._msg.configure(text="ダウンロード完了！インストールしてアプリを更新できます。")
        self._set_state("ready")

    def _show_download_failed(self):
        self._msg.configure(text="ダウンロードに失敗しました。後でもう一度お試しください。")
        self._set_state("found")
        self._dl_btn.configure(text="再試行")

    # ── インストール ─────────────────────────────────────────────

    def _install(self):
        if not self._installer_path:
            return
        if getattr(sys, "frozen", False):
            launch_updater(self._installer_path)
        else:
            import subprocess
            subprocess.Popen([self._installer_path])

    # ── 閉じる ───────────────────────────────────────────────────

    def _dismiss(self):
        self.configure(height=0)
