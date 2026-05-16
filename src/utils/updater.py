"""
GitHub Releases を使ったアップデートチェック機能
"""

import json
import urllib.request
from typing import Optional

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
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return {
                "tag_name": data.get("tag_name", ""),
                "html_url": data.get("html_url", GITHUB_RELEASES_URL),
            }
    except Exception:
        return None
