"""
アプリケーション設定ファイル
要件定義書 5.6.保守性に基づく設定の集中管理
"""

import os
from pathlib import Path

# アプリケーション基本設定
APP_NAME = "PDF変換・結合ツール"
APP_VERSION = "1.0.0"
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# ウィンドウ設定（450×700縦長レイアウト）
WINDOW_WIDTH = 570
WINDOW_HEIGHT = 700
WINDOW_MIN_WIDTH = 350
WINDOW_MIN_HEIGHT = 500

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

# ログ設定 (要件定義書 5.2)
LOG_RETENTION_DAYS = 30
LOG_LEVELS = ['INFO', 'WARN', 'ERROR']

# ログファイル保存先
if os.name == 'nt':  # Windows
    LOG_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME / 'logs'
else:  # macOS/Linux
    LOG_DIR = Path.home() / 'Library' / 'Logs' / APP_NAME

# 性能設定 (要件定義書 5.3)
MAX_STARTUP_TIME_SECONDS = 5
MAX_CONVERSION_TIME_SECONDS = 10
MAX_IDLE_MEMORY_MB = 200
MAX_CONCURRENT_FILES = 100

# UI設定
UI_THEME = "System"  # CustomTkinter テーマ
UI_COLOR_THEME = "blue"  # カラーテーマ

# ファイルサイズ制限 (MB)
MAX_FILE_SIZE_MB = 100