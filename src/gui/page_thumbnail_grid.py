"""
ページ編集タブのサムネイルグリッド

表示専用のウィジェット。ページの並びと描画済み画像を外から受け取って
並べるだけで、fitz には触れない（描画は PageEditWorker 上で行う）。
"""

from typing import Callable, Dict, List, Optional, Set

import customtkinter as ctk
import fitz
from PIL import Image, ImageTk

from ..core.page_editor import PageRef
from .theme import (
    CLR_BORDER,
    CLR_DARK_TEXT,
    CLR_LIGHT_BG,
    CLR_PE_PRIMARY,
    CLR_SEL_BORDER,
    FONT_FAMILY,
)

# サムネイル幅110px。A4縦で高さ約156px、ラベルと余白を含めたセルは約126×184px
THUMBNAIL_WIDTH = 110
CELL_WIDTH = 126
CELL_HEIGHT = 184

# 表示サイズプリセット（表示名 → サムネイル幅px）。中が既定（THUMBNAIL_WIDTHと同じ）
THUMBNAIL_SIZE_PRESETS = {"小": 80, "中": THUMBNAIL_WIDTH, "大": 150}
DEFAULT_THUMBNAIL_SIZE = "中"


def cell_dims_for(thumb_width: int) -> "tuple[int, int]":
    """サムネイル幅から、余白込みのセル幅・高さを求める（A4縦比率を仮定）"""
    cell_width = thumb_width + 16
    cell_height = int(round(thumb_width * 1.414)) + 28
    return cell_width, cell_height


def calc_columns(grid_width: int, cell_width: int = CELL_WIDTH,
                 min_columns: int = 1) -> int:
    """グリッドの実幅から列数を求める（固定列数にしない）"""
    if grid_width <= 0:
        return min_columns
    return max(min_columns, grid_width // cell_width)


def render_thumbnail(page: "fitz.Page", width: int = THUMBNAIL_WIDTH) -> Image.Image:
    """1ページを指定幅のサムネイル画像にする。

    必ず PageEditWorker のスレッド上から呼ぶこと（fitz はスレッドセーフでない）。
    """
    # 幅0のページ（壊れたPDFで稀にある）で ZeroDivisionError にしない
    if page.rect.width <= 0:
        raise ValueError("ページの幅が0のため、サムネイルを作成できません")
    scale = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


class _PageCell(ctk.CTkFrame):
    """1ページぶんのセル（チェックボックス＋ページ番号＋サムネイル）"""

    def __init__(self, parent, index: int, image: Optional[ImageTk.PhotoImage],
                 on_toggle: Callable[[int, bool], None],
                 on_shift_click: Optional[Callable[[int], None]] = None,
                 on_preview: Optional[Callable[[int], None]] = None,
                 on_wheel: Optional[Callable[[object], None]] = None,
                 cell_width: int = CELL_WIDTH, cell_height: int = CELL_HEIGHT):
        super().__init__(
            parent, fg_color="transparent", border_width=1,
            border_color=CLR_BORDER, corner_radius=4,
            width=cell_width, height=cell_height,
        )
        self.grid_propagate(False)
        self._index = index
        self._on_toggle = on_toggle
        self._on_shift_click = on_shift_click
        self._on_preview = on_preview
        self._on_wheel = on_wheel

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=2, pady=(2, 0))

        self.var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            header, text="", width=18, checkbox_width=16, checkbox_height=16,
            variable=self.var, command=self._toggled,
            fg_color=CLR_PE_PRIMARY, hover_color=CLR_PE_PRIMARY,
        )
        self.checkbox.pack(side="left")

        self._number_label = ctk.CTkLabel(
            header, text=str(index + 1), text_color=CLR_DARK_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        )
        self._number_label.pack(side="left", padx=(2, 0))

        # 右クリックだけでは気づきにくいため、拡大プレビュー用のボタンを明示的に置く
        if on_preview is not None:
            preview_btn = ctk.CTkButton(
                header, text="🔍", command=self._preview,
                width=20, height=18, fg_color="transparent",
                text_color=CLR_DARK_TEXT, hover_color=CLR_BORDER,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            )
            preview_btn.pack(side="right", padx=(0, 2))

        self.image_label = ctk.CTkLabel(self, text="", image=image)
        self.image_label.pack(expand=True)
        # クリックでも選択できる（チェックボックスは自前のtoggleを持つのでここでは扱わない）
        self.image_label.bind("<Button-1>", lambda _e: self.toggle())

        # Shift+クリック（範囲選択）・右クリック（拡大プレビュー、🔍ボタンの補助）・
        # ホイール（親グリッドのスクロール）は、セル内のどこを操作しても効くように
        # したい。だが CTkCheckBox は内部でキャンバス等に分割された子ウィジェットを
        # 持ち、実際にクリックを受け取るのはその内部ウィジェットのため、
        # self.checkbox 自体へのbindでは拾えない。セル配下の全ウィジェットへ
        # 再帰的にbindすることで、チェックボックスの上で操作しても確実に反応させる。
        self._bind_recursive(self, "<Shift-Button-1>", lambda _e: self._shift_click())
        self._bind_recursive(self, "<Button-3>", lambda _e: self._preview())
        if on_wheel is not None:
            self._bind_recursive(self, "<MouseWheel>", self._forward_wheel)

    @staticmethod
    def _bind_recursive(widget, sequence: str, handler) -> None:
        widget.bind(sequence, handler, add="+")
        for child in widget.winfo_children():
            _PageCell._bind_recursive(child, sequence, handler)

    def _forward_wheel(self, event) -> None:
        if self._on_wheel is not None:
            self._on_wheel(event)

    def _toggled(self) -> None:
        self._update_appearance()
        self._on_toggle(self._index, self.var.get())

    def toggle(self) -> None:
        self.var.set(not self.var.get())
        self._toggled()

    def update_content(self, index: int, image: Optional[ImageTk.PhotoImage]) -> None:
        """ウィジェットを作り直さず、表すページだけを差し替える（並べ替えの高速化用）"""
        self._index = index
        self._number_label.configure(text=str(index + 1))
        self.image_label.configure(image=image)
        self.var.set(False)
        self._update_appearance()

    def _shift_click(self) -> None:
        if self._on_shift_click is not None:
            self._on_shift_click(self._index)

    def _preview(self) -> None:
        if self._on_preview is not None:
            self._on_preview(self._index)

    def set_selected(self, selected: bool) -> None:
        self.var.set(selected)
        self._update_appearance()

    def _update_appearance(self) -> None:
        if self.var.get():
            self.configure(fg_color=CLR_LIGHT_BG, border_color=CLR_SEL_BORDER,
                           border_width=2)
        else:
            self.configure(fg_color="transparent", border_color=CLR_BORDER,
                           border_width=1)


class PageThumbnailGrid(ctk.CTkScrollableFrame):
    """サムネイルを並べるグリッド。列数はウィンドウ幅に追従する"""

    def __init__(self, parent, on_selection_change: Callable[[Set[int]], None],
                 on_preview: Optional[Callable[[int], None]] = None,
                 **kwargs):
        super().__init__(parent, fg_color="white", **kwargs)
        self._on_selection_change = on_selection_change
        self._on_preview = on_preview
        self._pages: List[PageRef] = []
        self._images: Dict[PageRef, ImageTk.PhotoImage] = {}
        self._cells: List[_PageCell] = []
        self._selected: Set[int] = set()
        self._anchor_index: Optional[int] = None
        self._columns = 0
        self._cell_width = CELL_WIDTH
        self._cell_height = CELL_HEIGHT
        # _rebuild() がセルを使い回してよいか判定するための「最後に構築した時点のサイズ」
        self._built_cell_width = CELL_WIDTH
        self._built_cell_height = CELL_HEIGHT
        # add="+" が必須: CTkScrollableFrame は自身の <Configure> に
        # スクロール範囲（scrollregion）更新用のハンドラを内部で登録している。
        # add="+" を付けずに bind すると、その内部ハンドラを丸ごと上書きしてしまい、
        # コンテンツが増えてもスクロール可能範囲が更新されなくなる
        # （スクロールバーが効かない・ホイールがわずかしか動かない原因）。
        self.bind("<Configure>", self._on_configure, add="+")
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")

    # ── 公開API ──

    @property
    def selected_indices(self) -> Set[int]:
        return set(self._selected)

    def set_cell_size(self, cell_width: int, cell_height: int) -> None:
        """サムネイル表示サイズ変更時のセル寸法を設定する（再描画は set_pages 側で行う）"""
        self._cell_width = cell_width
        self._cell_height = cell_height

    def set_pages(self, pages: List[PageRef],
                  images: Dict[PageRef, ImageTk.PhotoImage]) -> None:
        """並びと画像を差し替えて再描画する（選択状態はクリアされる）"""
        self._pages = list(pages)
        self._images = images
        self._selected = set()
        self._anchor_index = None
        self._rebuild()
        self._on_selection_change(set())

    def reorder(self, pages: List[PageRef]) -> None:
        """ページ枚数が変わらない並べ替え専用の高速パス。

        set_pages() は全セルを破棄して作り直すため、ページ数が多いと
        並べ替えのたびに毎回何百ものウィジェットを再生成することになり遅い。
        並べ替えでは各セルが表すページが変わるだけで枚数もレイアウトも
        変わらないため、既存ウィジェットの中身だけを差し替えて使い回す。
        枚数が変わっている（想定外の呼び出し）場合は set_pages にフォールバックする。
        """
        if len(pages) != len(self._cells):
            self.set_pages(pages, self._images)
            return
        old_pages = self._pages
        self._pages = list(pages)
        # 実際に表示ページが変わったセルだけ更新する（ページ数が多いと
        # 全セル更新は体感できるほど遅いため。1〜2ページの移動なら
        # ほとんどのセルは元のページのままで更新不要）
        for i, (cell, ref) in enumerate(zip(self._cells, self._pages)):
            if i >= len(old_pages) or old_pages[i] != ref:
                cell.update_content(i, self._images.get(ref))
        self._selected = set()

    def select_indices(self, indices: Set[int]) -> None:
        """指定インデックスのみを選択状態にする（例: 移動操作後の選択復元用）"""
        valid = {i for i in indices if 0 <= i < len(self._cells)}
        # 選択状態が実際に変わるセルだけ更新する（全セル更新は
        # ページ数が多いと体感できるほど遅いため）
        for i in self._selected.symmetric_difference(valid):
            self._cells[i].set_selected(i in valid)
        self._selected = valid
        self._on_selection_change(self.selected_indices)

    def clear_selection(self) -> None:
        for i in self._selected:
            if 0 <= i < len(self._cells):
                self._cells[i].set_selected(False)
        self._selected = set()
        self._anchor_index = None
        self._on_selection_change(set())

    def select_all(self) -> None:
        all_indices = set(range(len(self._pages)))
        for i in all_indices - self._selected:
            self._cells[i].set_selected(True)
        self._selected = all_indices
        self._on_selection_change(self.selected_indices)

    # ── 内部 ──

    def _on_toggle(self, index: int, selected: bool) -> None:
        if selected:
            self._selected.add(index)
        else:
            self._selected.discard(index)
        self._anchor_index = index
        self._on_selection_change(self.selected_indices)

    def _on_shift_click(self, index: int) -> None:
        """アンカー（直前に単独操作したページ）から index までを範囲選択する"""
        if not self._cells:
            return
        anchor = self._anchor_index if self._anchor_index is not None else index
        lo, hi = sorted((anchor, index))
        self.select_indices(set(range(lo, hi + 1)))
        # 連続してShiftクリックすると範囲を伸縮できるよう、アンカーは動かさない
        self._anchor_index = anchor

    def _on_preview_click(self, index: int) -> None:
        if self._on_preview is not None:
            self._on_preview(index)

    def _on_mousewheel(self, event) -> None:
        """マウスホイールで縦スクロールする（Windows: event.delta は120単位）"""
        canvas = getattr(self, "_parent_canvas", None)
        if canvas is not None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_configure(self, event) -> None:
        """幅が変わって列数が変わったときだけ配置し直す"""
        columns = calc_columns(event.width, cell_width=self._cell_width)
        if columns != self._columns:
            self._columns = columns
            self._layout()

    def _rebuild(self) -> None:
        """セルをできるだけ使い回して再構築する。

        削除・挿入・取り消し等でページ枚数が変わっても、大半のセルは
        「表示する内容（ページ）が変わるだけ」であり、ウィジェットとしては
        使い回せる。全セルを毎回壊して作り直すと、ページ数が多いPDFでは
        操作のたびに何百ものウィジェットを再生成することになり体感できる
        ほど遅くなるため、枚数の差分ぶんだけ作成・破棄する。
        表示サイズ（セル寸法）が変わった直後だけは使い回さず全部作り直す。
        """
        size_changed = (self._built_cell_width != self._cell_width or
                        self._built_cell_height != self._cell_height)
        if size_changed:
            for cell in self._cells:
                cell.destroy()
            self._cells = []

        old_count = len(self._cells)
        new_count = len(self._pages)
        reuse_count = min(old_count, new_count)

        for i in range(reuse_count):
            self._cells[i].update_content(i, self._images.get(self._pages[i]))

        if new_count < old_count:
            for cell in self._cells[new_count:]:
                cell.destroy()
            self._cells = self._cells[:new_count]
        elif new_count > old_count:
            for i in range(old_count, new_count):
                self._cells.append(
                    _PageCell(self, i, self._images.get(self._pages[i]),
                              self._on_toggle, self._on_shift_click,
                              self._on_preview_click, on_wheel=self._on_mousewheel,
                              cell_width=self._cell_width, cell_height=self._cell_height)
                )

        self._built_cell_width = self._cell_width
        self._built_cell_height = self._cell_height
        self._columns = calc_columns(self.winfo_width(), cell_width=self._cell_width)
        self._layout()

    def _layout(self) -> None:
        columns = max(1, self._columns)
        for i, cell in enumerate(self._cells):
            cell.grid(row=i // columns, column=i % columns, padx=4, pady=4)
