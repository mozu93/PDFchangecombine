"""サムネイルグリッドのGUI非依存部分のテスト"""

import fitz
import pytest

from src.gui.page_thumbnail_grid import (
    CELL_WIDTH,
    THUMBNAIL_WIDTH,
    calc_columns,
    render_thumbnail,
)


class TestCalcColumns:
    def test_グリッド幅から列数を求める(self):
        assert calc_columns(520, cell_width=126) == 4
        assert calc_columns(680, cell_width=126) == 5
        assert calc_columns(1170, cell_width=126) == 9

    def test_幅が足りなくても最低1列は返す(self):
        assert calc_columns(50, cell_width=126) == 1
        assert calc_columns(0, cell_width=126) == 1
        assert calc_columns(-100, cell_width=126) == 1

    def test_最低列数を指定できる(self):
        assert calc_columns(50, cell_width=126, min_columns=2) == 2

    def test_既定のセル幅はサムネイル幅より広い(self):
        # ラベル・余白ぶんの余裕があること
        assert CELL_WIDTH > THUMBNAIL_WIDTH


class TestRenderThumbnail:
    @pytest.fixture
    def a4_page(self):
        doc = fitz.open()
        doc.new_page(width=595, height=842)  # A4縦
        yield doc[0]
        doc.close()

    def test_指定幅の画像を返す(self, a4_page):
        img = render_thumbnail(a4_page, width=110)
        assert img.width == 110

    def test_縦横比が保たれる(self, a4_page):
        img = render_thumbnail(a4_page, width=110)
        # A4縦の比率は約1.414
        assert 1.40 < img.height / img.width < 1.43

    def test_横向きページでも指定幅になる(self):
        doc = fitz.open()
        doc.new_page(width=842, height=595)  # A4横
        img = render_thumbnail(doc[0], width=110)
        doc.close()
        assert img.width == 110
        assert img.height < img.width
