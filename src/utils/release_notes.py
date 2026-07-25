"""
バージョンアップ時にリリースノートをポップアップ表示するための判定・検索ロジック
"""

from pathlib import Path
from typing import Optional, Union


def should_show_release_notes(current_version: str, last_seen_version: str) -> bool:
    """リリースノートのポップアップを表示すべきか判定する。

    last_seen_versionが空（初回インストール等）の場合は、比較対象がないため表示しない。
    現在のバージョンと異なる場合のみ表示する。
    """
    return bool(last_seen_version) and last_seen_version != current_version


def find_release_notes_path(project_root: Union[str, Path], version: str) -> Optional[Path]:
    """指定バージョンのリリースノートファイル（RELEASE_NOTES_v{version}.md）を探す。

    見つからない場合はNoneを返す。
    """
    candidate = Path(project_root) / f"RELEASE_NOTES_v{version}.md"
    return candidate if candidate.is_file() else None
