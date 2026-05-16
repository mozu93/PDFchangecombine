"""
GUIテーマ定義とヘルパー関数
カラー定数とバッジマッピング
"""

from pathlib import Path

# ── フォント ─────────────────────────────────────────────────
FONT_FAMILY = "Yu Gothic UI"

# ── タブカラー ───────────────────────────────────────────────
TAB_CONVERSION  = ("#2B6CB0", "#1A4A7A")   # (active, hover)  PDF変換  青
TAB_COMBINATION = ("#276749", "#1C4D36")   # PDF結合  緑
TAB_DOCUMENT    = ("#C05621", "#963D15")   # 資料NO   オレンジ
TAB_INACTIVE    = ("#718096", "#4A5568")   # 非選択タブ  グレー

# ── カラー定数 ──────────────────────────────────────────────
CLR_PRIMARY       = "#2B6CB0"   # ヘッダー背景・主要アクション
CLR_ACCENT        = "#3182CE"   # 選択ボーダー・バッジ(Word)
CLR_LIGHT_BG      = "#EBF8FF"   # 選択行背景
CLR_LIGHT_BORDER  = "#BEE3F8"   # タブヘッダー下線・リストヘッダー下線
CLR_SEL_BORDER    = "#90CDF4"   # 選択行ボーダー
CLR_TOOLBAR_BG    = "#F7FAFC"   # ツールバー背景
CLR_BORDER        = "#E2E8F0"   # 通常ボーダー
CLR_RED_LIGHT     = "#FED7D7"   # ×ボタン背景
CLR_RED_TEXT      = "#C53030"   # ×ボタン文字・削除ボタン
CLR_GRAY_TEXT     = "#718096"   # 補助テキスト
CLR_DARK_TEXT     = "#2D3748"   # メインテキスト
CLR_LIST_HEADER   = "#EBF8FF"   # リストヘッダー背景
CLR_WHITE         = "white"

# ── バッジ定義 ───────────────────────────────────────────────
_BADGE_MAP: dict[str, tuple[str, str]] = {
    ".docx": ("Word",  "#3182CE"),
    ".doc":  ("Word",  "#3182CE"),
    ".xlsx": ("Excel", "#38A169"),
    ".xls":  ("Excel", "#38A169"),
    ".pptx": ("PPT",   "#DD6B20"),
    ".ppt":  ("PPT",   "#DD6B20"),
    ".pdf":  ("PDF",   "#E53E3E"),
    ".jpg":  ("画像",  "#805AD5"),
    ".jpeg": ("画像",  "#805AD5"),
    ".png":  ("画像",  "#805AD5"),
    ".bmp":  ("画像",  "#805AD5"),
    ".gif":  ("画像",  "#805AD5"),
    ".tiff": ("画像",  "#805AD5"),
}


def get_file_type_badge(file_path: str) -> tuple[str, str]:
    """拡張子からバッジの (ラベル, 背景色) を返す"""
    ext = Path(file_path).suffix.lower()
    return _BADGE_MAP.get(ext, ("FILE", "#718096"))
