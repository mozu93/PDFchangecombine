"""ページ編集コアロジックのテスト"""

import pytest

from src.core.page_editor import (
    PageRef,
    delete_pages,
    insert_refs,
    move_pages,
    move_pages_backward,
    move_pages_forward,
    reorder_pages,
)


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
