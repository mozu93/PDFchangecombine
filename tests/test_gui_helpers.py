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
