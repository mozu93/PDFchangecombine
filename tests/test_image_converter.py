"""
画像変換モジュール（ImageConverter）のテスト
実画像・実PDFを用いたエンドツーエンド検証（モックに頼らない実処理確認）
"""

import sys
from pathlib import Path

import pytest
from PIL import Image
import fitz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.image_converter import ImageConverter


def _make_image(path: Path, size=(200, 100), mode="RGB", color=(255, 0, 0)):
    img = Image.new(mode, size, color)
    img.save(path)
    return path


class TestIsSupportedFormat:
    def test_supported_extensions(self):
        converter = ImageConverter()
        for ext in ["jpg", "jpeg", "png", "bmp", "gif", "tiff"]:
            assert converter.is_supported_format(f"photo.{ext}") is True

    def test_unsupported_extension(self):
        converter = ImageConverter()
        assert converter.is_supported_format("document.docx") is False

    def test_case_insensitive(self):
        converter = ImageConverter()
        assert converter.is_supported_format("PHOTO.PNG") is True


class TestConvertToPdfEndToEnd:
    def test_rgb_png_converts_to_valid_pdf(self, tmp_path):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.pdf"

        converter = ImageConverter()
        assert converter.convert_to_pdf(str(src), str(out)) is True
        assert out.exists()

        doc = fitz.open(str(out))
        try:
            assert doc.page_count == 1
        finally:
            doc.close()

    def test_rgba_png_converts_without_error(self, tmp_path):
        src = _make_image(tmp_path / "in_rgba.png", mode="RGBA", color=(0, 255, 0, 128))
        out = tmp_path / "out_rgba.pdf"

        converter = ImageConverter()
        assert converter.convert_to_pdf(str(src), str(out)) is True
        assert out.exists()

    def test_palette_mode_converts_without_error(self, tmp_path):
        src_rgb = tmp_path / "in_p.png"
        Image.new("RGB", (100, 100), (10, 20, 30)).convert("P").save(src_rgb)
        out = tmp_path / "out_p.pdf"

        converter = ImageConverter()
        assert converter.convert_to_pdf(str(src_rgb), str(out)) is True

    def test_unsupported_extension_returns_false(self, tmp_path):
        fake = tmp_path / "not_an_image.txt"
        fake.write_text("hello")
        out = tmp_path / "out.pdf"

        converter = ImageConverter()
        assert converter.convert_to_pdf(str(fake), str(out)) is False
        assert not out.exists()

    def test_missing_source_file_returns_false(self, tmp_path):
        missing = tmp_path / "missing.png"
        out = tmp_path / "out.pdf"

        converter = ImageConverter()
        assert converter.convert_to_pdf(str(missing), str(out)) is False


class TestConvertMultipleImagesToPdf:
    def test_produces_one_page_per_image(self, tmp_path):
        images = [
            _make_image(tmp_path / "a.png", color=(255, 0, 0)),
            _make_image(tmp_path / "b.png", color=(0, 255, 0)),
            _make_image(tmp_path / "c.png", color=(0, 0, 255)),
        ]
        out = tmp_path / "combined.pdf"

        converter = ImageConverter()
        assert converter.convert_multiple_images_to_pdf([str(p) for p in images], str(out)) is True

        doc = fitz.open(str(out))
        try:
            assert doc.page_count == 3
        finally:
            doc.close()

    def test_empty_list_still_produces_pdf_file(self, tmp_path):
        out = tmp_path / "empty.pdf"
        converter = ImageConverter()
        assert converter.convert_multiple_images_to_pdf([], str(out)) is True
        assert out.exists()


class TestGetImageInfo:
    def test_returns_dimensions_for_valid_image(self, tmp_path):
        src = _make_image(tmp_path / "info.png", size=(150, 80))
        converter = ImageConverter()

        info = converter.get_image_info(str(src))
        assert info["width"] == 150
        assert info["height"] == 80
        assert info["size"] == (150, 80)
        assert info["mode"] == "RGB"

    def test_returns_empty_dict_for_invalid_file(self, tmp_path):
        bogus = tmp_path / "bogus.png"
        bogus.write_bytes(b"not a real image")

        converter = ImageConverter()
        assert converter.get_image_info(str(bogus)) == {}

    def test_returns_empty_dict_for_missing_file(self, tmp_path):
        converter = ImageConverter()
        assert converter.get_image_info(str(tmp_path / "nope.png")) == {}
