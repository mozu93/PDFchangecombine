# GUI リデザイン 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** チェックボックスを廃止し、行クリック選択＋ホバー×ボタン＋クリーンブルーテーマでGUIを刷新する

**Architecture:** `src/gui/theme.py`（新規）にカラー定数とバッジヘルパーを切り出し、`draggable_list.py` のリストアイテムを行選択式に全面書き換え、`unified_window.py` でツールバーレイアウト・オプションUI・ヘッダーを更新する。コアロジック（`core/`・`utils/`）は一切変更しない。

**Tech Stack:** Python 3.10+, CustomTkinter (ctk), tkinter

**仕様書:** `docs/superpowers/specs/2026-05-16-gui-redesign-design.md`

---

## ファイル構成

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/gui/theme.py` | **新規作成** | カラー定数・バッジヘルパー関数 |
| `src/gui/draggable_list.py` | **大幅変更** | DraggableListItem・DraggableFileList |
| `src/gui/unified_window.py` | **大幅変更** | 全タブUI・ツールバー・ヘッダー |
| `tests/test_gui_helpers.py` | **新規作成** | theme.py のユニットテスト |

---

## Task 1: theme.py — カラー定数とバッジヘルパー

**Files:**
- Create: `src/gui/theme.py`
- Create: `tests/test_gui_helpers.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_gui_helpers.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gui.theme import get_file_type_badge

def test_word():
    assert get_file_type_badge("report.docx") == ("Word", "#3182CE")
    assert get_file_type_badge("old.doc")    == ("Word", "#3182CE")

def test_excel():
    assert get_file_type_badge("data.xlsx") == ("Excel", "#38A169")
    assert get_file_type_badge("data.xls")  == ("Excel", "#38A169")

def test_ppt():
    assert get_file_type_badge("slides.pptx") == ("PPT", "#DD6B20")
    assert get_file_type_badge("slides.ppt")  == ("PPT", "#DD6B20")

def test_pdf():
    assert get_file_type_badge("doc.pdf") == ("PDF", "#E53E3E")

def test_image():
    assert get_file_type_badge("photo.png")  == ("画像", "#805AD5")
    assert get_file_type_badge("photo.jpg")  == ("画像", "#805AD5")
    assert get_file_type_badge("photo.jpeg") == ("画像", "#805AD5")

def test_unknown():
    assert get_file_type_badge("file.xyz") == ("FILE", "#718096")
    assert get_file_type_badge("file")     == ("FILE", "#718096")
```

- [ ] **Step 2: テストが失敗することを確認**

```
cd C:\Users\taka\Documents\Gemini\0030Business\PDFchangecombine
pytest tests/test_gui_helpers.py -v
```
期待: `ModuleNotFoundError: No module named 'src.gui.theme'`

- [ ] **Step 3: theme.py を実装**

```python
# src/gui/theme.py
from pathlib import Path

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
```

- [ ] **Step 4: テストが通ることを確認**

```
pytest tests/test_gui_helpers.py -v
```
期待: 全テスト PASS

- [ ] **Step 5: コミット**

```
cd C:\Users\taka\Documents\Gemini\0030Business\PDFchangecombine
git add src/gui/theme.py tests/test_gui_helpers.py
git commit -m "feat: add theme.py with color constants and badge helper"
```

---

## Task 2: DraggableListItem — 全面書き換え

**Files:**
- Modify: `src/gui/draggable_list.py`（`DraggableListItem` クラス全体を置き換え）

- [ ] **Step 1: インポートに theme を追加**

`src/gui/draggable_list.py` の冒頭 import ブロックを以下に置き換える：

```python
import customtkinter as ctk
from pathlib import Path
from typing import List, Callable, Optional, Dict
import tkinter as tk

from .theme import (
    CLR_LIGHT_BG, CLR_SEL_BORDER, CLR_RED_LIGHT, CLR_RED_TEXT,
    CLR_GRAY_TEXT, CLR_DARK_TEXT, get_file_type_badge
)
```

- [ ] **Step 2: DraggableListItem クラス全体を以下に置き換える**

`class DraggableListItem` から最後の `def _update_appearance(self):` ブロックまで（行 11〜123）を丸ごと削除し、下記コードに置き換える：

```python
class DraggableListItem(ctk.CTkFrame):
    """ドラッグ可能なリストアイテム（チェックボックスなし・行選択式）"""

    def __init__(self, parent, file_path: str, on_select: Callable,
                 on_drag_start: Callable,
                 on_remove: Optional[Callable] = None,
                 drag_enabled: bool = True,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self.file_path = file_path
        self.on_select = on_select
        self.on_drag_start = on_drag_start
        self.on_remove = on_remove
        self.drag_enabled = drag_enabled
        self.is_selected = False
        self.is_dragging = False
        self._setup_ui()
        self._setup_events()

    def _setup_ui(self):
        self.configure(height=44, fg_color="transparent", corner_radius=4)

        # ── 左: ドラッグハンドル（drag_enabled 時のみ） ──
        if self.drag_enabled:
            self.drag_handle = ctk.CTkLabel(
                self, text="⋮⋮", width=20,
                font=ctk.CTkFont(size=12),
                text_color=(CLR_GRAY_TEXT, CLR_GRAY_TEXT)
            )
            self.drag_handle.pack(side="left", padx=(6, 0), pady=4)
        else:
            self.drag_handle = None

        # ── 右: ×ボタン（ホバー時のみ表示） ──
        self.remove_btn = None
        if self.on_remove:
            self.remove_btn = ctk.CTkButton(
                self, text="✕", width=22, height=22,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
                hover_color="#FEB2B2", corner_radius=11,
                command=self._on_remove_click
            )
            self.remove_btn.pack(side="right", padx=(0, 8), pady=4)
            self.remove_btn.pack_forget()  # 初期非表示

        # ── 右: バッジ ──
        badge_text, badge_color = get_file_type_badge(self.file_path)
        self.badge_label = ctk.CTkLabel(
            self, text=badge_text,
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=badge_color, text_color="white",
            corner_radius=4, width=36, height=18
        )
        self.badge_label.pack(side="right", padx=(4, 4), pady=4)

        # ── 中: ファイル名 + パス ──
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=3)

        filename = Path(self.file_path).name
        self.filename_label = ctk.CTkLabel(
            self.text_frame, text=filename,
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=CLR_DARK_TEXT
        )
        self.filename_label.pack(anchor="w")

        parent_path = str(Path(self.file_path).parent)
        display_path = (f"...{parent_path[-35:]}" if len(parent_path) > 35
                        else parent_path)
        self.path_label = ctk.CTkLabel(
            self.text_frame, text=display_path,
            anchor="w", font=ctk.CTkFont(size=9),
            text_color=CLR_GRAY_TEXT
        )
        self.path_label.pack(anchor="w")

    def _setup_events(self):
        clickable = [self, self.text_frame, self.filename_label, self.path_label]
        if self.drag_handle:
            clickable.append(self.drag_handle)

        for w in clickable:
            w.bind("<Button-1>",        self._on_click)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Enter>",           self._on_hover_enter)
            w.bind("<Leave>",           self._on_hover_leave)
            if self.drag_enabled:
                w.bind("<B1-Motion>", self._on_drag)

    # ── ホバー ──────────────────────────────────────────────

    def _on_hover_enter(self, event=None):
        if self.remove_btn:
            self.remove_btn.pack(side="right", padx=(0, 8), pady=4)

    def _on_hover_leave(self, event=None):
        self.after(80, self._check_hover)

    def _check_hover(self):
        """マウスが行フレーム外に出たときのみ×ボタンを隠す"""
        try:
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
            w, in_self = widget, False
            while w is not None:
                if w == self:
                    in_self = True
                    break
                try:
                    w = w.master
                except Exception:
                    break
            if not in_self and self.remove_btn:
                self.remove_btn.pack_forget()
        except Exception:
            pass

    def _on_remove_click(self):
        if self.on_remove:
            self.on_remove(self.file_path)

    # ── クリック / ドラッグ ─────────────────────────────────

    def _on_click(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.is_dragging = False

    def _on_release(self, event):
        if not self.is_dragging:
            self.set_selected(not self.is_selected)
            self.on_select(self.file_path, self.is_selected)
        else:
            self.is_dragging = False

    def _on_drag(self, event):
        if not self.is_dragging and (
            abs(event.x_root - self.start_x) > 5 or
            abs(event.y_root - self.start_y) > 5
        ):
            self.is_dragging = True
            self.on_drag_start(self, event)

    # ── 選択 ────────────────────────────────────────────────

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_appearance()

    def _update_appearance(self):
        if self.is_selected:
            self.configure(fg_color=CLR_LIGHT_BG,
                           border_width=1, border_color=CLR_SEL_BORDER)
        else:
            self.configure(fg_color="transparent", border_width=0)
```

- [ ] **Step 3: アプリを起動して動作確認（手動）**

```
cd C:\Users\taka\Documents\Gemini\0030Business\PDFchangecombine
python src/main.py
```

確認: クラッシュしないこと。ファイルを追加して行クリックでハイライトが付くこと。

- [ ] **Step 4: コミット**

```
git add src/gui/draggable_list.py
git commit -m "feat: replace checkbox with row-click selection and hover remove button"
```

---

## Task 3: DraggableFileList — drag_enabled パラメータ対応

**Files:**
- Modify: `src/gui/draggable_list.py`（`DraggableFileList` クラス）

- [ ] **Step 1: `__init__` に `drag_enabled` パラメータを追加**

`DraggableFileList.__init__` の冒頭（`super().__init__` の直前）を以下に変更：

```python
def __init__(self, parent, drag_enabled: bool = True, **kwargs):
    if 'fg_color' not in kwargs:
        kwargs['fg_color'] = ("white", "white")
    super().__init__(parent, **kwargs)
    self.configure(fg_color=("white", "white"))
    self.after(1, self._set_background_colors)

    self.drag_enabled = drag_enabled          # ← 追加
    self.file_paths: List[str] = []
    self.items: Dict[str, DraggableListItem] = {}
    self.selected_files: List[str] = []
    self.drag_source: Optional[DraggableListItem] = None
    self.drop_target_index: int = -1
    self.drop_indicator = None
    self.on_selection_change: Optional[Callable] = None
    self.on_order_change: Optional[Callable] = None
```

背景色も現在の水色（`#E6F7FF`）から白（`white`）に変更する（上記コードに含まれている）。

- [ ] **Step 2: `_set_background_colors` を更新（白に変更）**

```python
def _set_background_colors(self):
    try:
        if hasattr(self, '_parent_canvas'):
            self._parent_canvas.configure(bg="white")
        if hasattr(self, '_parent_frame'):
            self._parent_frame.configure(fg_color="white")
    except Exception:
        pass
```

- [ ] **Step 3: `_create_item` に `drag_enabled` と `on_remove` を渡す**

```python
def _create_item(self, file_path: str):
    item = DraggableListItem(
        self,
        file_path,
        on_select=self._on_item_select,
        on_drag_start=self._on_drag_start,
        on_remove=self.remove_file,       # ← ホバー×ボタン用
        drag_enabled=self.drag_enabled,   # ← drag_enabled を渡す
        height=44
    )
    self.items[file_path] = item
```

- [ ] **Step 4: アプリ起動して確認（手動）**

```
python src/main.py
```

確認: ファイルリストの背景が白になっていること。ファイル行にマウスを乗せると×ボタンが出ること。×ボタンをクリックするとリストから削除されること。

- [ ] **Step 5: コミット**

```
git add src/gui/draggable_list.py
git commit -m "feat: add drag_enabled param and wire on_remove to DraggableFileList"
```

---

## Task 4: UnifiedWindow — 変換タブのリスト管理を DraggableFileList に移行

**Files:**
- Modify: `src/gui/unified_window.py`

変換タブは現在 `self.file_checkboxes` + `CTkScrollableFrame` で独自管理している。これを `DraggableFileList(drag_enabled=False)` に統一する。

- [ ] **Step 1: インポートに theme を追加**

`src/gui/unified_window.py` の import ブロックに以下を追加（`from .draggable_list import DraggableFileList` の行の後）：

```python
from .theme import (
    CLR_PRIMARY, CLR_ACCENT, CLR_LIGHT_BG, CLR_LIGHT_BORDER,
    CLR_SEL_BORDER, CLR_TOOLBAR_BG, CLR_BORDER, CLR_RED_LIGHT,
    CLR_RED_TEXT, CLR_GRAY_TEXT, CLR_DARK_TEXT, CLR_LIST_HEADER,
    CLR_WHITE, get_file_type_badge
)
```

- [ ] **Step 2: `__init__` の状態管理変数を更新**

`UnifiedWindow.__init__` 内の以下の行を削除する：

```python
self.combination_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
```

```python
# チェックボックス管理
self.file_checkboxes = {}  # 変換用ファイルチェックボックス
self.combine_checkboxes = {}  # 結合用ファイルチェックボックス
```

- [ ] **Step 3: `_create_conversion_ui` 内のファイルリストを DraggableFileList に置き換える**

`_create_conversion_ui` メソッド内の「ファイルリストエリア（チェックボックス付き）」ブロック（行 196〜232 付近）を以下に置き換える：

```python
# ファイルリスト（DraggableFileList・ドラッグ無効）
self.conversion_draggable_list = DraggableFileList(
    self.conversion_tab,
    drag_enabled=False,
    height=200,
    label_text="📁 変換対象ファイルリスト"
)
self.conversion_draggable_list.pack(fill="both", expand=True, padx=15, pady=8)
self.conversion_draggable_list.on_selection_change = self._on_conversion_selection_change

# 初期表示メッセージ
self.initial_message_label = ctk.CTkLabel(
    self.conversion_draggable_list,
    text=(
        "📁 ファイルをここにドラッグ&ドロップしてください\n\n"
        "対応ファイル:\n"
        "• Word: .docx, .doc\n"
        "• Excel: .xlsx, .xls\n"
        "• PowerPoint: .pptx, .ppt\n"
        "• 画像: .jpg, .jpeg, .png, .bmp, .gif, .tiff\n"
        "• PDF: .pdf （変換済フォルダにコピー）\n\n"
        "複数ファイルやフォルダもドロップできます"
    ),
    font=ctk.CTkFont(size=12),
    justify="left"
)
self.initial_message_label.pack(fill="both", expand=True, padx=20, pady=20)

# ファイルチェックボックス管理（廃止・互換性のため空で残す）
self.file_checkboxes = {}
```

- [ ] **Step 4: `_on_conversion_selection_change` を追加**

`UnifiedWindow` クラス内の任意の場所（例: `_on_combination_selection_change` の直前）に追加：

```python
def _on_conversion_selection_change(self, selected_files: List[str]) -> None:
    """変換リストの選択変更時のコールバック"""
    has_selection = len(selected_files) > 0
    # 選択削除ボタンの有効/無効（Task 5 でボタンを追加後に参照）
    if hasattr(self, 'conversion_delete_btn'):
        self.conversion_delete_btn.configure(
            state="normal" if has_selection else "disabled"
        )
```

- [ ] **Step 5: `_add_conversion_files` を更新**

既存の `_add_conversion_files` メソッドを以下に置き換える：

```python
def _add_conversion_files(self, paths: List[str]) -> None:
    """変換ファイル追加"""
    scan_result = FileScanner.scan_files_from_paths(paths)
    valid_files = scan_result['valid']

    if valid_files:
        new_files = [f for f in valid_files if f not in self.conversion_files]
        if new_files:
            self.conversion_files.extend(new_files)
            self.conversion_draggable_list.add_files(new_files)
            self._update_conversion_display()
            logger.info(f"変換ファイル追加: {len(new_files)}個")
        else:
            self.conversion_status.configure(text="選択されたファイルは既に追加済みです")
    else:
        self.conversion_status.configure(text="対応ファイルが見つかりませんでした")
```

- [ ] **Step 6: `_clear_files` を `_delete_selected_conversion` と `_clear_all_conversion` に分割**

既存の `_clear_files` メソッドを削除し、以下の2メソッドに置き換える：

```python
def _delete_selected_conversion(self) -> None:
    """選択中の変換ファイルを削除"""
    selected = self.conversion_draggable_list.get_selected_files()
    if not selected:
        return
    for fp in selected:
        if fp in self.conversion_files:
            self.conversion_files.remove(fp)
    self.conversion_draggable_list.remove_selected_files()
    self._update_conversion_display()
    logger.info(f"変換ファイル削除: {len(selected)}個")

def _clear_all_conversion(self, force: bool = False) -> None:
    """変換ファイルを全クリア"""
    if not self.conversion_files:
        return
    if not force and not self._show_confirmation_dialog(
        "全ファイルクリア", f"全{len(self.conversion_files)}件をクリアしますか？"
    ):
        return
    self.conversion_files.clear()
    self.conversion_draggable_list.clear_files()
    self.file_checkboxes.clear()
    self._update_conversion_display()
    self.conversion_status.configure(text="ファイルリストをクリアしました")
    logger.info("変換ファイル全クリア")
```

`_start_conversion` 完了後の `_clear_files(force=True)` 呼び出し（行 1523 付近）を `_clear_all_conversion(force=True)` に変更する。

- [ ] **Step 7: `_update_conversion_display` を更新**

既存の `_update_conversion_display` を以下に置き換える：

```python
def _update_conversion_display(self) -> None:
    """変換タブ表示更新"""
    current_files = self.conversion_draggable_list.get_files()
    self.conversion_files = current_files
    self.conversion_count_label.configure(text=f"ファイル数: {len(current_files)}")

    if current_files:
        self.initial_message_label.pack_forget()
        self.conversion_convert_btn.configure(state="normal")
        if hasattr(self, 'conversion_clear_btn'):
            self.conversion_clear_btn.configure(state="normal")
        self.conversion_status.configure(
            text=f"{len(current_files)}個のファイルが追加されました"
        )
    else:
        self.initial_message_label.pack(fill="both", expand=True, padx=20, pady=20)
        self.conversion_convert_btn.configure(state="disabled")
        if hasattr(self, 'conversion_clear_btn'):
            self.conversion_clear_btn.configure(state="disabled")
        if hasattr(self, 'conversion_delete_btn'):
            self.conversion_delete_btn.configure(state="disabled")
        self.conversion_status.configure(text="変換するファイルを追加してください")
```

- [ ] **Step 8: ドラッグ&ドロップのターゲットを更新**

`_setup_drag_drop` 内の変換タブ設定を更新する：

```python
drag_drop_handler.setup_drag_drop(
    self.conversion_draggable_list,   # file_list_frame → conversion_draggable_list
    self._add_conversion_files,
    office_filter
)
```

- [ ] **Step 9: アプリ起動で動作確認（手動）**

```
python src/main.py
```

確認: 変換タブにファイルを追加できること。行クリックでハイライトされること。

- [ ] **Step 10: コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: migrate conversion tab file list to DraggableFileList"
```

---

## Task 5: UnifiedWindow — 変換タブのツールバーUI

**Files:**
- Modify: `src/gui/unified_window.py`（`_create_conversion_ui` メソッド）

- [ ] **Step 1: 上部ボタンフレームを新ツールバーに置き換える**

`_create_conversion_ui` 内の「ボタンフレーム（上部左側）」ブロック（`conversion_btn_frame` 定義〜 `conversion_count_label` まで）を以下に置き換える：

```python
# ── ツールバー ──
toolbar = ctk.CTkFrame(self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
                        border_width=1, border_color=CLR_BORDER, corner_radius=6)
toolbar.pack(fill="x", padx=15, pady=(8, 5))

self.conversion_select_btn = ctk.CTkButton(
    toolbar, text="📂 ファイル追加",
    command=self._select_conversion_files,
    height=32, width=110,
    fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
    font=ctk.CTkFont(size=11, weight="bold")
)
self.conversion_select_btn.pack(side="left", padx=(8, 4), pady=6)

self.conversion_delete_btn = ctk.CTkButton(
    toolbar, text="✕ 選択削除",
    command=self._delete_selected_conversion,
    height=32, width=90,
    fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
    hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
    state="disabled"
)
self.conversion_delete_btn.pack(side="left", padx=(0, 4), pady=6)

self.conversion_clear_btn = ctk.CTkButton(
    toolbar, text="🗑️ 全クリア",
    command=self._clear_all_conversion,
    height=32, width=80,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
    state="disabled"
)
self.conversion_clear_btn.pack(side="left", padx=(0, 4), pady=6)

self.conversion_count_label = ctk.CTkLabel(
    toolbar, text="ファイル数: 0",
    font=ctk.CTkFont(size=11), text_color=CLR_GRAY_TEXT
)
self.conversion_count_label.pack(side="right", padx=10, pady=6)
```

- [ ] **Step 2: アプリ起動して確認（手動）**

```
python src/main.py
```

確認: 変換タブのツールバーがクリーンブルーで表示されること。ファイル追加→選択削除ボタンが有効化されること。

- [ ] **Step 3: コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: redesign conversion tab toolbar with clean blue theme"
```

---

## Task 6: UnifiedWindow — 結合タブのツールバーとテーマ更新

**Files:**
- Modify: `src/gui/unified_window.py`（`_create_combination_ui` メソッド）

- [ ] **Step 1: `_create_combination_ui` のボタンフレームを新ツールバーに置き換える**

`_create_combination_ui` 内の `list_btn_frame` 定義〜 `combination_count_label` までを以下に置き換える：

```python
# ── ツールバー ──
toolbar = ctk.CTkFrame(self.combination_tab, fg_color=CLR_TOOLBAR_BG,
                        border_width=1, border_color=CLR_BORDER, corner_radius=6)
toolbar.pack(fill="x", padx=15, pady=(8, 5))

self.combination_select_btn = ctk.CTkButton(
    toolbar, text="📂 PDF追加",
    command=self._select_combination_files,
    height=32, width=100,
    fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
    font=ctk.CTkFont(size=11, weight="bold")
)
self.combination_select_btn.pack(side="left", padx=(8, 4), pady=6)

self.combination_delete_btn = ctk.CTkButton(
    toolbar, text="✕ 選択削除",
    command=self._delete_selected_combination,
    height=32, width=90,
    fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
    hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
    state="disabled"
)
self.combination_delete_btn.pack(side="left", padx=(0, 4), pady=6)

self.combination_clear_btn = ctk.CTkButton(
    toolbar, text="🗑️ クリア",
    command=self._clear_combination_files,
    height=32, width=70,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
)
self.combination_clear_btn.pack(side="left", padx=(0, 4), pady=6)

self.combination_move_up_btn = ctk.CTkButton(
    toolbar, text="↑", command=self._move_combination_up,
    height=32, width=36,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
)
self.combination_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

self.combination_move_down_btn = ctk.CTkButton(
    toolbar, text="↓", command=self._move_combination_down,
    height=32, width=36,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
)
self.combination_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

self.combination_count_label = ctk.CTkLabel(
    toolbar, text="ファイル数: 0",
    font=ctk.CTkFont(size=11), text_color=CLR_GRAY_TEXT
)
self.combination_count_label.pack(side="right", padx=10, pady=6)
```

- [ ] **Step 2: `DraggableFileList` の `fg_color` を white に（既にTask3で変更済み）**

`DraggableFileList` のインスタンス生成コードを確認：

```python
self.combination_draggable_list = DraggableFileList(
    self.combination_tab,
    height=200,
    label_text="📋 PDFファイル結合リスト（ドラッグで並び替え可能）"
)
```

`drag_enabled` はデフォルト `True` なので変更不要。

- [ ] **Step 3: 結合タブの初期メッセージラベルの `fg_color` を削除**

`combination_list_msg` から `fg_color="#E6F7FF"` 引数を削除する（白背景に合わせる）：

```python
self.combination_list_msg = ctk.CTkLabel(
    self.combination_draggable_list,
    text="📋 PDFファイルをここにドラッグ&ドロップしてください\n\n・複数PDFファイルの結合に対応\n・ファイルリストの順序で結合されます\n・ドラッグで順序変更、↑↓ボタンでも調整可能",
    font=ctk.CTkFont(size=12),
    justify="left",
    corner_radius=8
)
```

- [ ] **Step 4: アプリ起動して確認（手動）**

```
python src/main.py
```

確認: 結合タブのツールバーがクリーンブルーで表示されること。

- [ ] **Step 5: コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: redesign combination tab toolbar with clean blue theme"
```

---

## Task 7: UnifiedWindow — 資料NOタブのツールバーとテーマ更新

**Files:**
- Modify: `src/gui/unified_window.py`（`_create_document_number_ui` メソッド）

- [ ] **Step 1: `_create_document_number_ui` のボタンフレームを新ツールバーに置き換える**

`_create_document_number_ui` 内の `btn_frame` 定義〜 `document_count_label` までを以下に置き換える：

```python
# ── ツールバー ──
toolbar = ctk.CTkFrame(self.document_number_tab, fg_color=CLR_TOOLBAR_BG,
                        border_width=1, border_color=CLR_BORDER, corner_radius=6)
toolbar.pack(fill="x", padx=15, pady=(8, 5))

self.document_select_btn = ctk.CTkButton(
    toolbar, text="📂 PDFファイル選択",
    command=self._select_document_number_files,
    height=32, width=130,
    fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
    font=ctk.CTkFont(size=11, weight="bold")
)
self.document_select_btn.pack(side="left", padx=(8, 4), pady=6)

self.document_delete_btn = ctk.CTkButton(
    toolbar, text="✕ 選択削除",
    command=self._delete_selected_document,
    height=32, width=90,
    fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
    hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
    state="disabled"
)
self.document_delete_btn.pack(side="left", padx=(0, 4), pady=6)

self.document_clear_btn = ctk.CTkButton(
    toolbar, text="🗑️ クリア",
    command=self._clear_document_number_files,
    height=32, width=70,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_GRAY_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER,
    state="disabled"
)
self.document_clear_btn.pack(side="left", padx=(0, 4), pady=6)

self.document_move_up_btn = ctk.CTkButton(
    toolbar, text="↑", command=self._move_document_up,
    height=32, width=36,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
)
self.document_move_up_btn.pack(side="left", padx=(0, 2), pady=6)

self.document_move_down_btn = ctk.CTkButton(
    toolbar, text="↓", command=self._move_document_down,
    height=32, width=36,
    fg_color=CLR_TOOLBAR_BG, text_color=CLR_DARK_TEXT,
    hover_color=CLR_BORDER, border_width=1, border_color=CLR_BORDER
)
self.document_move_down_btn.pack(side="left", padx=(0, 4), pady=6)

self.document_count_label = ctk.CTkLabel(
    toolbar, text="ファイル数: 0",
    font=ctk.CTkFont(size=11), text_color=CLR_GRAY_TEXT
)
self.document_count_label.pack(side="right", padx=10, pady=6)
```

- [ ] **Step 2: 初期メッセージの fg_color を削除**

`document_list_msg` から `fg_color="#E6F7FF"` を削除（`corner_radius=8` は維持）。

- [ ] **Step 3: アプリ起動して確認（手動）**

```
python src/main.py
```

確認: 資料NOタブのツールバーがクリーンブルーで表示されること。

- [ ] **Step 4: コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: redesign document-number tab toolbar with clean blue theme"
```

---

## Task 8: UnifiedWindow — オプションを CTkSwitch に変更

**Files:**
- Modify: `src/gui/unified_window.py`

- [ ] **Step 1: 変換タブの Excel 分割オプションを CTkSwitch に変更**

`_create_conversion_ui` 内の `split_excel_sheets_checkbox` 定義を以下に置き換える：

```python
# Excelシート分割オプション
self.excel_options_frame = ctk.CTkFrame(
    self.conversion_tab, fg_color=CLR_TOOLBAR_BG,
    border_width=1, border_color=CLR_BORDER, corner_radius=6
)
self.excel_options_frame.pack(fill="x", padx=15, pady=(0, 5))

ctk.CTkLabel(
    self.excel_options_frame,
    text="⚙️ Excelのシートを個別のPDFに分割する",
    font=ctk.CTkFont(size=11), text_color=CLR_DARK_TEXT
).pack(side="left", padx=(10, 8), pady=6)

self.split_excel_sheets_switch = ctk.CTkSwitch(
    self.excel_options_frame, text="",
    variable=self.split_excel_sheets_var,
    onvalue=True, offvalue=False,
    progress_color=CLR_PRIMARY
)
self.split_excel_sheets_switch.pack(side="right", padx=10, pady=6)
```

`_run_conversion` 内の `split_sheets = self.split_excel_sheets_var.get()` はそのまま動作する（変数は同じ）。

- [ ] **Step 2: 結合タブの「白紙挿入」オプションを CTkSwitch に変更**

`_create_combination_ui` 内の `add_blank_page_checkbox` 定義を以下に置き換える：

```python
# オプションフレーム（白紙挿入 + ページ番号）
options_frame = ctk.CTkFrame(
    self.combination_tab, fg_color=CLR_TOOLBAR_BG,
    border_width=1, border_color=CLR_BORDER, corner_radius=6
)
options_frame.pack(fill="x", padx=15, pady=(0, 5))

# 白紙挿入スイッチ
blank_row = ctk.CTkFrame(options_frame, fg_color="transparent")
blank_row.pack(fill="x", padx=8, pady=(6, 2))

ctk.CTkLabel(
    blank_row, text="奇数ページのPDF末尾に白紙ページを挿入する",
    font=ctk.CTkFont(size=11), text_color=CLR_DARK_TEXT
).pack(side="left")

self.add_blank_page_switch = ctk.CTkSwitch(
    blank_row, text="", variable=self.add_blank_page_var,
    onvalue=True, offvalue=False, progress_color=CLR_PRIMARY
)
self.add_blank_page_switch.pack(side="right")

# ページ番号スイッチ
page_row = ctk.CTkFrame(options_frame, fg_color="transparent")
page_row.pack(fill="x", padx=8, pady=(2, 6))

ctk.CTkLabel(
    page_row, text="フッター中央にページ番号を挿入する",
    font=ctk.CTkFont(size=11), text_color=CLR_DARK_TEXT
).pack(side="left")

self.add_page_number_switch = ctk.CTkSwitch(
    page_row, text="", variable=self.add_page_number_var,
    onvalue=True, offvalue=False, progress_color=CLR_PRIMARY,
    command=self._toggle_page_number_options
)
self.add_page_number_switch.pack(side="right", padx=(8, 0))

# 開始ページ・開始番号（インライン）
self.start_page_label = ctk.CTkLabel(
    page_row, text="開始ページ:", font=ctk.CTkFont(size=11)
)
self.start_page_label.pack(side="right", padx=(8, 2))

self.start_page_entry = ctk.CTkEntry(
    page_row, textvariable=self.start_page_var, width=40
)
self.start_page_entry.pack(side="right")

self.start_number_label = ctk.CTkLabel(
    page_row, text="開始番号:", font=ctk.CTkFont(size=11)
)
self.start_number_label.pack(side="right", padx=(8, 2))

self.start_number_entry = ctk.CTkEntry(
    page_row, textvariable=self.start_number_var, width=40
)
self.start_number_entry.pack(side="right")

self._toggle_page_number_options()
```

`page_number_frame` の定義（既存）と `add_page_number_checkbox` の定義を削除する（上記コードに含まれていない部分）。

- [ ] **Step 3: `_toggle_page_number_options` が参照するウィジェット名を確認**

```python
def _toggle_page_number_options(self) -> None:
    state = "normal" if self.add_page_number_var.get() else "disabled"
    self.start_page_label.configure(state=state)
    self.start_page_entry.configure(state=state)
    self.start_number_label.configure(state=state)
    self.start_number_entry.configure(state=state)
```

変数名は Task 2 で定義したものと一致しているので変更不要。

- [ ] **Step 4: アプリ起動して確認（手動）**

```
python src/main.py
```

確認: 変換タブにトグルスイッチが表示されること。結合タブのオプションがスイッチ化されること。スイッチON/OFFでページ番号入力欄の有効/無効が切り替わること。

- [ ] **Step 5: コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: replace option checkboxes with CTkSwitch"
```

---

## Task 9: UnifiedWindow — ヘッダーとタブバーのデザイン更新

**Files:**
- Modify: `src/gui/unified_window.py`（`_create_main_ui` メソッド）

- [ ] **Step 1: タイトルバーをクリーンブルーヘッダーに置き換える**

`_create_main_ui` 内の「タイトルバー」ブロック（`title_frame` 〜 `title_label.pack` まで）を以下に置き換える：

```python
# ── ヘッダー（クリーンブルー） ──
header_frame = ctk.CTkFrame(
    self.main_frame, fg_color=CLR_PRIMARY, corner_radius=8
)
header_frame.pack(fill="x", padx=10, pady=(10, 5))

ctk.CTkLabel(
    header_frame, text="📄",
    font=ctk.CTkFont(size=22)
).pack(side="left", padx=(14, 6), pady=10)

ctk.CTkLabel(
    header_frame,
    text="PDF変換・結合ツール",
    font=ctk.CTkFont(size=18, weight="bold"),
    text_color="white"
).pack(side="left", pady=10)
```

- [ ] **Step 2: タブバーのスタイルを更新**

`_create_main_ui` 内の `CTkTabview` 定義を以下に更新する（`segmented_button_*` の色をより洗練されたブルー系に変更）：

```python
self.tab_view = ctk.CTkTabview(
    self.main_frame,
    width=530, height=620,
    text_color=(CLR_DARK_TEXT, CLR_DARK_TEXT),
    segmented_button_selected_color=CLR_LIGHT_BG,
    segmented_button_selected_hover_color=CLR_LIGHT_BG,
    segmented_button_unselected_color=("gray90", "gray25"),
    segmented_button_unselected_hover_color=(CLR_BORDER, "gray30"),
    border_color=CLR_BORDER, border_width=1
)
self.tab_view.pack(fill="both", expand=True, padx=10, pady=5)
self.tab_view._segmented_button.configure(font=ctk.CTkFont(size=13, weight="bold"))
```

- [ ] **Step 3: `_set_conversion_frame_colors` メソッドを削除**

`unified_window.py` 内の `_set_conversion_frame_colors` メソッド全体（行 1482〜1490 付近）を削除する。`_create_conversion_ui` 内の `self.file_list_frame.after(1, self._set_conversion_frame_colors)` も削除する（Task 4 で `file_list_frame` 自体を削除済み）。

- [ ] **Step 4: `_create_main_ui` のメインフレーム背景を更新**

```python
self.main_frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray10"))
self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)
```

- [ ] **Step 5: アプリを起動して全体確認（手動）**

```
python src/main.py
```

確認項目:
1. ヘッダーが青背景・白文字で表示される
2. 全タブが正常に切り替わる
3. PDF変換タブ: ファイル追加 → 行クリックでハイライト → 選択削除ボタン有効化 → 削除
4. PDF変換タブ: ファイル行にホバー → ×ボタン出現 → クリックで即削除
5. PDF変換タブ: ファイルが追加された状態で変換実行 → 完了
6. PDF結合タブ: ファイル追加 → ドラッグ並び替え → ↑↓ボタン移動
7. 資料NOタブ: ファイル追加 → 番号設定 → 実行
8. オプションのトグルスイッチが動作する

- [ ] **Step 6: 最終テスト**

```
pytest tests/ -v
```

期待: 全既存テスト PASS（コアロジックは変更していないため）

- [ ] **Step 7: 最終コミット**

```
git add src/gui/unified_window.py
git commit -m "feat: update header and tab bar to clean blue design

- Add blue gradient header with icon
- Refine tab view styling
- Remove legacy background color hacks"
```

---

## セルフレビュー結果

**仕様書カバレッジ確認:**

| 仕様要件 | 対応タスク |
|---|---|
| チェックボックス廃止（変換タブ） | Task 4 |
| チェックボックス廃止（結合・資料NOタブ） | Task 2 |
| 行クリックでハイライト選択 | Task 2 |
| ホバー×ボタン（1件即削除） | Task 2, 3 |
| ツールバー「選択削除」ボタン | Task 5, 6, 7 |
| ファイル種別バッジ | Task 1, 2 |
| クリーンブルーカラーテーマ | Task 1, 5, 6, 7, 9 |
| ヘッダー単色ブルー（グラデーション不可のため） | Task 9 |
| CTkSwitch オプション化 | Task 8 |
| drag_enabled=False で変換タブは並び替え不可 | Task 3, 4 |
| 全クリアのみ確認ダイアログ | Task 4 |
| 白ベース背景（水色廃止） | Task 3, 6, 7 |
