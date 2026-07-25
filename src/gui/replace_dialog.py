"""
資料差し替えダイアログ
本アプリで結合したPDF（構成情報を内部に持つもの）を選択し、
中の1資料だけを別ファイルに差し替える。
"""

import threading
from pathlib import Path
from typing import Callable, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..utils.file_utils import OutputManager
from .theme import (
    FONT_FAMILY, CLR_COMB_PRIMARY, CLR_COMB_HOVER, CLR_BORDER,
    CLR_DARK_TEXT, CLR_GRAY_TEXT,
)


class ReplaceDocumentDialog(ctk.CTkToplevel):
    """PDF結合タブから開く、資料差し替え用のダイアログ"""

    _WIDTH = 560
    _HEIGHT = 520

    def __init__(self, parent, pdf_combiner, initial_pdf_path: str = "",
                 open_folder_callback: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self.title("資料の差し替え")
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
        header.pack(fill="x", padx=16, pady=(16, 8))

        self._path_label = ctk.CTkLabel(
            header, text="差し替え対象の結合済みPDFを選択してください",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=CLR_GRAY_TEXT,
            anchor="w", justify="left", wraplength=380
        )
        self._path_label.pack(side="left", fill="x", expand=True)

        self._choose_btn = ctk.CTkButton(
            header, text="PDFを選択...", width=110,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            command=self._choose_pdf
        )
        self._choose_btn.pack(side="right")

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
            title="差し替え対象の結合済みPDFを選択",
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

        replace_btn = ctk.CTkButton(
            row, text="差し替え...", width=90,
            fg_color=CLR_COMB_PRIMARY, hover_color=CLR_COMB_HOVER,
            command=lambda e=entry: self._start_replace(e)
        )
        replace_btn.pack(side="right", padx=10)

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

            out_dir = str(Path(current).parent)
            filename = f"{Path(current).stem}_差替済.pdf"
            output_path = OutputManager.get_unique_output_path(out_dir, filename)

            result = self._combiner.replace_document_in_combined_pdf(
                current, document_number, new_path, output_path,
                progress_callback=progress_callback,
            )

            self.after(0, lambda: self._on_replace_complete(result))

        except Exception as e:
            self.after(0, lambda: self._on_replace_error(str(e)))

    def _on_replace_complete(self, result) -> None:
        self._set_busy(False)
        self._progress.set(1.0 if result.success else 0)

        if result.success:
            self._status_label.configure(
                text=f"差し替え完了: {Path(result.output_path).name} ({result.total_pages}ページ)"
            )
            self._load_pdf(result.output_path)

            if self._open_folder_callback and messagebox.askyesno(
                "差し替え完了",
                f"差し替えが完了しました。\n\n出力先: {result.output_path}\n\n"
                f"出力フォルダを開きますか？"
            ):
                self._open_folder_callback(str(Path(result.output_path).parent))
        else:
            self._status_label.configure(text="差し替えに失敗しました")
            messagebox.showerror("差し替え失敗", result.error_message)

    def _on_replace_error(self, message: str) -> None:
        self._set_busy(False)
        self._progress.set(0)
        self._status_label.configure(text="差し替えに失敗しました")
        messagebox.showerror("差し替え失敗", message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._choose_btn.configure(state=state)
        for row in self._list_frame.winfo_children():
            for child in row.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(state=state)
        if busy:
            self._status_label.configure(text="差し替え処理中...")
