"""
GitHub Releases を使ったアップデートチェック・ダウンロード機能
"""

import json
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from typing import Optional, Callable

GITHUB_API_URL = "https://api.github.com/repos/mozu93/PDFchangecombine/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/mozu93/PDFchangecombine/releases/latest"


def is_newer_version(current: str, latest: str) -> bool:
    """latest が current より新しいか判定"""
    def parse(v: str):
        return tuple(int(x) for x in v.lstrip("v").split("."))
    try:
        return parse(latest) > parse(current)
    except Exception:
        return False


def _make_ssl_context() -> ssl.SSLContext:
    """PyInstaller 環境でも動く SSL コンテキストを返す"""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # ImportError / FileNotFoundError 等を全て補足
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def check_latest_version() -> Optional[dict]:
    """GitHub API から最新リリース情報を取得。失敗時は None を返す"""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "PDFchangecombine-updater",
            },
        )
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            assets = data.get("assets", [])
            download_url = assets[0]["browser_download_url"] if assets else ""
            return {
                "tag_name": data.get("tag_name", ""),
                "html_url": data.get("html_url", GITHUB_RELEASES_URL),
                "download_url": download_url,
            }
    except Exception:
        return None


def download_new_installer(
    url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Optional[str]:
    """
    インストーラーを %TEMP% にダウンロードする。

    Args:
        url: ダウンロードURL
        progress_callback: (受信バイト数, 合計バイト数) を受け取るコールバック

    Returns:
        ダウンロード先の一時ファイルパス。失敗時は None。
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PDFchangecombine-updater"},
        )
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            total = int(resp.headers.get("Content-Length", -1))
            fd, tmp_path = tempfile.mkstemp(
                prefix="PDFchangecombine_new_", suffix=".exe"
            )
            received = 0
            with os.fdopen(fd, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if progress_callback:
                        progress_callback(received, total)
        return tmp_path
    except Exception:
        return None


def launch_updater(installer_path: str) -> None:
    """
    バッチファイル経由でインストーラーを起動し、アプリを終了する。
    アプリの完全終了を待ってからインストーラーを実行する。
    """
    fd, bat_path = tempfile.mkstemp(
        prefix="PDFchangecombine_updater_", suffix=".bat"
    )
    with os.fdopen(fd, "w", encoding="cp932") as f:
        f.write("@echo off\n")
        f.write("timeout /t 3 /nobreak > nul\n")
        f.write(f'start "" "{installer_path}"\n')
        f.write('del "%~f0"\n')

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
