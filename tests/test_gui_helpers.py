"""
テーマとGUIヘルパーのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


class TestDraggableFileListSort:
    """DraggableFileList.sort_by_filename のテスト（GUIなし）"""

    def test_sort_by_filename_alphabetical(self):
        """ファイル名のアルファベット順に並び替わる"""
        from pathlib import Path
        from src.gui.draggable_list import DraggableFileList

        dl = object.__new__(DraggableFileList)
        dl.file_paths = [
            "/path/to/c_file.pdf",
            "/path/to/a_file.pdf",
            "/path/to/b_file.pdf",
        ]
        dl.items = {}
        dl.on_order_change = None

        dl.sort_by_filename()

        names = [Path(p).name for p in dl.file_paths]
        assert names == ["a_file.pdf", "b_file.pdf", "c_file.pdf"]

    def test_sort_by_filename_numeric_order(self):
        """数字を含むファイル名が数値順（自然順）に並ぶ"""
        from pathlib import Path
        from src.gui.draggable_list import DraggableFileList

        dl = object.__new__(DraggableFileList)
        dl.file_paths = [
            "/path/to/file_10.pdf",
            "/path/to/file_2.pdf",
            "/path/to/file_1.pdf",
        ]
        dl.items = {}
        dl.on_order_change = None

        dl.sort_by_filename()

        names = [Path(p).name for p in dl.file_paths]
        assert names == ["file_1.pdf", "file_2.pdf", "file_10.pdf"]

    def test_sort_by_filename_empty_list(self):
        """空リストでも例外が発生しない"""
        from src.gui.draggable_list import DraggableFileList

        dl = object.__new__(DraggableFileList)
        dl.file_paths = []
        dl.items = {}
        dl.on_order_change = None

        dl.sort_by_filename()

        assert dl.file_paths == []
