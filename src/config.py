"""
アプリケーション設定ファイル
要件定義書 5.6.保守性に基づく設定の集中管理
"""

import os
from pathlib import Path

# アプリケーション基本設定
APP_NAME = "PDF変換・結合ツール"
APP_VERSION = "1.18.0"
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# ウィンドウ設定（450×700縦長レイアウト）
WINDOW_WIDTH = 570
WINDOW_HEIGHT = 700
WINDOW_MIN_WIDTH = 350
WINDOW_MIN_HEIGHT = 630

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

# 本番配布設定
PRODUCTION_MODE = False  # 本番環境ではTrueに設定
DEBUG_MODE = True        # デバッグログの有効/無効

# セキュリティ設定
ENABLE_SECURITY_VALIDATION = True  # セキュリティ検証の有効/無効
ALLOWED_FILE_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.xlsx', '.xls',
    '.pptx', '.ppt', '.jpg', '.jpeg', '.png',
    '.bmp', '.gif', '.tiff'
}

# パフォーマンス設定
ENABLE_PERFORMANCE_MONITORING = True  # パフォーマンス監視の有効/無効
MAX_PROCESSING_THREADS = 4             # 最大処理スレッド数
MEMORY_WARNING_THRESHOLD_MB = 500      # メモリ警告閾値

# UI設定
SHOW_DETAILED_ERRORS = not PRODUCTION_MODE  # 詳細エラー表示（開発時のみ）
AUTO_BACKUP_ENABLED = True                  # 自動バックアップ機能
BACKUP_FOLDER_NAME = "元ファイル"            # バックアップフォルダ名

# 監視・ログ設定
STRUCTURED_LOGGING = True              # 構造化ログの有効/無効
LOG_PERFORMANCE_METRICS = True         # パフォーマンスメトリクスログ
LOG_USER_ACTIONS = not PRODUCTION_MODE  # ユーザーアクションログ（開発時のみ）
LOG_SECURITY_EVENTS = True            # セキュリティイベントログ

# 運用設定
APP_UPDATE_CHECK_URL = ""             # アップデート確認URL（未使用）
TELEMETRY_ENABLED = False             # テレメトリ送信（プライバシー考慮）
CRASH_REPORT_ENABLED = False          # クラッシュレポート送信

# 開発者設定
if not PRODUCTION_MODE:
    # 開発時の設定上書き
    LOG_RETENTION_DAYS = 7
    MAX_FILE_SIZE_MB = 50
    DEBUG_MODE = True