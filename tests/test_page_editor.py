"""ページ編集コアロジックのテスト"""

from pathlib import Path
from typing import List

import fitz
import pytest

from src.core.page_editor import (
    PageEditError,
    PageEditSession,
    PageRef,
    delete_pages,
    insert_refs,
    move_pages,
    move_pages_backward,
    move_pages_forward,
    reorder_pages,
)


@pytest.fixture
def make_pdf(tmp_path):
    """指定ページ数のPDFを作り、そのパスを返すファクトリ。

    各ページに「<name> Page <n>」というテキストを入れるので、
    出力PDFの中身をテキストで検証できる。
    """
    def _make(name: str, page_count: int) -> str:
        doc = fitz.open()
        for i in range(page_count):
            page = doc.new_page()
            page.insert_text((72, 72), f"{name} Page {i + 1}", fontsize=24)
        path = tmp_path / f"{name}.pdf"
        doc.save(str(path))
        doc.close()
        return str(path)
    return _make


@pytest.fixture
def session():
    """テスト終了時に必ず close する PageEditSession。

    close し忘れると Windows で tmp_path の削除に失敗してテストが落ちる。
    """
    s = PageEditSession()
    yield s
    s.close()


def page_texts(pdf_path: str) -> List[str]:
    """PDFの各ページのテキストを返す（出力内容の検証用）"""
    with fitz.open(pdf_path) as doc:
        return [p.get_text().strip() for p in doc]


def refs(doc_id: int, count: int):
    """doc_id の 0..count-1 ページを指す PageRef のリスト"""
    return [PageRef(doc_id, i) for i in range(count)]


class TestPageRef:
    def test_値として比較できる(self):
        assert PageRef(1, 0) == PageRef(1, 0)
        assert PageRef(1, 0) != PageRef(1, 1)

    def test_ハッシュ可能でsetに入れられる(self):
        assert len({PageRef(1, 0), PageRef(1, 0), PageRef(1, 1)}) == 2


class TestDeletePages:
    def test_指定インデックスを除いた並びを返す(self):
        pages = refs(1, 5)
        assert delete_pages(pages, {1, 3}) == [
            PageRef(1, 0), PageRef(1, 2), PageRef(1, 4)
        ]

    def test_元のリストを変更しない(self):
        pages = refs(1, 3)
        delete_pages(pages, {0})
        assert pages == refs(1, 3)

    def test_空の指定なら同じ並びを返す(self):
        pages = refs(1, 3)
        assert delete_pages(pages, set()) == pages

    def test_全削除で空リストになる(self):
        pages = refs(1, 3)
        assert delete_pages(pages, {0, 1, 2}) == []

    def test_範囲外インデックスでValueError(self):
        pages = refs(1, 3)
        with pytest.raises(ValueError):
            delete_pages(pages, {3})
        with pytest.raises(ValueError):
            delete_pages(pages, {-1})


class TestReorderPages:
    def test_新しい並び順にインデックスを並べたものを受け取る(self):
        pages = refs(1, 3)
        # [2, 0, 1] = 「元の3番目・1番目・2番目」の順に並べ替える
        assert reorder_pages(pages, [2, 0, 1]) == [
            PageRef(1, 2), PageRef(1, 0), PageRef(1, 1)
        ]

    def test_元のリストを変更しない(self):
        pages = refs(1, 3)
        reorder_pages(pages, [2, 1, 0])
        assert pages == refs(1, 3)

    def test_インデックスが欠けていたらValueError(self):
        with pytest.raises(ValueError):
            reorder_pages(refs(1, 3), [0, 1])

    def test_インデックスが重複していたらValueError(self):
        with pytest.raises(ValueError):
            reorder_pages(refs(1, 3), [0, 0, 1])

    def test_範囲外インデックスでValueError(self):
        with pytest.raises(ValueError):
            reorder_pages(refs(1, 3), [0, 1, 3])


class TestMovePages:
    def test_選択ページを取り除いた残りのtarget位置へ挿入する(self):
        pages = refs(1, 5)
        # {2} を取り除くと [0,1,3,4]。その位置1へ挿入
        assert move_pages(pages, {2}, 1) == [
            PageRef(1, 0), PageRef(1, 2), PageRef(1, 1), PageRef(1, 3), PageRef(1, 4)
        ]

    def test_複数選択は相対順序を保ったまま移動する(self):
        pages = refs(1, 5)
        # {0,2} を取り除くと [1,3,4]。その位置2へ挿入
        assert move_pages(pages, {0, 2}, 2) == [
            PageRef(1, 1), PageRef(1, 3), PageRef(1, 0), PageRef(1, 2), PageRef(1, 4)
        ]

    def test_残りリストの長さと同じtargetは末尾へ挿入(self):
        pages = refs(1, 3)
        assert move_pages(pages, {0}, 2) == [
            PageRef(1, 1), PageRef(1, 2), PageRef(1, 0)
        ]

    def test_targetが範囲外ならValueError(self):
        with pytest.raises(ValueError):
            move_pages(refs(1, 3), {0}, 3)
        with pytest.raises(ValueError):
            move_pages(refs(1, 3), {0}, -1)


class TestMoveBackwardForward:
    def test_前へで1つ手前に移動する(self):
        pages = refs(1, 4)
        assert move_pages_backward(pages, {2}) == [
            PageRef(1, 0), PageRef(1, 2), PageRef(1, 1), PageRef(1, 3)
        ]

    def test_先頭にある選択は前へ移動しても変わらない(self):
        pages = refs(1, 3)
        assert move_pages_backward(pages, {0}) == pages

    def test_次へで1つ後ろに移動する(self):
        pages = refs(1, 4)
        assert move_pages_forward(pages, {1}) == [
            PageRef(1, 0), PageRef(1, 2), PageRef(1, 1), PageRef(1, 3)
        ]

    def test_末尾にある選択は次へ移動しても変わらない(self):
        pages = refs(1, 3)
        assert move_pages_forward(pages, {2}) == pages

    def test_連続した複数選択をまとめて前へ移動する(self):
        pages = refs(1, 4)
        assert move_pages_backward(pages, {1, 2}) == [
            PageRef(1, 1), PageRef(1, 2), PageRef(1, 0), PageRef(1, 3)
        ]

    def test_連続した複数選択をまとめて次へ移動する(self):
        pages = refs(1, 4)
        assert move_pages_forward(pages, {1, 2}) == [
            PageRef(1, 0), PageRef(1, 3), PageRef(1, 1), PageRef(1, 2)
        ]

    def test_空の選択は何もしない(self):
        pages = refs(1, 3)
        assert move_pages_backward(pages, set()) == pages
        assert move_pages_forward(pages, set()) == pages


class TestInsertRefs:
    def test_指定インデックスの直後に挿入する(self):
        pages = refs(1, 3)
        new = refs(2, 2)
        assert insert_refs(pages, 0, new) == [
            PageRef(1, 0), PageRef(2, 0), PageRef(2, 1), PageRef(1, 1), PageRef(1, 2)
        ]

    def test_after_indexがマイナス1なら先頭に挿入する(self):
        pages = refs(1, 2)
        new = refs(2, 1)
        assert insert_refs(pages, -1, new) == [
            PageRef(2, 0), PageRef(1, 0), PageRef(1, 1)
        ]

    def test_最終インデックス指定で末尾に挿入する(self):
        pages = refs(1, 2)
        new = refs(2, 1)
        assert insert_refs(pages, 1, new) == [
            PageRef(1, 0), PageRef(1, 1), PageRef(2, 0)
        ]

    def test_空リストへの挿入はafter_indexマイナス1で行える(self):
        assert insert_refs([], -1, refs(2, 2)) == refs(2, 2)

    def test_範囲外のafter_indexでValueError(self):
        with pytest.raises(ValueError):
            insert_refs(refs(1, 2), 2, refs(2, 1))
        with pytest.raises(ValueError):
            insert_refs(refs(1, 2), -2, refs(2, 1))


class TestSessionLoad:
    def test_読み込んだページ数と並びが正しい(self, session, make_pdf):
        path = make_pdf("main", 5)
        session.load(path)
        assert len(session.pages) == 5
        assert [r.page_index for r in session.pages] == [0, 1, 2, 3, 4]
        assert len({r.doc_id for r in session.pages}) == 1

    def test_元ファイルをロックしない(self, session, make_pdf, tmp_path):
        path = make_pdf("main", 3)
        session.load(path)
        # 開いたままでも元ファイルをリネーム・削除できること
        renamed = tmp_path / "renamed.pdf"
        Path(path).rename(renamed)
        renamed.unlink()
        assert not renamed.exists()

    def test_読み込み直後は元ファイルパスを引ける(self, session, make_pdf):
        path = make_pdf("main", 2)
        session.load(path)
        assert session.source_path(session.pages[0]) == path

    def test_ページオブジェクトを取得できる(self, session, make_pdf):
        path = make_pdf("main", 3)
        session.load(path)
        page = session.get_page(session.pages[1])
        assert "main Page 2" in page.get_text()

    def test_存在しないパスでPageEditError(self, session, tmp_path):
        with pytest.raises(PageEditError):
            session.load(str(tmp_path / "no_such_file.pdf"))

    def test_破損PDFでPageEditError(self, session, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"this is not a pdf")
        with pytest.raises(PageEditError):
            session.load(str(broken))

    def test_パスワード保護PDFでPageEditError(self, session, tmp_path):
        doc = fitz.open()
        doc.new_page()
        protected = tmp_path / "protected.pdf"
        doc.save(
            str(protected),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="secret",
            owner_pw="secret",
        )
        doc.close()
        with pytest.raises(PageEditError):
            session.load(str(protected))

    def test_再読み込みで前のセッションが破棄される(self, session, make_pdf):
        session.load(make_pdf("first", 5))
        session.load(make_pdf("second", 2))
        assert len(session.pages) == 2


class TestSessionClose:
    def test_closeでページが空になる(self, session, make_pdf):
        session.load(make_pdf("main", 3))
        session.close()
        assert session.pages == []

    def test_close済みセッションのcloseは安全(self, session, make_pdf):
        session.load(make_pdf("main", 3))
        session.close()
        session.close()  # 例外にならないこと

    def test_未読み込みでのcloseは安全(self, session):
        session.close()
        assert session.pages == []
