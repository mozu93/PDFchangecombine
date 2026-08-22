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
    scale = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


class _PageCell(ctk.CTkFrame):
    """1ページぶんのセル（チェックボックス＋ページ番号＋サムネイル）"""

    def __init__(self, parent, index: int, image: Optional[ImageTk.PhotoImage],
                 on_toggle: Callable[[int, bool], None]):
        super().__init__(
            parent, fg_color="transparent", border_width=1,
            border_color=CLR_BORDER, corner_radius=4,
            width=CELL_WIDTH, height=CELL_HEIGHT,
        )
        self.grid_propagate(False)
        self._index = index
        self._on_toggle = on_toggle

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=2, pady=(2, 0))

        self.var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            header, text="", width=18, checkbox_width=16, checkbox_height=16,
            variable=self.var, command=self._toggled,
            fg_color=CLR_PE_PRIMARY, hover_color=CLR_PE_PRIMARY,
        )
        self.checkbox.pack(side="left")

        ctk.CTkLabel(
            header, text=str(index + 1), text_color=CLR_DARK_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(side="left", padx=(2, 0))

        self.image_label = ctk.CTkLabel(self, text="", image=image)
        self.image_label.pack(expand=True)
        # クリックでも選択できるようにする
        self.image_label.bind("<Button-1>", lambda _e: self.toggle())

    def _toggled(self) -> None:
        self._update_appearance()
        self._on_toggle(self._index, self.var.get())

    def toggle(self) -> None:
        self.var.set(not self.var.get())
        self._toggled()

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
                 **kwargs):
        super().__init__(parent, fg_color="white", **kwargs)
        self._on_selection_change = on_selection_change
        self._pages: List[PageRef] = []
        self._images: Dict[PageRef, ImageTk.PhotoImage] = {}
        self._cells: List[_PageCell] = []
        self._selected: Set[int] = set()
        self._columns = 0
        self.bind("<Configure>", self._on_configure)

    # ── 公開API ──

    @property
    def selected_indices(self) -> Set[int]:
        return set(self._selected)

    def set_pages(self, pages: List[PageRef],
                  images: Dict[PageRef, ImageTk.PhotoImage]) -> None:
        """並びと画像を差し替えて再描画する（選択状態はクリアされる）"""
        self._pages = list(pages)
        self._images = images
        self._selected = set()
        self._rebuild()
        self._on_selection_change(set())

    def clear_selection(self) -> None:
        for cell in self._cells:
            cell.set_selected(False)
        self._selected = set()
        self._on_selection_change(set())

    def select_all(self) -> None:
        for cell in self._cells:
            cell.set_selected(True)
        self._selected = set(range(len(self._pages)))
        self._on_selection_change(self.selected_indices)

    # ── 内部 ──

    def _on_toggle(self, index: int, selected: bool) -> None:
        if selected:
            self._selected.add(index)
        else:
            self._selected.discard(index)
        self._on_selection_change(self.selected_indices)

    def _on_configure(self, event) -> None:
        """幅が変わって列数が変わったときだけ配置し直す"""
        columns = calc_columns(event.width)
        if columns != self._columns:
            self._columns = columns
            self._layout()

    def _rebuild(self) -> None:
        for cell in self._cells:
            cell.destroy()
        self._cells = []
        for i, ref in enumerate(self._pages):
            self._cells.append(
                _PageCell(self, i, self._images.get(ref), self._on_toggle)
            )
        self._columns = calc_columns(self.winfo_width())
        self._layout()

    def _layout(self) -> None:
        columns = max(1, self._columns)
        for i, cell in enumerate(self._cells):
            cell.grid(row=i // columns, column=i % columns, padx=4, pady=4)
