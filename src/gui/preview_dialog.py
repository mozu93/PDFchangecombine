"""
PDFプレビューダイアログ - 資料番号・ページ番号の挿入位置をプレビュー
ズーム（＋／－ボタン・マウスホイール）、ドラッグパン対応
"""

import threading
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import fitz
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT

_RENDER_SCALE = 1.5
_CANVAS_W = 740
_CANVAS_H = 540

# ズームステップ（フィット比率に対する倍率）
_ZOOM_STEPS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
_FIT_IDX = 3   # _ZOOM_STEPS[3] == 1.0 がフィット


def _load_jp_font(size_px: int) -> ImageFont.FreeTypeFont:
    for fp in [
        "C:/Windows/Fonts/msmincho.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothic.ttf",
    ]:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size_px)
            except Exception:
                continue
    return ImageFont.load_default()


def _paste_rotated_text(img: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                         x_pdf: float, y_pdf: float,
                         tw_pdf: float, font_size_pdf: float,
                         hi_color: tuple, text_color: tuple) -> None:
    """90°CW 回転テキストを img に合成する（left-binding 用）"""
    s = _RENDER_SCALE
    tw_px = max(1, int(tw_pdf * s))
    fh_px = max(1, int(font_size_pdf * s))
    tmp = Image.new("RGBA", (tw_px, fh_px), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.rectangle([0, 0, tw_px - 1, fh_px - 1], fill=hi_color)
    d.text((4, 2), text, font=font, fill=text_color)
    rotated = tmp.rotate(-90, expand=True)
    img.paste(rotated, (int(x_pdf * s), int(y_pdf * s)), rotated)


def _paste_normal_text(img: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                        x_pdf: float, y_pdf: float,
                        tw_pdf: float, font_size_pdf: float,
                        hi_color: tuple, text_color: tuple) -> None:
    """通常（水平）テキストを img に描画する"""
    s = _RENDER_SCALE
    xp = int(x_pdf * s)
    yp = int(y_pdf * s)
    tw_px = max(1, int(tw_pdf * s))
    fh_px = max(1, int(font_size_pdf * s))
    d = ImageDraw.Draw(img)
    d.rectangle([xp - 2, yp - 2, xp + tw_px + 2, yp + fh_px + 2], fill=hi_color)
    d.text((xp, yp), text, font=font, fill=text_color)


# ─── 資料番号プレビュー ──────────────────────────────────────────


def render_doc_number_preview(
    pdf_path: str,
    document_text: str,
    a3_portrait_compat: bool,
    white_background: bool = False,
) -> Optional[Image.Image]:
    """資料番号挿入位置のプレビュー画像を生成する（フルサイズで返す）"""
    try:
        with fitz.open(pdf_path) as doc:
            if not doc:
                return None
            page = doc[0]
            orig_rot = page.rotation
            if orig_rot:
                page.set_rotation(0)
            pw, ph = page.rect.width, page.rect.height
            pix = page.get_pixmap(matrix=fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")

        font_size = 20.0
        margin = 28.35
        jc = sum(1 for c in document_text if ord(c) > 127)
        ac = len(document_text) - jc
        tw = jc * font_size + ac * (font_size * 0.6)

        is_a3p = orig_rot == 0 and ph > 1000 and ph > pw
        is_ls  = orig_rot == 0 and pw > ph and pw < 1100
        rotate_text = a3_portrait_compat and (is_a3p or is_ls)

        if orig_rot == 0:
            if rotate_text:
                x = pw - margin - font_size
                y = ph - margin - tw
            else:
                x = pw - tw - margin
                y = margin
        elif orig_rot == 90:
            x, y = margin, margin
        elif orig_rot == 180:
            x, y = margin, ph - margin - font_size
        else:
            x = pw - margin - font_size
            y = ph - margin - tw

        font = _load_jp_font(int(font_size * _RENDER_SCALE))
        hi  = (255, 255, 255, 255) if white_background else (220, 50, 50, 160)
        col = (180, 0, 0, 255)

        if rotate_text:
            _paste_rotated_text(img, document_text, font, x, y, tw, font_size, hi, col)
        else:
            _paste_normal_text(img, document_text, font, x, y, tw, font_size, hi, col)

        return img.convert("RGB")
    except Exception:
        return None


# ─── ページ番号プレビュー ─────────────────────────────────────────


def render_page_number_preview(
    pdf_path: str,
    page_number_text: str,
    binding_compat: bool,
) -> Optional[Image.Image]:
    """ページ番号挿入位置のプレビュー画像を生成する（フルサイズで返す）"""
    try:
        with fitz.open(pdf_path) as doc:
            if not doc:
                return None
            page = doc[0]
            orig_rot = page.rotation
            if orig_rot:
                page.set_rotation(0)
            pw, ph = page.rect.width, page.rect.height
            pix = page.get_pixmap(matrix=fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")

        font_size = 12.0
        margin = 28.35
        tw = fitz.get_text_length(page_number_text, fontname="cour", fontsize=font_size)

        rotate_text = False
        if orig_rot == 0:
            is_a3l = pw > ph and pw > 1100
            is_lb  = (pw > ph and pw <= 1100) or (ph > pw and ph > 1000)
            if binding_compat and is_a3l:
                # A3横 Z折り（片袖折り）: 右端から75mm
                x = pw - (75 * 72 / 25.4) - tw
                y = ph - margin - font_size
            elif binding_compat and is_lb:
                x = margin
                y = (ph - tw) / 2
                rotate_text = True
            else:
                x = (pw - tw) / 2
                y = ph - margin - font_size
        else:
            x = (pw - tw) / 2
            y = ph - margin - font_size

        font = _load_jp_font(int(font_size * _RENDER_SCALE))
        hi  = (50, 80, 220, 160)
        col = (0, 0, 180, 255)

        if rotate_text:
            _paste_rotated_text(img, page_number_text, font, x, y, tw, font_size, hi, col)
        else:
            _paste_normal_text(img, page_number_text, font, x, y, tw, font_size, hi, col)

        return img.convert("RGB")
    except Exception:
        return None


# ─── ダイアログ ──────────────────────────────────────────────────


class PDFPreviewDialog(ctk.CTkToplevel):
    """PDF 挿入位置プレビューダイアログ（ズーム・パン対応）"""

    def __init__(self, parent, title: str,
                 render_fn: Callable[[], Optional[Image.Image]]):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._orig_img: Optional[Image.Image] = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        self._zoom_idx: int = _FIT_IDX
        self._fit_scale: float = 1.0

        # ── ズームツールバー ──────────────────────────────────────
        tb = ctk.CTkFrame(self, fg_color="transparent")
        tb.pack(fill="x", padx=12, pady=(12, 4))

        self._btn_zout = ctk.CTkButton(
            tb, text="－", width=36, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            command=self._zoom_out, state="disabled"
        )
        self._btn_zout.pack(side="left", padx=(0, 2))

        self._zoom_lbl = ctk.CTkLabel(
            tb, text="読込中...", width=80,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        )
        self._zoom_lbl.pack(side="left", padx=4)

        self._btn_zin = ctk.CTkButton(
            tb, text="＋", width=36, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            command=self._zoom_in, state="disabled"
        )
        self._btn_zin.pack(side="left", padx=(2, 10))

        self._btn_fit = ctk.CTkButton(
            tb, text="フィット", width=72, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._zoom_fit, state="disabled"
        )
        self._btn_fit.pack(side="left")

        ctk.CTkLabel(
            tb, text="マウスホイールでズーム / ドラッグでスクロール",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="gray"
        ).pack(side="right", padx=8)

        # ── キャンバス + スクロールバー ───────────────────────────
        cf = tk.Frame(self, bg="#444444")
        cf.pack(fill="both", expand=True, padx=12, pady=0)

        self._sb_y = tk.Scrollbar(cf, orient="vertical")
        self._sb_x = tk.Scrollbar(cf, orient="horizontal")
        self._canvas = tk.Canvas(
            cf, bg="#606060", cursor="fleur",
            width=_CANVAS_W, height=_CANVAS_H,
            highlightthickness=0,
            yscrollcommand=self._sb_y.set,
            xscrollcommand=self._sb_x.set,
        )
        self._sb_y.config(command=self._canvas.yview)
        self._sb_x.config(command=self._canvas.xview)

        self._sb_y.pack(side="right", fill="y")
        self._sb_x.pack(side="bottom", fill="x")
        self._canvas.pack(side="left", fill="both", expand=True)

        # 読み込み中テキスト
        self._loading_id = self._canvas.create_text(
            _CANVAS_W // 2, _CANVAS_H // 2,
            text="プレビューを生成中...",
            font=(FONT_FAMILY, 14), fill="white"
        )

        # マウス操作バインド
        self._canvas.bind("<ButtonPress-1>", self._drag_start)
        self._canvas.bind("<B1-Motion>", self._drag_move)
        self._canvas.bind("<MouseWheel>", self._on_wheel)

        # ── 閉じるボタン ──────────────────────────────────────────
        ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=self.destroy
        ).pack(pady=10)

        # ウィンドウを親の中央付近に配置
        self.update_idletasks()
        w = _CANVAS_W + 32
        h = _CANVAS_H + 140
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")

        threading.Thread(target=self._render, args=(render_fn,), daemon=True).start()

    # ── レンダリング ──────────────────────────────────────────────

    def _render(self, fn: Callable):
        img = fn()
        self.after(0, lambda: self._display(img))

    def _display(self, img: Optional[Image.Image]) -> None:
        self._canvas.delete(self._loading_id)
        if img is None:
            self._canvas.create_text(
                _CANVAS_W // 2, _CANVAS_H // 2,
                text="プレビューを生成できませんでした",
                font=(FONT_FAMILY, 13), fill="red"
            )
            return

        self._orig_img = img
        w, h = img.size
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        cw = cw if cw > 4 else _CANVAS_W
        ch = ch if ch > 4 else _CANVAS_H
        self._fit_scale = min(cw / w, ch / h, 1.0)
        self._zoom_idx = _FIT_IDX

        for btn in (self._btn_zout, self._btn_zin, self._btn_fit):
            btn.configure(state="normal")

        self._apply_zoom()

    # ── ズーム ────────────────────────────────────────────────────

    def _apply_zoom(self):
        if self._orig_img is None:
            return
        scale = self._fit_scale * _ZOOM_STEPS[self._zoom_idx]
        w = max(1, int(self._orig_img.width * scale))
        h = max(1, int(self._orig_img.height * scale))

        resized = self._orig_img.resize((w, h), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(resized)

        self._canvas.delete("img")
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img, tags="img")
        self._canvas.configure(scrollregion=(0, 0, w, h))

        step = _ZOOM_STEPS[self._zoom_idx]
        self._zoom_lbl.configure(
            text="フィット" if step == 1.0 else f"{int(step * 100)}%"
        )
        self._btn_zout.configure(
            state="normal" if self._zoom_idx > 0 else "disabled"
        )
        self._btn_zin.configure(
            state="normal" if self._zoom_idx < len(_ZOOM_STEPS) - 1 else "disabled"
        )

    def _zoom_in(self):
        if self._zoom_idx < len(_ZOOM_STEPS) - 1:
            self._zoom_idx += 1
            self._apply_zoom()

    def _zoom_out(self):
        if self._zoom_idx > 0:
            self._zoom_idx -= 1
            self._apply_zoom()

    def _zoom_fit(self):
        self._zoom_idx = _FIT_IDX
        self._apply_zoom()

    # ── ドラッグパン ──────────────────────────────────────────────

    def _drag_start(self, event):
        self._canvas.scan_mark(event.x, event.y)

    def _drag_move(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)

    # ── マウスホイールズーム ──────────────────────────────────────

    def _on_wheel(self, event):
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()
