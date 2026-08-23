"""
GUIテーマ定義とヘルパー関数
カラー定数とバッジマッピング
"""

from pathlib import Path

# ── フォント ─────────────────────────────────────────────────
FONT_FAMILY = "Yu Gothic UI"

# ── タブカラー ───────────────────────────────────────────────
TAB_CONVERSION  = ("#2B6CB0", "#1A4A7A")   # (active, hover)  PDF変換  青
TAB_COMBINATION = ("#C05621", "#963D15")   # PDF結合  オレンジ
TAB_DOCUMENT    = ("#276749", "#1C4D36")   # 資料NO   緑
TAB_PAGENUMBER  = ("#553C9A", "#3D2B6E")   # ページ番号  紫
TAB_PAGEEDIT    = ("#2C7A7B", "#22595A")   # ページ編集  ティール
TAB_INACTIVE    = ("#718096", "#4A5568")   # 非選択タブ  グレー

# ── タブ別アクセントカラー ─────────────────────────────────────
CLR_CONV_PRIMARY = "#2B6CB0"   # 変換タブ: 青
CLR_CONV_HOVER   = "#1A4A7A"
CLR_COMB_PRIMARY = "#C05621"   # 結合タブ: オレンジ
CLR_COMB_HOVER   = "#963D15"
CLR_DOC_PRIMARY  = "#276749"   # 資料NOタブ: 緑
CLR_DOC_HOVER    = "#1C4D36"
CLR_PN_PRIMARY   = "#553C9A"   # ページ番号タブ: 紫
CLR_PN_HOVER     = "#3D2B6E"
CLR_PE_PRIMARY   = "#2C7A7B"   # ページ編集タブ: ティール
CLR_PE_HOVER     = "#22595A"

# ── カラー定数 ──────────────────────────────────────────────
CLR_PRIMARY       = "#2B6CB0"   # ヘッダー背景・主要アクション（変換タブと同色）
CLR_ACCENT        = "#3182CE"   # 選択ボーダー・バッジ(Word)
CLR_LIGHT_BG      = "#EBF8FF"   # 選択行背景
CLR_LIGHT_BORDER  = "#BEE3F8"   # タブヘッダー下線・リストヘッダー下線
CLR_SEL_BORDER    = "#90CDF4"   # 選択行ボーダー
CLR_TOOLBAR_BG    = "#F7FAFC"   # ツールバー背景
CLR_BORDER        = "#E2E8F0"   # 通常ボーダー
CLR_RED_LIGHT     = "#FED7D7"   # ×ボタン背景
CLR_RED_TEXT      = "#C53030"   # ×ボタン文字・削除ボタン
CLR_GRAY_TEXT     = "#5A6B7F"   # 補助テキスト（#F7FAFC背景でWCAG AA 4.5:1以上を確保）
CLR_DARK_TEXT     = "#2D3748"   # メインテキスト
CLR_LIST_HEADER   = "#EBF8FF"   # リストヘッダー背景
CLR_WHITE         = "white"

# ── 無効状態ボタン配色（実行ボタン等がdisabled時に有効時と見分けがつくように） ──
CLR_DISABLED_BG   = "#CBD5E0"   # 無効ボタン背景（グレー）
CLR_DISABLED_TEXT = "#A0AEC0"   # 無効ボタン文字

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
