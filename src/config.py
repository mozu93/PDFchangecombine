"""
アプリケーション設定ファイル
要件定義書 5.6.保守性に基づく設定の集中管理
"""

import os
from pathlib import Path

# アプリケーション基本設定
APP_NAME = "PDF変換・結合ツール"
APP_VERSION = "1.22.0"
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# ウィンドウ設定（縦長レイアウト）
# WINDOW_WIDTH: 左サイドバー（タブメニュー、幅130px）分の余白を確保しつつ、
# 画面占有を抑えるためユーザー指定で850pxから15%削減した値。
# 結合タブのツールバー（PDF選択・選択削除・クリア・↑・↓・Ａ↓・
# 資料を差し替え...）は1行に収まることを実機確認済み
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 700
WINDOW_MIN_WIDTH = 500
WINDOW_MIN_HEIGHT = 630

# PAGE_EDITOR_MIN_WIDTH: ページ編集タブはサムネイルを横に並べるため、
# 720pxでは4列しか入らない。タブ選択時にこの幅まで「広げる」（縮めることはしない）。
# 1366x768のノートPCに収まる値にしてある。
PAGE_EDITOR_MIN_WIDTH = 880

# 対応ファイル形式 (要件定義書 F-102)
SUPPORTED_OFFICE_EXTENSIONS = {
    'word': ['.docx', '.doc'],
    'excel': ['.xlsx', '.xls'], 
    'powerpoint': ['.pptx', '.ppt']
}

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']

# PDFファイル対応（コピー処理）
SUPPORTED_PDF_EXTENSIONS = ['.pdf']

ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_OFFICE_EXTENSIONS['word'] + 
    SUPPORTED_OFFICE_EXTENSIONS['excel'] + 
    SUPPORTED_OFFICE_EXTENSIONS['powerpoint'] + 
    SUPPORTED_IMAGE_EXTENSIONS +
    SUPPORTED_PDF_EXTENSIONS
)

# 出力設定 (要件定義書 F-104)
OUTPUT_FOLDER_NAME = "変換済"

# 機能別の既定出力フォルダ名（変換元ファイルの親フォルダ配下に作成）
CONVERSION_OUTPUT_FOLDER_NAME = "PDF変換済"
DOCUMENT_OUTPUT_FOLDER_NAME = "資料NO挿入済"
COMBINATION_OUTPUT_FOLDER_NAME = "PDF結合済"
PAGENUMBER_OUTPUT_FOLDER_NAME = "ページ番号挿入済"
PAGE_EDITOR_OUTPUT_FOLDER_NAME = "ページ編集済"

# ログ設定 (要件定義書 5.2)
LOG_RETENTION_DAYS = 30

# ログファイル保存先
LOG_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME / 'logs'

# 性能設定 (要件定義書 5.3)
MAX_STARTUP_TIME_SECONDS = 5
MAX_CONVERSION_TIME_SECONDS = 10
MAX_CONCURRENT_FILES = 100

# UI設定
# 現状のテーマ定数はライト固定色のため、"System"でOSがダークモードの場合に
# 配色が破綻する（外枠のみ暗色化し、内部は白基調のまま）。当面はLightに固定する。
UI_THEME = "Light"  # CustomTkinter テーマ
UI_COLOR_THEME = "blue"  # カラーテーマ

# ファイルサイズ制限 (MB)
MAX_FILE_SIZE_MB = 100
