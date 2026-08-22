"""
ページ単位の編集ロジック（削除・並べ替え・抽出・挿入）

実PDFのバイト列は保存・抽出のときにだけ書き出し、編集中は
「どのドキュメントの何ページ目か」を指す PageRef のリストだけを操作する。
"""

from dataclasses import dataclass
from typing import List, Set

from ..utils.logger import logger


class PageEditError(Exception):
    """ページ編集で発生した業務エラー（GUI層で警告表示して操作を中止する）"""


@dataclass(frozen=True)
class PageRef:
    """編集中の1ページを指す参照。

    doc_id は PageEditSession が採番するセッション内の識別子で、
    fitz.Document そのものは持たない（クローズ管理を一元化するため）。
    """

    doc_id: int
    page_index: int


class PageEditResult:
    """保存・抽出の結果を保持するクラス（CombineResult と同じ形に揃える）"""

    def __init__(self, output_path: str = "", success: bool = False,
                 error_message: str = "", total_pages: int = 0):
        self.output_path = output_path
        self.success = success
        self.error_message = error_message
        self.total_pages = total_pages


# ── 並び操作の純粋関数（fitz に触れないためGUI・PDF抜きでテストできる） ──


def _validate_indices(pages: List[PageRef], indices: Set[int]) -> None:
    for i in indices:
        if not 0 <= i < len(pages):
            raise ValueError(f"ページインデックスが範囲外です: {i}（全{len(pages)}ページ）")


def delete_pages(pages: List[PageRef], indices: Set[int]) -> List[PageRef]:
    """指定インデックスを除いた新しい並びを返す"""
    _validate_indices(pages, indices)
    return [ref for i, ref in enumerate(pages) if i not in indices]


def reorder_pages(pages: List[PageRef], new_order: List[int]) -> List[PageRef]:
    """並べ替え結果を返す。

    new_order は「新しい並び順に、元リストのインデックスを並べたもの」。
    例: [2, 0, 1] は「元の3番目→1番目、元の1番目→2番目、元の2番目→3番目」。
    元リストの全インデックスをちょうど1回ずつ含んでいる必要がある。
    """
    if sorted(new_order) != list(range(len(pages))):
        raise ValueError(
            f"new_order は 0〜{len(pages) - 1} を1回ずつ含む必要があります: {new_order}"
        )
    return [pages[i] for i in new_order]


def move_pages(pages: List[PageRef], indices: Set[int], target_index: int) -> List[PageRef]:
    """選択ページ群を target_index の位置へまとめて移動する。

    target_index は「選択ページを取り除いた残りのリスト」における挿入位置
    （0始まり、残りの長さと同じ値で末尾）。選択の相対順序は維持される。
    """
    _validate_indices(pages, indices)
    moving = [ref for i, ref in enumerate(pages) if i in indices]
    rest = [ref for i, ref in enumerate(pages) if i not in indices]
    if not 0 <= target_index <= len(rest):
        raise ValueError(
            f"移動先が範囲外です: {target_index}（0〜{len(rest)}）"
        )
    return rest[:target_index] + moving + rest[target_index:]


def _reduced_position(pages: List[PageRef], indices: Set[int]) -> int:
    """選択ページを取り除いた残りのリストにおける、選択ブロックの現在位置"""
    return sum(1 for i in range(min(indices)) if i not in indices)


def move_pages_backward(pages: List[PageRef], indices: Set[int]) -> List[PageRef]:
    """選択ページを1つ手前へ移動する（◀ 前へ）"""
    if not indices:
        return list(pages)
    _validate_indices(pages, indices)
    target = max(0, _reduced_position(pages, indices) - 1)
    return move_pages(pages, indices, target)


def move_pages_forward(pages: List[PageRef], indices: Set[int]) -> List[PageRef]:
    """選択ページを1つ後ろへ移動する（次へ ▶）"""
    if not indices:
        return list(pages)
    _validate_indices(pages, indices)
    rest_len = len(pages) - len(indices)
    target = min(rest_len, _reduced_position(pages, indices) + 1)
    return move_pages(pages, indices, target)


def insert_refs(pages: List[PageRef], after_index: int,
                new_refs: List[PageRef]) -> List[PageRef]:
    """after_index の直後に new_refs を挿入した新しい並びを返す。

    after_index = -1 は「先頭に挿入」を意味する。
    """
    if not -1 <= after_index < len(pages):
        raise ValueError(
            f"挿入位置が範囲外です: {after_index}（-1〜{len(pages) - 1}）"
        )
    at = after_index + 1
    return list(pages[:at]) + list(new_refs) + list(pages[at:])
