"""
ドラッグアンドドロップ対応のカスタムリストコンポーネント
"""

import customtkinter as ctk
from pathlib import Path
from typing import List, Callable, Optional, Dict
import tkinter as tk
import re

from .theme import (
    CLR_LIGHT_BG, CLR_SEL_BORDER, CLR_RED_LIGHT, CLR_RED_TEXT,
    CLR_GRAY_TEXT, CLR_DARK_TEXT, get_file_type_badge, FONT_FAMILY
)

try:
    from ..utils.drag_drop import drag_drop_handler as _drag_drop_handler
except Exception:
    _drag_drop_handler = None


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
        self.configure(height=26, fg_color="transparent", corner_radius=4)

        self.drag_handle = None

        # ── 右: ×ボタン（ホバー時のみ表示） ──
        self.remove_btn = None
        if self.on_remove:
            self.remove_btn = ctk.CTkButton(
                self, text="✕", width=20, height=18,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
                hover_color="#FEB2B2", corner_radius=9,
                command=self._on_remove_click
            )
            self.remove_btn.pack(side="right", padx=(0, 6), pady=2)
            self.remove_btn.pack_forget()  # 初期非表示

        # ── 右: バッジ ──
        badge_text, badge_color = get_file_type_badge(self.file_path)
        self.badge_label = ctk.CTkLabel(
            self, text=badge_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            fg_color=badge_color, text_color="white",
            corner_radius=4, width=36, height=16
        )
        self.badge_label.pack(side="right", padx=(4, 4), pady=2)

        # ── 中: ファイル名 ──
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=1)

        filename = Path(self.file_path).name
        self.filename_label = ctk.CTkLabel(
            self.text_frame, text=filename,
            anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=CLR_DARK_TEXT
        )
        self.filename_label.pack(anchor="w")

    def _setup_events(self):
        clickable = [self, self.text_frame, self.filename_label]
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


class DraggableFileList(ctk.CTkScrollableFrame):
    """ドラッグアンドドロップ対応のファイルリスト"""

    def __init__(self, parent, drag_enabled: bool = True, **kwargs):
        if 'fg_color' not in kwargs:
            kwargs['fg_color'] = ("white", "white")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=("white", "white"))
        self.after(1, self._set_background_colors)

        self.drag_enabled = drag_enabled
        self.file_paths: List[str] = []
        self.items: Dict[str, DraggableListItem] = {}
        self.selected_files: List[str] = []
        self.drag_source: Optional[DraggableListItem] = None
        self.drop_target_index: int = -1

        # ドロップ位置を示すインジケーター
        self.drop_indicator = None

        # コールバック
        self.on_selection_change: Optional[Callable] = None
        self.on_order_change: Optional[Callable] = None

        # 外部ドロップ（OSからのD&D）設定
        self._ext_drop_callback: Optional[Callable] = None
        self._ext_drop_filter: Optional[Callable] = None

    def _set_background_colors(self):
        try:
            if hasattr(self, '_parent_canvas'):
                self._parent_canvas.configure(bg="white")
            if hasattr(self, '_parent_frame'):
                self._parent_frame.configure(fg_color="white")
        except Exception:
            pass

    def add_file(self, file_path: str):
        """ファイルを追加"""
        if file_path not in self.file_paths:
            self.file_paths.append(file_path)
            self._create_item(file_path)
            self._update_display()

    def add_files(self, file_paths: List[str]):
        """複数ファイルを追加"""
        new_files = [f for f in file_paths if f not in self.file_paths]
        self.file_paths.extend(new_files)

        for file_path in new_files:
            self._create_item(file_path)

        self._update_display()

    def remove_selected_files(self):
        """選択されたファイルを削除"""
        for file_path in self.selected_files[:]:
            self.remove_file(file_path)

    def remove_file(self, file_path: str):
        """ファイルを削除"""
        if file_path in self.file_paths:
            self.file_paths.remove(file_path)

            if file_path in self.items:
                self.items[file_path].destroy()
                del self.items[file_path]

            if file_path in self.selected_files:
                self.selected_files.remove(file_path)

            self._update_display()

    def clear_files(self):
        """すべてのファイルをクリア"""
        for item in self.items.values():
            item.destroy()

        self.file_paths.clear()
        self.items.clear()
        self.selected_files.clear()
        self._update_display()

    def get_files(self) -> List[str]:
        """ファイルパスのリストを取得"""
        return self.file_paths.copy()

    def get_selected_files(self) -> List[str]:
        """選択されたファイルのリストを取得"""
        return self.selected_files.copy()

    def set_external_drop(self, callback: Callable, file_filter: Optional[Callable] = None) -> None:
        """OSからのD&D受け入れ設定を保存（新規アイテム生成時にも適用）"""
        self._ext_drop_callback = callback
        self._ext_drop_filter = file_filter

    def _register_widget_for_drop(self, widget) -> None:
        """ウィジェットとその子を外部D&Dターゲットとして登録"""
        if _drag_drop_handler is None or self._ext_drop_callback is None:
            return
        try:
            _drag_drop_handler.setup_drag_drop(widget, self._ext_drop_callback, self._ext_drop_filter)
            for child in widget.winfo_children():
                try:
                    _drag_drop_handler.setup_drag_drop(child, self._ext_drop_callback, self._ext_drop_filter)
                except Exception:
                    pass
        except Exception:
            pass

    def _create_item(self, file_path: str):
        """リストアイテムの作成"""
        item = DraggableListItem(
            self,
            file_path,
            on_select=self._on_item_select,
            on_drag_start=self._on_drag_start,
            on_remove=self.remove_file,
            drag_enabled=self.drag_enabled,
            height=26
        )
        self.items[file_path] = item

        # 新しいアイテムも外部D&Dターゲットとして登録
        self._register_widget_for_drop(item)

    def _update_display(self):
        """表示の更新"""
        # 既存のアイテムを全て削除
        for item in self.items.values():
            item.pack_forget()

        # 新しい順序で表示
        for file_path in self.file_paths:
            if file_path in self.items:
                self.items[file_path].pack(fill="x", padx=5, pady=1)

        # コールバック呼び出し
        if self.on_order_change:
            self.on_order_change(self.file_paths)

    def _on_item_select(self, file_path: str, selected: bool):
        """アイテム選択時の処理"""
        if selected and file_path not in self.selected_files:
            self.selected_files.append(file_path)
        elif not selected and file_path in self.selected_files:
            self.selected_files.remove(file_path)

        # 全てのアイテムの外観を更新
        self._update_all_appearances()

        if self.on_selection_change:
            self.on_selection_change(self.selected_files)

    def _update_all_appearances(self):
        """全アイテムの外観を更新"""
        for file_path, item in self.items.items():
            item.is_selected = file_path in self.selected_files
            item._update_appearance()

    def update_selection_appearance(self, selected_files: List[str]):
        """外部から選択状態の外観を更新"""
        self.selected_files = selected_files[:]
        self._update_all_appearances()

    def _on_drag_start(self, item: DraggableListItem, event):
        """ドラッグ開始時の処理"""
        self.drag_source = item

        # ドロップインジケーターの作成
        if not self.drop_indicator:
            self.drop_indicator = ctk.CTkFrame(
                self,
                height=2,
                fg_color=("blue", "lightblue")
            )

        # マウス座標に基づいてドロップ位置を計算
        self._update_drop_position(event)

        # ドラッグ中のイベントバインド
        self.bind_all("<B1-Motion>", self._on_drag_motion)
        self.bind_all("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_motion(self, event):
        """ドラッグ中の処理"""
        if self.drag_source:
            self._update_drop_position(event)

    def _on_drag_end(self, event):
        """ドラッグ終了時の処理"""
        # イベントバインドを解除
        self.unbind_all("<B1-Motion>")
        self.unbind_all("<ButtonRelease-1>")

        # ドロップインジケーターを非表示
        if self.drop_indicator:
            self.drop_indicator.pack_forget()

        # ドロップ処理
        if self.drag_source and self.drop_target_index >= 0:
            self._perform_drop()

        self.drag_source = None
        self.drop_target_index = -1

    def _update_drop_position(self, event):
        """ドロップ位置の更新"""
        # スクロール領域内のY座標を取得
        widget_y = self.winfo_rooty()
        relative_y = event.y_root - widget_y

        # どのアイテムの間にドロップするかを計算
        item_height = 39  # アイテムの高さ + パディング
        target_index = min(max(0, relative_y // item_height), len(self.file_paths))

        if target_index != self.drop_target_index:
            self.drop_target_index = target_index
            self._show_drop_indicator()

    def _show_drop_indicator(self):
        """ドロップインジケーターの表示"""
        if not self.drop_indicator:
            return

        # インジケーターを非表示
        self.drop_indicator.pack_forget()

        # 新しい位置に表示
        if 0 <= self.drop_target_index <= len(self.file_paths):
            # 対象位置の前にインジケーターを挿入
            target_item = None
            if self.drop_target_index < len(self.file_paths):
                target_file = self.file_paths[self.drop_target_index]
                target_item = self.items.get(target_file)

            if target_item:
                self.drop_indicator.pack(fill="x", padx=5, before=target_item)
            else:
                # 最後に追加
                self.drop_indicator.pack(fill="x", padx=5)

    def _perform_drop(self):
        """ドロップ処理の実行"""
        if not self.drag_source:
            return

        source_file = self.drag_source.file_path
        source_index = self.file_paths.index(source_file)

        # ドロップ位置の調整
        target_index = self.drop_target_index
        if target_index > source_index:
            target_index -= 1  # 元の位置より後ろにドロップする場合は調整

        # ファイルリストの順序を変更
        self.file_paths.pop(source_index)
        self.file_paths.insert(target_index, source_file)

        # 表示を更新
        self._update_display()

    def move_selected_up(self):
        """選択されたファイルを上に移動"""
        if not self.selected_files:
            return False

        moved = False
        for file_path in self.selected_files:
            current_index = self.file_paths.index(file_path)
            if current_index > 0:
                self.file_paths[current_index], self.file_paths[current_index - 1] = \
                    self.file_paths[current_index - 1], self.file_paths[current_index]
                moved = True

        if moved:
            self._update_display()

        return moved

    def move_selected_down(self):
        """選択されたファイルを下に移動"""
        if not self.selected_files:
            return False

        moved = False
        # 下に移動する時は逆順で処理
        for file_path in reversed(self.selected_files):
            current_index = self.file_paths.index(file_path)
            if current_index < len(self.file_paths) - 1:
                self.file_paths[current_index], self.file_paths[current_index + 1] = \
                    self.file_paths[current_index + 1], self.file_paths[current_index]
                moved = True

        if moved:
            self._update_display()

        return moved

    def sort_by_filename(self):
        """ファイル名の自然順（数値を考慮）で並び替え"""
        def _natural_key(path: str):
            name = Path(path).name.lower()
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', name)]

        self.file_paths.sort(key=_natural_key)
        self._update_display()