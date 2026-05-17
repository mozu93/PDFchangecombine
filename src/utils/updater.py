"""
GitHub Releases を使ったアップデートチェック・ダウンロード機能
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from typing import Optional, Callable

from packaging.version import Version

GITHUB_API_URL = "https://api.github.com/repos/mozu93/PDFchangecombine/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/mozu93/PDFchangecombine/releases/latest"
_TIMEOUT = 8


def is_newer_version(current: str, latest: str) -> bool:
    """latest が current より新しいか判定"""
    try:
        return Version(latest.lstrip("v")) > Version(current.lstrip("v"))
    except Exception:
        return False


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
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        assets = data.get("assets", [])
        if not tag or not assets:
            return None
        download_url = assets[0].get("browser_download_url", "")
        if not download_url:
            return None
        return {
            "tag_name": tag,
            "html_url": data.get("html_url", GITHUB_RELEASES_URL),
            "download_url": download_url,
        }
    except Exception:
        return None


def download_new_installer(
    url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Optional[str]:
    """インストーラーを %TEMP% にダウンロードする。失敗時は None を返す"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PDFchangecombine-updater"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
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
    """バッチファイル経由でインストーラーを起動し、アプリを終了する"""
    fd, bat_path = tempfile.mkstemp(
        prefix="PDFchangecombine_updater_", suffix=".bat"
    )
    with os.fdopen(fd, "w", encoding="cp932") as f:
        f.write("@echo off\r\n")
        f.write("timeout /t 3 /nobreak > nul\r\n")
        f.write(f'start "" "{installer_path}"\r\n')
        f.write('del "%~f0"\r\n')

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
