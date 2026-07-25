"""
資料の差し替え・構成変更ダイアログ
本アプリで結合したPDF（構成情報を内部に持つもの）を選択し、
資料単位での差し替え・追加・削除・一括リナンバリングを行う。
"""

import threading
from pathlib import Path
from typing import Callable, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..utils.file_utils import OutputManager
from .theme import (
    FONT_FAMILY, CLR_COMB_PRIMARY, CLR_COMB_HOVER, CLR_BORDER,
    CLR_DARK_TEXT, CLR_GRAY_TEXT, CLR_RED_LIGHT, CLR_RED_TEXT, CLR_WHITE, CLR_LIGHT_BG,
)


def _set_buttons_state(container, state: str) -> None:
    """containerの配下にあるCTkButtonをすべて有効/無効にする"""
    for child in container.winfo_children():
        if isinstance(child, ctk.CTkButton):
            child.configure(state=state)
        _set_buttons_state(child, state)


class ReplaceDocumentDialog(ctk.CTkToplevel):
    """PDF結合タブから開く、資料差し替え・構成変更用のダイアログ"""

    _WIDTH = 620
    _HEIGHT = 560

    def __init__(self, parent, pdf_combiner, initial_pdf_path: str = "",
                 open_folder_callback: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self.title("資料の差し替え・構成変更")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.transient(parent)

        self._combiner = pdf_combiner
        self._open_folder_callback = open_folder_callback
        self._current_pdf_path: str = ""
        self._documents: List[dict] = []
        self._busy = False

        self._build()
        self.update_idletasks()
        self._center(parent)
        self.grab_set()

        if initial_pdf_path:
            self._load_pdf(initial_pdf_path)

    def _center(self, parent):
        px = parent.winfo_x() + (parent.winfo_width() - self._WIDTH) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self._HEIGHT) // 2
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}+{max(px, 0)}+{max(py, 0)}")

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 4))

        self._path_label = ctk.CTkLabel(
            header, text="対象の結合済みPDFを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT,
            anchor="w", justify="left", wraplength=440
        )
        self._path_label.pack(side="left", fill="x", expand=True)

        self._choose_btn = ctk.CTkButton(
            header, text="PDFを選択...", width=110,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            command=self._choose_pdf
        )
        self._choose_btn.pack(side="right")

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 8))

        self._add_first_btn = ctk.CTkButton(
            toolbar, text="＋ 先頭に資料を追加...", width=170, height=28,
            fg_color=CLR_WHITE, text_color=CLR_COMB_PRIMARY,
            border_width=1, border_color=CLR_COMB_PRIMARY, hover_color=CLR_LIGHT_BG,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._start_insert(None)
        )
        self._add_first_btn.pack(side="left")

        self._renumber_btn = ctk.CTkButton(
            toolbar, text="🔢 一括リナンバリング...", width=170, height=28,
            fg_color=CLR_WHITE, text_color=CLR_COMB_PRIMARY,
            border_width=1, border_color=CLR_COMB_PRIMARY, hover_color=CLR_LIGHT_BG,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._open_renumber_dialog
        )
        self._renumber_btn.pack(side="left", padx=(8, 0))

        self._list_frame = ctk.CTkScrollableFrame(self, fg_color=("white", "white"))
        self._list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._show_empty_message("結合済みPDFを選択すると、資料一覧が表示されます。")

        self._status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT,
            anchor="w"
        )
        self._status_label.pack(fill="x", padx=16)

        self._progress = ctk.CTkProgressBar(self)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_BORDER, text_color=CLR_DARK_TEXT, hover_color="#CBD5E0",
            command=self.destroy
        ).pack(pady=(0, 14))

    def _show_empty_message(self, text: str):
        for child in self._list_frame.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self._list_frame, text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT
        ).pack(pady=30)

    # ── PDF読み込み ────────────────────────────────────────────

    def _choose_pdf(self):
        if self._busy:
            return
        path = filedialog.askopenfilename(
            title="対象の結合済みPDFを選択",
            filetypes=[("PDFファイル", "*.pdf")]
        )
        if path:
            self._load_pdf(path)

    def _load_pdf(self, path: str):
        result = self._combiner.load_combine_manifest(path)
        if not result.success:
            messagebox.showerror("読み込みエラー", result.error_message)
            return

        self._current_pdf_path = path
        self._documents = result.manifest.get("documents", [])
        self._path_label.configure(text=path, text_color=CLR_DARK_TEXT)
        self._status_label.configure(text="")
        self._refresh_list()

    def _refresh_list(self):
        for child in self._list_frame.winfo_children():
            child.destroy()

        if not self._documents:
            self._show_empty_message("このPDFには資料が含まれていません。")
            return

        for entry in self._documents:
            self._build_row(entry)

    def _build_row(self, entry: dict):
        row = ctk.CTkFrame(self._list_frame, fg_color="transparent", border_width=1,
                            border_color=CLR_BORDER, corner_radius=6)
        row.pack(fill="x", pady=3)

        label = entry.get("document_number") or "(番号なし)"
        filename = entry.get("source_filename", "")
        page_start = entry.get("page_start")
        page_end = entry.get("page_end")
        page_range = f"p.{page_start}-{page_end}" if page_start and page_end else ""

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            text_frame, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=CLR_DARK_TEXT, anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            text_frame, text=f"{filename}　({page_range})",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=CLR_GRAY_TEXT, anchor="w"
        ).pack(fill="x")

        button_frame = ctk.CTkFrame(row, fg_color="transparent")
        button_frame.pack(side="right", padx=8, pady=6)

        ctk.CTkButton(
            button_frame, text="差し替え...", width=84, height=26,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=lambda e=entry: self._start_replace(e)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            button_frame, text="＋この後に追加", width=100, height=26,
            fg_color=CLR_WHITE, text_color=CLR_COMB_PRIMARY,
            border_width=1, border_color=CLR_COMB_PRIMARY, hover_color=CLR_LIGHT_BG,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=lambda e=entry: self._start_insert(e)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            button_frame, text="削除", width=56, height=26,
            fg_color=CLR_RED_LIGHT, text_color=CLR_RED_TEXT,
            hover_color="#FEB2B2", border_width=1, border_color="#FEB2B2",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=lambda e=entry: self._start_delete(e)
        ).pack(side="left", padx=2)

    # ── 差し替え実行 ────────────────────────────────────────────

    def _start_replace(self, entry: dict):
        if self._busy:
            return

        document_number = entry.get("document_number") or ""
        new_path = filedialog.askopenfilename(
            title=f"「{document_number or '選択した資料'}」の差し替え後PDFを選択",
            filetypes=[("PDFファイル", "*.pdf")]
        )
        if not new_path:
            return

        if not messagebox.askyesno(
            "差し替えの確認",
            f"「{document_number}」を次のファイルに差し替えますか？\n\n"
            f"差し替え後: {Path(new_path).name}\n\n"
            f"元の結合済みPDFは変更されず、新しいファイルとして出力されます。"
        ):
            return

        self._set_busy(True)
        threading.Thread(
            target=self._run_replace, args=(document_number, new_path), daemon=True
        ).start()

    def _run_replace(self, document_number: str, new_path: str):
        current = self._current_pdf_path
        try:
            def progress_callback(message, progress):
                self.after(0, lambda: self._progress.set(progress / 100))
                self.after(0, lambda: self._status_label.configure(text=message))

            output_path = self._make_output_path(current, "差替済")

            result = self._combiner.replace_document_in_combined_pdf(
                current, document_number, new_path, output_path,
                progress_callback=progress_callback,
            )

            self.after(0, lambda: self._on_operation_complete(result, "差し替え"))

        except Exception as e:
            self.after(0, lambda: self._on_operation_error(str(e)))

    # ── 追加実行 ────────────────────────────────────────────────

    def _start_insert(self, after_entry: Optional[dict]):
        if self._busy:
            return

        new_path = filedialog.askopenfilename(
            title="追加するPDFを選択",
            filetypes=[("PDFファイル", "*.pdf")]
        )
        if not new_path:
            return

        template_settings = self._pick_template_stamp_settings(after_entry)
        dialog = ctk.CTkInputDialog(
            title="資料番号の入力",
            text="追加する資料の番号を入力してください（例: 4）。\n空欄のまま実行すると、番号スタンプなしで追加します。"
        )
        number_value = dialog.get_input()
        if number_value is None:
            return
        number_value = number_value.strip()

        document_prefix = (template_settings or {}).get("document_prefix", "資料")
        if number_value:
            document_number = f"{document_prefix}{number_value}"
            stamp_settings = dict(template_settings) if template_settings else {
                "document_prefix": document_prefix, "font_display_name": None,
                "doc_font_size": 20, "white_background": False,
                "a3_portrait_compat": False, "insert_all_pages": False,
            }
            stamp_settings["number_part"] = number_value
            stamp_settings["document_prefix"] = document_prefix
        else:
            document_number = ""
            stamp_settings = None

        anchor_label = after_entry.get("document_number") if after_entry else None
        position_desc = f"「{anchor_label}」の直後" if anchor_label else "先頭"
        if not messagebox.askyesno(
            "追加の確認",
            f"{position_desc}に次のファイルを追加しますか？\n\n"
            f"追加するファイル: {Path(new_path).name}\n"
            f"資料番号: {document_number or '（なし）'}\n\n"
            f"元の結合済みPDFは変更されず、新しいファイルとして出力されます。"
        ):
            return

        self._set_busy(True)
        threading.Thread(
            target=self._run_insert,
            args=(new_path, anchor_label, document_number, stamp_settings),
            daemon=True
        ).start()

    def _pick_template_stamp_settings(self, after_entry: Optional[dict]) -> Optional[dict]:
        """新規追加資料のスタンプ見た目のひな形を選ぶ（隣接資料 → 先頭のスタンプ済み資料の順）"""
        if after_entry and after_entry.get("stamp_settings"):
            return after_entry["stamp_settings"]
        for entry in self._documents:
            if entry.get("stamp_settings"):
                return entry["stamp_settings"]
        return None

    def _run_insert(self, new_path: str, anchor_label: Optional[str],
                    document_number: str, stamp_settings: Optional[dict]):
        current = self._current_pdf_path
        try:
            def progress_callback(message, progress):
                self.after(0, lambda: self._progress.set(progress / 100))
                self.after(0, lambda: self._status_label.configure(text=message))

            output_path = self._make_output_path(current, "資料追加済")

            result = self._combiner.insert_document_into_combined_pdf(
                current, new_path, output_path,
                insert_after_document_number=anchor_label,
                document_number=document_number, stamp_settings=stamp_settings,
                progress_callback=progress_callback,
            )

            self.after(0, lambda: self._on_operation_complete(result, "追加"))

        except Exception as e:
            self.after(0, lambda: self._on_operation_error(str(e)))

    # ── 削除実行 ────────────────────────────────────────────────

    def _start_delete(self, entry: dict):
        if self._busy:
            return

        document_number = entry.get("document_number") or "(番号なし)"
        if not messagebox.askyesno(
            "削除の確認",
            f"「{document_number}」を削除しますか？\n\n"
            f"他の資料の番号は自動では振り直されません（欠番として残ります）。\n"
            f"番号を詰めたい場合は、削除後に「一括リナンバリング」を実行してください。\n\n"
            f"元の結合済みPDFは変更されず、新しいファイルとして出力されます。"
        ):
            return

        self._set_busy(True)
        threading.Thread(
            target=self._run_delete, args=(entry.get("document_number") or "",), daemon=True
        ).start()

    def _run_delete(self, document_number: str):
        current = self._current_pdf_path
        try:
            def progress_callback(message, progress):
                self.after(0, lambda: self._progress.set(progress / 100))
                self.after(0, lambda: self._status_label.configure(text=message))

            output_path = self._make_output_path(current, "資料削除済")

            result = self._combiner.delete_document_from_combined_pdf(
                current, document_number, output_path,
                progress_callback=progress_callback,
            )

            self.after(0, lambda: self._on_operation_complete(result, "削除"))

        except Exception as e:
            self.after(0, lambda: self._on_operation_error(str(e)))

    # ── 一括リナンバリング ──────────────────────────────────────

    def _open_renumber_dialog(self):
        if self._busy or not self._current_pdf_path:
            return
        _RenumberSettingsDialog(self, on_confirm=self._start_renumber)

    def _start_renumber(self, numbering_type: str, start_number: int, prefix_number: str,
                        document_prefix: str):
        if not messagebox.askyesno(
            "一括リナンバリングの確認",
            "資料番号スタンプ済みの資料をすべて振り直します。\n"
            "元データが確認できない資料はスキップされます。\n\n"
            "元の結合済みPDFは変更されず、新しいファイルとして出力されます。実行しますか？"
        ):
            return

        self._set_busy(True)
        threading.Thread(
            target=self._run_renumber,
            args=(numbering_type, start_number, prefix_number, document_prefix),
            daemon=True
        ).start()

    def _run_renumber(self, numbering_type: str, start_number: int, prefix_number: str,
                      document_prefix: str):
        current = self._current_pdf_path
        try:
            def progress_callback(message, progress):
                self.after(0, lambda: self._progress.set(progress / 100))
                self.after(0, lambda: self._status_label.configure(text=message))

            output_path = self._make_output_path(current, "再採番済")

            result = self._combiner.renumber_documents_in_combined_pdf(
                current, output_path,
                numbering_type=numbering_type, start_number=start_number,
                prefix_number=prefix_number, document_prefix=document_prefix,
                progress_callback=progress_callback,
            )

            self.after(0, lambda: self._on_operation_complete(result, "一括リナンバリング"))

        except Exception as e:
            self.after(0, lambda: self._on_operation_error(str(e)))

    # ── 共通 ────────────────────────────────────────────────────

    def _make_output_path(self, current_path: str, suffix: str) -> str:
        out_dir = str(Path(current_path).parent)
        filename = f"{Path(current_path).stem}_{suffix}.pdf"
        return OutputManager.get_unique_output_path(out_dir, filename)

    def _on_operation_complete(self, result, operation_name: str) -> None:
        self._set_busy(False)
        self._progress.set(1.0 if result.success else 0)

        if result.success:
            self._status_label.configure(
                text=f"{operation_name}完了: {Path(result.output_path).name} ({result.total_pages}ページ)"
            )
            self._load_pdf(result.output_path)

            notice = ""
            if result.error_message:
                # 成功しつつ一部スキップ等の通知がある場合（再採番のスキップ通知など）
                notice = f"\n\n{result.error_message}"

            if self._open_folder_callback and messagebox.askyesno(
                f"{operation_name}完了",
                f"{operation_name}が完了しました。\n\n出力先: {result.output_path}{notice}\n\n"
                f"出力フォルダを開きますか？"
            ):
                self._open_folder_callback(str(Path(result.output_path).parent))
            elif notice:
                messagebox.showinfo(f"{operation_name}完了", notice.strip())
        else:
            self._status_label.configure(text=f"{operation_name}に失敗しました")
            messagebox.showerror(f"{operation_name}失敗", result.error_message)

    def _on_operation_error(self, message: str) -> None:
        self._set_busy(False)
        self._progress.set(0)
        self._status_label.configure(text="処理に失敗しました")
        messagebox.showerror("処理失敗", message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._choose_btn.configure(state=state)
        self._add_first_btn.configure(state=state)
        self._renumber_btn.configure(state=state)
        _set_buttons_state(self._list_frame, state)
        if busy:
            self._status_label.configure(text="処理中...")


class _RenumberSettingsDialog(ctk.CTkToplevel):
    """一括リナンバリングの番号方式を入力する小さなダイアログ"""

    def __init__(self, parent, on_confirm: Callable[[str, int, str, str], None]):
        super().__init__(parent)
        self.title("一括リナンバリング")
        self.resizable(False, False)
        self.transient(parent)

        self._on_confirm = on_confirm
        self._prefix_var = ctk.StringVar(value="資料")
        self._type_var = ctk.StringVar(value="連番")
        self._number_var = ctk.StringVar(value="1")

        self._build()
        self.update_idletasks()
        self._center(parent)
        self.grab_set()

    def _center(self, parent):
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px, 0)}+{max(py, 0)}")

    def _build(self):
        ctk.CTkLabel(
            self, text="プレフィックス", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            anchor="w"
        ).pack(padx=20, pady=(20, 2), anchor="w")
        ctk.CTkEntry(self, textvariable=self._prefix_var, width=340).pack(padx=20)

        ctk.CTkLabel(
            self, text="番号方式", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            anchor="w"
        ).pack(padx=20, pady=(12, 2), anchor="w")
        ctk.CTkSegmentedButton(
            self, variable=self._type_var, values=["連番", "ハイフン連番"],
        ).pack(padx=20, fill="x")

        ctk.CTkLabel(
            self, text="開始番号 / ハイフン前の番号", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            anchor="w"
        ).pack(padx=20, pady=(12, 2), anchor="w")
        ctk.CTkEntry(self, textvariable=self._number_var, width=340).pack(padx=20)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(20, 18))
        ctk.CTkButton(
            btn_row, text="キャンセル", width=100,
            fg_color=CLR_BORDER, text_color=CLR_DARK_TEXT, hover_color="#CBD5E0",
            command=self.destroy
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row, text="実行する", width=100,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            command=self._confirm
        ).pack(side="left", padx=6)

    def _confirm(self):
        prefix = self._prefix_var.get().strip() or "資料"
        number_text = self._number_var.get().strip() or "1"
        if not number_text.isdigit():
            messagebox.showwarning("入力エラー", "番号には数字を入力してください。")
            return

        numbering_type = "hyphen" if self._type_var.get() == "ハイフン連番" else "basic"
        start_number = int(number_text)
        prefix_number = number_text

        self.destroy()
        self._on_confirm(numbering_type, start_number, prefix_number, prefix)
