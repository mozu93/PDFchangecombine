"""
ユーザー設定の永続化
出力先フォルダ・フォント・各種スイッチなど、次回起動時にも引き継ぎたい設定を
%APPDATA%/PDF変換・結合ツール/settings.json に保存/復元する。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from ..config import APP_NAME
from .logger import logger

_SETTINGS_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME

SETTINGS_PATH = _SETTINGS_DIR / 'settings.json'

# 各設定のデフォルト値（「デフォルトに戻す」で使用）
DEFAULT_SETTINGS: Dict[str, Any] = {
    "split_excel_sheets": False,
    "doc_font": "メイリオ",
    "doc_font_size": "20",
    "rename_file": False,
    "a3_compat": False,
    "insert_all_pages": False,
    "add_blank_page": False,
    "add_page_number": False,
    "combine_pn_binding_compat": False,
    "pn_font": "メイリオ",
    "pn_binding_compat": False,
    "auto_open_output_folder": True,
    "skip_confirm_document_number": False,
    "skip_confirm_pagenumber": False,
}


def load_settings() -> Dict[str, Any]:
    """保存済み設定を読み込む。存在しない/壊れている場合はデフォルトを返す"""
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        return merged
    except Exception as e:
        logger.warning(f"設定ファイルの読み込みに失敗しました: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """設定をJSONファイルに保存する"""
    try:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"設定ファイルの保存に失敗しました: {e}")
