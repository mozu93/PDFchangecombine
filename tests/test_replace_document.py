"""
結合済みPDFへの構成情報埋め込み・資料差し替え機能のテスト
（差し替え機能: PDF本体に埋め込んだ構成情報でリネーム・移動後も差し替え可能にする）
"""

import shutil
import sys
from pathlib import Path

import fitz
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.combiner import PDFCombiner


def _make_pdf(path: Path, n_pages: int, width: float = 595, height: float = 842) -> Path:
    doc = fitz.open()
    for _ in range(n_pages):
        doc.new_page(width=width, height=height)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def combiner():
    return PDFCombiner()


@pytest.fixture
def three_docs(tmp_path):
    """資料1(2p) / 資料2(2p) / 資料3(2p) の3ファイル"""
    return [
        _make_pdf(tmp_path / "a.pdf", 2),
        _make_pdf(tmp_path / "b.pdf", 2),
        _make_pdf(tmp_path / "c.pdf", 2),
    ]


def _metadata(paths):
    labels = ["資料1", "資料2", "資料3"]
    return {str(p): {"document_number": labels[i]} for i, p in enumerate(paths)}


class TestManifestEmbedding:
    def test_combine_embeds_readable_manifest(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        result = combiner.combine_pdfs(
            [str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs)
        )
        assert result.success is True

        manifest_result = combiner.load_combine_manifest(str(out))
        assert manifest_result.success is True
        docs = manifest_result.manifest["documents"]
        assert [d["document_number"] for d in docs] == ["資料1", "資料2", "資料3"]
        assert [d["page_start"] for d in docs] == [1, 3, 5]
        assert [d["page_end"] for d in docs] == [2, 4, 6]

    def test_manifest_survives_rename_and_move(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        moved_dir = tmp_path / "moved" / "elsewhere"
        moved_dir.mkdir(parents=True)
        renamed = moved_dir / "提出用_20260725.pdf"
        shutil.move(str(out), str(renamed))

        manifest_result = combiner.load_combine_manifest(str(renamed))
        assert manifest_result.success is True
        assert len(manifest_result.manifest["documents"]) == 3

    def test_pdf_without_manifest_fails_gracefully(self, combiner, tmp_path):
        plain = _make_pdf(tmp_path / "plain.pdf", 2)
        result = combiner.load_combine_manifest(str(plain))
        assert result.success is False
        assert "構成情報" in result.error_message

    def test_page_count_mismatch_detected(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        # 本アプリ以外での編集を想定し、埋め込み情報と矛盾する状態を作る
        with fitz.open(str(out)) as doc:
            doc.delete_page(0)
            tampered = tmp_path / "tampered.pdf"
            doc.save(str(tampered))

        result = combiner.load_combine_manifest(str(tampered))
        assert result.success is False
        assert "一致しない" in result.error_message


class TestReplaceDocumentSamePageCount:
    def test_replaces_target_pages_only(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 2)
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))

        assert result.success is True
        assert result.total_pages == 6

        manifest_result = combiner.load_combine_manifest(str(out2))
        docs = manifest_result.manifest["documents"]
        assert docs[1]["source_filename"] == "b_v2.pdf"
        # ページ数が変わらないので、後続資料の範囲は変化しない
        assert docs[2]["page_start"] == 5
        assert docs[2]["page_end"] == 6

    def test_page_numbers_unaffected_when_count_unchanged(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs(
            [str(p) for p in three_docs], str(out),
            add_page_numbers=True, start_page=1, start_number=1,
            document_metadata=_metadata(three_docs),
        )

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 2)
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))
        assert result.success is True

        with fitz.open(str(out2)) as doc:
            texts = [doc[i].get_text().strip() for i in range(len(doc))]
        assert texts == ["1", "2", "3", "4", "5", "6"]


class TestReplaceDocumentPageCountChanges:
    def test_subsequent_ranges_shift_when_pages_increase(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 4)  # 2p -> 4p
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))

        assert result.success is True
        assert result.total_pages == 8

        docs = combiner.load_combine_manifest(str(out2)).manifest["documents"]
        assert docs[0]["page_start"] == 1 and docs[0]["page_end"] == 2   # 資料1は不変
        assert docs[1]["page_start"] == 3 and docs[1]["page_end"] == 6   # 資料2が拡大
        assert docs[2]["page_start"] == 7 and docs[2]["page_end"] == 8   # 資料3が後ろへシフト

    def test_page_number_footer_cascades_when_pages_increase(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs(
            [str(p) for p in three_docs], str(out),
            add_page_numbers=True, start_page=1, start_number=1,
            document_metadata=_metadata(three_docs),
        )

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 4)
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))
        assert result.success is True

        with fitz.open(str(out2)) as doc:
            texts = [doc[i].get_text().strip() for i in range(len(doc))]
        # 資料3(旧ページ5,6)が旧番号のまま残らず、7,8に振り直されていること
        assert texts == ["1", "2", "3", "4", "5", "6", "7", "8"]

    def test_subsequent_ranges_shift_when_pages_decrease(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs(
            [str(p) for p in three_docs], str(out),
            add_page_numbers=True, start_page=1, start_number=1,
            document_metadata=_metadata(three_docs),
        )

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 1)  # 2p -> 1p
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))

        assert result.success is True
        assert result.total_pages == 5

        with fitz.open(str(out2)) as doc:
            texts = [doc[i].get_text().strip() for i in range(len(doc))]
        assert texts == ["1", "2", "3", "4", "5"]


class TestReplaceDocumentErrorHandling:
    def test_unknown_document_number_returns_error(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        replacement = _make_pdf(tmp_path / "x.pdf", 1)
        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out), "資料99", str(replacement), str(out2))

        assert result.success is False
        assert "見つかりません" in result.error_message

    def test_missing_replacement_file_returns_error(self, combiner, three_docs, tmp_path):
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))

        out2 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(
            str(out), "資料2", str(tmp_path / "missing.pdf"), str(out2)
        )
        assert result.success is False

    def test_replace_without_manifest_returns_error(self, combiner, tmp_path):
        plain = _make_pdf(tmp_path / "plain.pdf", 2)
        replacement = _make_pdf(tmp_path / "x.pdf", 1)
        out2 = tmp_path / "replaced.pdf"

        result = combiner.replace_document_in_combined_pdf(str(plain), "資料1", str(replacement), str(out2))
        assert result.success is False
        assert "構成情報" in result.error_message

    def test_original_combined_pdf_untouched(self, combiner, three_docs, tmp_path):
        """差し替えは非破壊（新規ファイル出力）であること"""
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs([str(p) for p in three_docs], str(out), document_metadata=_metadata(three_docs))
        original_bytes = out.read_bytes()

        replacement = _make_pdf(tmp_path / "b_v2.pdf", 4)
        out2 = tmp_path / "replaced.pdf"
        combiner.replace_document_in_combined_pdf(str(out), "資料2", str(replacement), str(out2))

        assert out.read_bytes() == original_bytes


class TestDocumentMetadataPopulation:
    """資料NO挿入結果からcombine_pdfsへ渡すdocument_metadataが正しく組み立てられること

    (GUI側は _on_document_number_complete でこのresult.document_metadataをそのまま
    _send_files_to_combination_tab 経由でcombine_pdfsへ渡す)
    """

    def test_sequential_numbering_populates_metadata_per_file(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)
        b = _make_pdf(tmp_path / "b.pdf", 1)

        result = combiner.add_sequential_document_numbers(
            pdf_paths=[str(a), str(b)], output_dir=str(tmp_path),
            numbering_type="basic", document_prefix="資料",
        )
        assert result.success is True
        assert len(result.document_metadata) == 2

        labels = {meta["document_number"] for meta in result.document_metadata.values()}
        assert labels == {"資料1", "資料2"}

        for new_path in result.processed_files:
            meta = result.document_metadata[new_path]
            assert meta["stamp_settings"]["document_prefix"] == "資料"
            assert meta["stamp_settings"]["number_part"] in {"1", "2"}

    def test_fixed_number_populates_metadata(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)

        result = combiner.add_document_numbers(
            pdf_paths=[str(a)], output_path="",
            document_number="5", document_prefix="資料",
            output_dir=str(tmp_path),
        )
        assert result.success is True
        assert len(result.document_metadata) == 1

        new_path = result.processed_files[0]
        meta = result.document_metadata[new_path]
        assert meta["document_number"] == "資料5"
        assert meta["stamp_settings"]["number_part"] == "5"

    def test_metadata_flows_into_combine_manifest(self, combiner, tmp_path):
        """資料NO挿入 → 結合 の一連の流れで、構成情報が正しく埋め込まれること"""
        a = _make_pdf(tmp_path / "a.pdf", 1)
        b = _make_pdf(tmp_path / "b.pdf", 1)

        numbering_result = combiner.add_sequential_document_numbers(
            pdf_paths=[str(a), str(b)], output_dir=str(tmp_path),
            numbering_type="basic", document_prefix="資料",
        )
        assert numbering_result.success is True

        out = tmp_path / "combined.pdf"
        combine_result = combiner.combine_pdfs(
            numbering_result.processed_files, str(out),
            document_metadata=numbering_result.document_metadata,
        )
        assert combine_result.success is True

        manifest_result = combiner.load_combine_manifest(str(out))
        assert manifest_result.success is True
        labels = [d["document_number"] for d in manifest_result.manifest["documents"]]
        assert labels == ["資料1", "資料2"]
