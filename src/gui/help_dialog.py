"""
ヘルプダイアログ - 使い方とバージョン情報
"""

import webbrowser
import customtkinter as ctk

from ..config import APP_VERSION, APP_NAME
from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT


_MANUAL_TEXT = """\
■ PDF変換タブ
  Word / Excel / PowerPoint / 画像ファイルをPDFに変換します。

  【ファイルの追加】
  ・ファイルやフォルダをウィンドウにドラッグ&ドロップ
  ・「ファイル追加」ボタンからダイアログで選択

  【Excelオプション】
  ・オン: 各シートを個別のPDFとして出力
  ・オフ: 印刷設定に従い1ファイルに出力

  【出力先】
  元ファイルと同じフォルダ内の「変換済」フォルダに保存されます。


■ 資料NO挿入タブ
  PDFのヘッダー右上に資料番号を挿入します。

  【文字選択】
  ・資料 / 参考 から選択

  【番号方式】
  ・連番    : 資料1, 資料2, 資料3 ...
  ・ハイフン連番: 資料1-1, 資料1-2 ...
  ・固定番号  : 全ファイルに同一番号を挿入
  ・番号なし  : 番号なしで文字のみ挿入

  【バックアップ】
  元ファイルは「元ファイル」フォルダに自動バックアップされます。

  【ファイル名への追加（オプション）】
  オンにするとファイル名の先頭に「【資料１】」が付加されます。

  【A3縦・A4横ページを左綴じ対応位置（右下）に挿入】
  A3縦やA4横のPDFをA4縦の左綴じ資料に挟む場合、ページを90°回転して見るため
  通常の右上が綴じ側になってしまいます。このオプションをオンにすると
  A3縦・A4横ページを自動検出し、右下（回転後に右上になる位置）に挿入します。
  資料番号は90°回転した向きで挿入されます。
  ※A3横（Z折り）は対象外です（A3横には別途ページ番号の左綴じ対応を使用）。


■ PDF結合タブ
  複数のPDFを1つに結合します。

  【順序変更】
  リスト内のファイルをドラッグ、または ↑ ↓ ボタンで順序を変更できます。

  【オプション】
  ・奇数ページ末尾に白紙挿入: 両面印刷で次PDFが奇数ページから始まるよう調整
  ・ページ番号挿入: フッター中央にページ番号を追加（開始ページ・開始番号を指定可）


■ ページ番号挿入タブ
  PDFのフッター中央にページ番号を挿入して保存します。

  【手順】
  ・PDFファイルをドラッグ&ドロップまたはボタンで追加
  ・開始ページ: 何ページ目からページ番号を印刷するか
  ・開始番号: ページ番号の開始値（例: 5 → 5, 6, 7 ...）
  ・「ページ番号挿入実行」→ 保存先を指定して実行

  【左綴じ対応オプション】
  A3横（Z折り）: ページ左半分の中央下にページ番号を挿入します。
  A4横・A3縦: 左綴じバインダーで90°回転して読む際に読める向きで
  左端中央にページ番号を挿入します。
  ※通常のA4縦ページは影響を受けません。


■ 共通操作
  ・フォルダをドロップすると内部のファイルを自動検索します。
  ・複数ファイルの同時追加に対応しています。
"""


class HelpDialog(ctk.CTkToplevel):
    """ヘルプダイアログ（使い方 + バージョン情報）"""

    _GITHUB_URL = "https://github.com/mozu93/PDFchangecombine"
    _RELEASES_URL = "https://github.com/mozu93/PDFchangecombine/releases"

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("ヘルプ")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._center(parent)
        self._build()

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 560) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 520) // 2
        self.geometry(f"560x520+{px}+{py}")

    def _build(self):
        tab = ctk.CTkTabview(self, anchor="nw")
        tab.pack(fill="both", expand=True, padx=12, pady=12)

        tab.add("使い方")
        tab.add("バージョン情報")

        self._build_manual_tab(tab.tab("使い方"))
        self._build_version_tab(tab.tab("バージョン情報"))

        close_btn = ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=self.destroy
        )
        close_btn.pack(pady=(0, 12))

    def _build_manual_tab(self, parent):
        textbox = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            wrap="word",
            activate_scrollbars=True,
        )
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", _MANUAL_TEXT)
        textbox.configure(state="disabled")

    def _build_version_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text=APP_NAME,
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
        ).pack(pady=(10, 4))

        ctk.CTkLabel(
            frame,
            text=f"バージョン  {APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        ).pack(pady=(0, 20))

        ctk.CTkLabel(
            frame,
            text="Office文書・画像をPDFに変換し、\n資料番号の挿入・PDF結合をまとめて行えるツールです。",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            justify="center",
        ).pack(pady=(0, 24))

        ctk.CTkButton(
            frame,
            text="GitHub でソースを見る",
            width=200,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=lambda: webbrowser.open(self._GITHUB_URL),
        ).pack(pady=4)

        ctk.CTkButton(
            frame,
            text="リリースページ（最新版を確認）",
            width=200,
            fg_color="transparent",
            border_width=1,
            text_color=CLR_PRIMARY,
            hover_color=("#E8F0FE", "#1E3A5F"),
            command=lambda: webbrowser.open(self._RELEASES_URL),
        ).pack(pady=4)
