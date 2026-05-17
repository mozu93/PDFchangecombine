"""
PDFプレビューダイアログ - 資料番号・ページ番号の挿入位置をプレビュー
"""

import threading
from pathlib import Path
from typing import Callable, Optional

import fitz
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from .theme import FONT_FAMILY, CLR_PRIMARY, CLR_ACCENT

_RENDER_SCALE = 1.5
_MAX_W = 740
_MAX_H = 540


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


def _fit(img: Image.Image) -> Image.Image:
    w, h = img.size
    ratio = min(_MAX_W / w, _MAX_H / h, 1.0)
    if ratio < 1.0:
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    return img


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
) -> Optional[Image.Image]:
    """資料番号挿入位置のプレビュー画像を生成する"""
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
        else:  # 270 or other
            x = pw - margin - font_size
            y = ph - margin - tw

        font = _load_jp_font(int(font_size * _RENDER_SCALE))
        hi  = (220, 50, 50, 160)
        col = (180, 0, 0, 255)

        if rotate_text:
            _paste_rotated_text(img, document_text, font, x, y, tw, font_size, hi, col)
        else:
            _paste_normal_text(img, document_text, font, x, y, tw, font_size, hi, col)

        return _fit(img.convert("RGB"))
    except Exception:
        return None


# ─── ページ番号プレビュー ─────────────────────────────────────────


def render_page_number_preview(
    pdf_path: str,
    page_number_text: str,
    binding_compat: bool,
) -> Optional[Image.Image]:
    """ページ番号挿入位置のプレビュー画像を生成する"""
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
                # A3横 Z折り: 左半分の中央下
                x = (pw / 2 - tw) / 2
                y = ph - margin - font_size
            elif binding_compat and is_lb:
                # A4横・A3縦 左綴じ: 左端中央、90°CW 回転
                x = margin
                y = (ph - tw) / 2
                rotate_text = True
            else:
                # 通常: 下部中央
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

        return _fit(img.convert("RGB"))
    except Exception:
        return None


# ─── ダイアログ ──────────────────────────────────────────────────


class PDFPreviewDialog(ctk.CTkToplevel):
    """PDF 挿入位置プレビューダイアログ"""

    def __init__(self, parent, title: str,
                 render_fn: Callable[[], Optional[Image.Image]]):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._frame = ctk.CTkFrame(self, fg_color="transparent")
        self._frame.pack(padx=12, pady=(12, 0), fill="both", expand=True)

        self._loading = ctk.CTkLabel(
            self._frame,
            text="プレビューを生成中...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14)
        )
        self._loading.pack(padx=80, pady=60)

        ctk.CTkButton(
            self, text="閉じる", width=100,
            fg_color=CLR_PRIMARY, hover_color=CLR_ACCENT,
            command=self.destroy
        ).pack(pady=10)

        # ウィンドウを親の中央付近に配置
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 800) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self._ctk_img = None
        threading.Thread(target=self._render, args=(render_fn,), daemon=True).start()

    def _render(self, fn: Callable):
        img = fn()
        self.after(0, lambda: self._display(img))

    def _display(self, img: Optional[Image.Image]) -> None:
        self._loading.pack_forget()
        if img is None:
            ctk.CTkLabel(
                self._frame,
                text="プレビューを生成できませんでした",
                text_color="red",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13)
            ).pack(padx=40, pady=30)
            return
        self._ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        ctk.CTkLabel(self._frame, image=self._ctk_img, text="").pack()
