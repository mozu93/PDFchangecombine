"""
ページ単位の編集ロジック（削除・並べ替え・抽出・挿入）

実PDFのバイト列は保存・抽出のときにだけ書き出し、編集中は
「どのドキュメントの何ページ目か」を指す PageRef のリストだけを操作する。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import fitz

from ..utils.logger import logger
from ..utils.security import SecurityValidator


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


class PageEditSession:
    """1つのメインPDFに対する編集セッション。

    fitz.Document をここで一元所有し、PageRef には doc_id しか持たせない。
    これによりクローズ管理・取り消し履歴・テストがすべて単純になる。
    """

    MAX_HISTORY = 20

    def __init__(self) -> None:
        self._docs: Dict[int, fitz.Document] = {}
        self._paths: Dict[int, str] = {}
        self._next_doc_id: int = 1
        self._pages: List[PageRef] = []
        self._initial_pages: List[PageRef] = []
        self._history: List[List[PageRef]] = []

    # ── 状態参照 ──

    @property
    def pages(self) -> List[PageRef]:
        """現在の並び（呼び出し元が壊さないようコピーを返す）"""
        return list(self._pages)

    @property
    def main_path(self) -> str:
        """メインPDFのパス（未読み込みなら空文字）"""
        return self._paths.get(1, "") if self._docs else ""

    def source_path(self, ref: PageRef) -> str:
        """PageRef の取得元ファイルパスを返す"""
        return self._paths.get(ref.doc_id, "")

    def get_page(self, ref: PageRef) -> fitz.Page:
        """サムネイル描画用に fitz.Page を返す。

        注意: 戻り値は Document に紐づくため、必ずワーカースレッド上で
        使い切ること（PageEditWorker 経由で呼ぶ）。
        """
        doc = self._docs.get(ref.doc_id)
        if doc is None:
            raise PageEditError("編集セッションが閉じられています")
        return doc[ref.page_index]

    # ── 読み込み ──

    def _open_document(self, path: str) -> int:
        """PDFを開いて doc_id を採番する。

        ファイルをロックしないよう、パスではなくバイト列から開く。
        （fitz.open(path) は Windows でハンドルを保持し続けるため使わない）
        """
        if not SecurityValidator.validate_file_path(path):
            raise PageEditError(f"読み込めないファイルです: {Path(path).name}")

        try:
            raw = Path(path).read_bytes()
            doc = fitz.open(stream=raw, filetype="pdf")
        except Exception as e:
            logger.warning(f"PDFの読み込みに失敗: {path}: {e}")
            raise PageEditError(
                f"PDFを開けませんでした: {Path(path).name}"
            ) from e

        # 暗号化PDFは fitz.open() が例外を投げない（needs_pass が立つだけ）ため
        # ここで明示的に弾く
        if doc.needs_pass:
            doc.close()
            raise PageEditError(
                f"パスワードで保護されたPDFは開けません: {Path(path).name}"
            )

        if doc.page_count == 0:
            doc.close()
            raise PageEditError(f"ページがありません: {Path(path).name}")

        doc_id = self._next_doc_id
        self._next_doc_id += 1
        self._docs[doc_id] = doc
        self._paths[doc_id] = path
        return doc_id

    def load(self, path: str) -> None:
        """メインPDFを読み込む。既存セッションがあれば先に破棄する"""
        self.close()
        doc_id = self._open_document(path)
        self._pages = [PageRef(doc_id, i) for i in range(self._docs[doc_id].page_count)]
        self._initial_pages = list(self._pages)
        self._history = []
        logger.info(f"ページ編集: 読み込み完了 {Path(path).name} ({len(self._pages)}ページ)")

    # ── 編集操作 ──

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def apply(self, new_pages: List[PageRef]) -> None:
        """純粋関数の結果を反映し、直前の状態を履歴に積む"""
        self._history.append(list(self._pages))
        if len(self._history) > self.MAX_HISTORY:
            self._history.pop(0)
        self._pages = list(new_pages)

    def undo(self) -> bool:
        """1手戻す。履歴が空なら False を返す"""
        if not self._history:
            return False
        self._pages = self._history.pop()
        return True

    def reset(self) -> None:
        """読み込み直後の並びへ全リセットする。

        ドキュメントは閉じないので、サムネイル画像をそのまま再利用できる。
        """
        self._pages = list(self._initial_pages)
        self._history = []

    def insert_from_file(self, after_index: int, insert_path: str) -> None:
        """指定PDFの全ページを after_index の直後に挿入する。

        after_index = -1 は先頭。失敗時は PageEditError を送出し、
        編集状態は一切変更しない。
        """
        if not -1 <= after_index < len(self._pages):
            raise PageEditError(f"挿入位置が不正です: {after_index}")

        # 位置検証を先に済ませてから開くことで、失敗時に doc を開きっぱなしにしない
        doc_id = self._open_document(insert_path)
        new_refs = [
            PageRef(doc_id, i) for i in range(self._docs[doc_id].page_count)
        ]
        self.apply(insert_refs(self._pages, after_index, new_refs))
        logger.info(
            f"ページ編集: {Path(insert_path).name} から{len(new_refs)}ページ挿入"
        )

    # ── 書き出し ──

    @staticmethod
    def _group_runs(pages: List[PageRef]) -> List[tuple]:
        """連続する同一doc・連番ページを (doc_id, from_page, to_page) にまとめる。

        1ページずつ insert_pdf すると遅いため、まとめて範囲指定で挿入する。
        """
        runs: List[tuple] = []
        for ref in pages:
            if runs and runs[-1][0] == ref.doc_id and runs[-1][2] + 1 == ref.page_index:
                doc_id, start, _ = runs[-1]
                runs[-1] = (doc_id, start, ref.page_index)
            else:
                runs.append((ref.doc_id, ref.page_index, ref.page_index))
        return runs

    def _write(self, pages: List[PageRef], output_path: str, label: str) -> PageEditResult:
        """指定した並びを新規PDFとして書き出す共通処理"""
        if not pages:
            return PageEditResult(
                success=False,
                error_message="出力するページがありません。",
            )

        writer: Optional[fitz.Document] = None
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            writer = fitz.open()
            for doc_id, from_page, to_page in self._group_runs(pages):
                src = self._docs.get(doc_id)
                if src is None:
                    raise PageEditError("編集セッションが閉じられています")
                writer.insert_pdf(src, from_page=from_page, to_page=to_page)
            writer.save(output_path)
            logger.info(f"ページ編集: {label}完了 {output_path} ({len(pages)}ページ)")
            return PageEditResult(
                output_path=output_path,
                success=True,
                total_pages=len(pages),
            )
        except Exception as e:
            logger.error(f"ページ編集: {label}に失敗: {e}", exc_info=True)
            return PageEditResult(
                success=False,
                error_message=f"{label}に失敗しました: {e}",
            )
        finally:
            if writer is not None:
                try:
                    writer.close()
                except Exception:
                    pass

    def save(self, output_path: str) -> PageEditResult:
        """現在の並びを1つの新規PDFとして書き出す。セッションは維持する"""
        return self._write(self._pages, output_path, "保存")

    def extract(self, indices: Set[int], output_path: str) -> PageEditResult:
        """選択ページのみを新規PDFとして書き出す。現在の並びは変更しない"""
        if not indices:
            return PageEditResult(
                success=False,
                error_message="抽出するページが選択されていません。",
            )
        if any(not 0 <= i < len(self._pages) for i in indices):
            return PageEditResult(
                success=False,
                error_message="選択されたページが範囲外です。",
            )
        selected = [self._pages[i] for i in sorted(indices)]
        return self._write(selected, output_path, "抽出")

    # ── 終了処理 ──

    def close(self) -> None:
        """開いている全ドキュメントを閉じ、状態をリセットする。

        呼ぶのは「新規読み込み直前」「アプリ終了」「タブのクリア」の3つだけ。
        保存後には呼ばない（保存後も編集を続けられるようにするため）。
        """
        for doc_id, doc in self._docs.items():
            try:
                doc.close()
            except Exception as e:
                logger.warning(f"ドキュメントのクローズに失敗 (doc_id={doc_id}): {e}")
        self._docs.clear()
        self._paths.clear()
        self._next_doc_id = 1
        self._pages = []
        self._initial_pages = []
        self._history = []
