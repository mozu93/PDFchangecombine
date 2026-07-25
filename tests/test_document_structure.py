"""
結合済みPDFの構成変更機能（資料の追加・削除・一括再採番）のテスト

これらは replace_document_in_combined_pdf (同一資料の差し替え) と異なり、
資料の並び自体を変える操作。ラベルが変わる資料は、PDFに埋め込まれた
raw master（資料番号スタンプ前のマスター）から再スタンプすることで、
二重スタンプにならずに正しく再現できる。
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


def _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=True):
    """資料1(1p) / 資料2(1p) / 資料3(1p) をadd_sequential_document_numbers→combine_pdfsで作る"""
    a = _make_pdf(tmp_path / "a.pdf", 1)
    b = _make_pdf(tmp_path / "b.pdf", 1)
    c = _make_pdf(tmp_path / "c.pdf", 1)

    num_result = combiner.add_sequential_document_numbers(
        pdf_paths=[str(a), str(b), str(c)], output_dir=str(tmp_path),
        numbering_type="basic", document_prefix="資料",
    )
    assert num_result.success is True

    out = tmp_path / "combined.pdf"
    combine_result = combiner.combine_pdfs(
        num_result.processed_files, str(out),
        add_page_numbers=add_page_numbers, start_page=1, start_number=1,
        document_metadata=num_result.document_metadata,
    )
    assert combine_result.success is True
    return out


def _page_texts(pdf_path) -> list:
    with fitz.open(str(pdf_path)) as doc:
        return [doc[i].get_text().strip() for i in range(doc.page_count)]


def _page_footer_numbers(pdf_path) -> list:
    """各ページの最終行（ページ番号footer）だけを取り出す。

    資料番号スタンプがあるページは get_text() に「資料N\n<footer>」のように
    スタンプ文字列も含まれるため、footerだけを比較したい場合はこちらを使う。
    """
    with fitz.open(str(pdf_path)) as doc:
        result = []
        for i in range(doc.page_count):
            lines = doc[i].get_text().strip().splitlines()
            result.append(lines[-1] if lines else "")
        return result


class TestRawMasterEmbedding:
    def test_raw_master_has_no_stamps(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        with fitz.open(str(out)) as doc:
            assert "pdfcc_raw_master.pdf" in doc.embfile_names()
            raw_bytes = doc.embfile_get("pdfcc_raw_master.pdf")
        with fitz.open(stream=raw_bytes, filetype="pdf") as raw_doc:
            assert raw_doc.page_count == 3
            for i in range(raw_doc.page_count):
                assert raw_doc[i].get_text().strip() == ""

    def test_no_raw_master_when_nothing_stamped(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)
        b = _make_pdf(tmp_path / "b.pdf", 1)
        out = tmp_path / "combined.pdf"
        result = combiner.combine_pdfs([str(a), str(b)], str(out))
        assert result.success is True
        with fitz.open(str(out)) as doc:
            assert "pdfcc_raw_master.pdf" not in doc.embfile_names()


class TestDeleteDocument:
    def test_delete_removes_document_and_leaves_gap(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        out2 = tmp_path / "deleted.pdf"

        result = combiner.delete_document_from_combined_pdf(str(out), "資料2", str(out2))
        assert result.success is True
        assert result.total_pages == 2

        manifest = combiner.load_combine_manifest(str(out2)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料3"]  # 欠番のまま、自動リナンバリングしない

    def test_delete_renumbers_page_footer(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        out2 = tmp_path / "deleted.pdf"
        combiner.delete_document_from_combined_pdf(str(out), "資料2", str(out2))

        assert _page_footer_numbers(out2) == ["1", "2"]

    def test_cannot_delete_last_remaining_document(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)
        num_result = combiner.add_document_numbers(
            pdf_paths=[str(a)], output_path="", document_number="1",
            document_prefix="資料", output_dir=str(tmp_path),
        )
        out = tmp_path / "combined.pdf"
        combiner.combine_pdfs(num_result.processed_files, str(out), document_metadata=num_result.document_metadata)

        result = combiner.delete_document_from_combined_pdf(str(out), "資料1", str(tmp_path / "x.pdf"))
        assert result.success is False

    def test_delete_unknown_label_fails(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        result = combiner.delete_document_from_combined_pdf(str(out), "資料99", str(tmp_path / "x.pdf"))
        assert result.success is False

    def test_delete_survives_rename_and_move(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        moved_dir = tmp_path / "moved"
        moved_dir.mkdir()
        renamed = moved_dir / "提出用.pdf"
        shutil.move(str(out), str(renamed))

        result = combiner.delete_document_from_combined_pdf(str(renamed), "資料2", str(tmp_path / "out.pdf"))
        assert result.success is True


class TestInsertDocument:
    def test_insert_between_two_documents(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        new_file = _make_pdf(tmp_path / "new.pdf", 2)
        out2 = tmp_path / "inserted.pdf"

        stamp_settings = {
            "document_prefix": "資料", "number_part": "1.5", "font_display_name": None,
            "doc_font_size": 20, "white_background": False, "a3_portrait_compat": False,
            "insert_all_pages": False,
        }
        result = combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(out2),
            insert_after_document_number="資料1", document_number="資料1.5",
            stamp_settings=stamp_settings,
        )
        assert result.success is True
        assert result.total_pages == 5  # 3 + 2枚追加

        manifest = combiner.load_combine_manifest(str(out2)).manifest
        docs = manifest["documents"]
        # 元は資料1/資料2/資料3の3件なので、資料1の直後に挿入すると4件になる
        assert [d["document_number"] for d in docs] == ["資料1", "資料1.5", "資料2", "資料3"]
        assert docs[1]["page_start"] == 2 and docs[1]["page_end"] == 3
        assert docs[2]["page_start"] == 4 and docs[2]["page_end"] == 4

    def test_insert_at_start_when_no_anchor_given(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=False)
        new_file = _make_pdf(tmp_path / "new.pdf", 1)
        out2 = tmp_path / "inserted.pdf"

        result = combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(out2),
            insert_after_document_number=None, document_number="資料0",
            stamp_settings=None,
        )
        assert result.success is True
        manifest = combiner.load_combine_manifest(str(out2)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料0", "資料1", "資料2", "資料3"]
        assert manifest["documents"][0]["page_start"] == 1

    def test_insert_at_end(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        new_file = _make_pdf(tmp_path / "new.pdf", 1)
        out2 = tmp_path / "inserted.pdf"

        result = combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(out2),
            insert_after_document_number="資料3", document_number="資料4",
            stamp_settings=None,
        )
        assert result.success is True
        manifest = combiner.load_combine_manifest(str(out2)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2", "資料3", "資料4"]

    def test_insert_page_numbers_cascade(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)  # add_page_numbers=True
        new_file = _make_pdf(tmp_path / "new.pdf", 2)
        out2 = tmp_path / "inserted.pdf"

        combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(out2),
            insert_after_document_number="資料1", document_number="資料1.5",
            stamp_settings=None,
        )
        assert _page_footer_numbers(out2) == ["1", "2", "3", "4", "5"]

    def test_insert_unknown_anchor_fails(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        new_file = _make_pdf(tmp_path / "new.pdf", 1)
        result = combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(tmp_path / "x.pdf"),
            insert_after_document_number="資料99", document_number="資料4",
        )
        assert result.success is False


class TestRenumberDocuments:
    def test_renumber_closes_gap_after_delete(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        deleted = tmp_path / "deleted.pdf"
        combiner.delete_document_from_combined_pdf(str(out), "資料2", str(deleted))

        renumbered = tmp_path / "renumbered.pdf"
        result = combiner.renumber_documents_in_combined_pdf(
            str(deleted), str(renumbered), numbering_type="basic", document_prefix="資料"
        )
        assert result.success is True

        manifest = combiner.load_combine_manifest(str(renumbered)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2"]

    def test_renumber_relabels_inserted_document_without_double_stamp(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        new_file = _make_pdf(tmp_path / "new.pdf", 1)
        inserted = tmp_path / "inserted.pdf"
        stamp_settings = {
            "document_prefix": "資料", "number_part": "1.5", "font_display_name": None,
            "doc_font_size": 20, "white_background": False, "a3_portrait_compat": False,
            "insert_all_pages": False,
        }
        combiner.insert_document_into_combined_pdf(
            str(out), str(new_file), str(inserted),
            insert_after_document_number="資料1", document_number="資料1.5",
            stamp_settings=stamp_settings,
        )

        renumbered = tmp_path / "renumbered.pdf"
        result = combiner.renumber_documents_in_combined_pdf(
            str(inserted), str(renumbered), numbering_type="basic", document_prefix="資料"
        )
        assert result.success is True

        # 挿入前は資料1/資料1.5/資料2/資料3の4件 -> 連番で資料1〜4に振り直される
        manifest = combiner.load_combine_manifest(str(renumbered)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2", "資料3", "資料4"]

        # 再スタンプ後のページに、古いラベルの残骸が残っていない（二重スタンプでない）こと
        with fitz.open(str(renumbered)) as doc:
            page1_text = doc[1].get_text()
        assert "1.5" not in page1_text

    def test_renumber_hyphen_mode(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=False)
        renumbered = tmp_path / "renumbered.pdf"
        result = combiner.renumber_documents_in_combined_pdf(
            str(out), str(renumbered), numbering_type="hyphen",
            prefix_number="9", document_prefix="資料",
        )
        assert result.success is True
        manifest = combiner.load_combine_manifest(str(renumbered)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料9-1", "資料9-2", "資料9-3"]

    def test_renumber_skips_entries_with_unavailable_raw(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)
        b = _make_pdf(tmp_path / "b.pdf", 1)
        num_result = combiner.add_sequential_document_numbers(
            pdf_paths=[str(a), str(b)], output_dir=str(tmp_path),
            numbering_type="basic", document_prefix="資料",
        )
        assert num_result.success is True

        # bの元ファイルを削除し、raw counterpartを取得不能にする
        b.unlink()

        out = tmp_path / "combined.pdf"
        combine_result = combiner.combine_pdfs(
            num_result.processed_files, str(out), document_metadata=num_result.document_metadata,
        )
        assert combine_result.success is True

        manifest = combiner.load_combine_manifest(str(out)).manifest
        raw_flags = [d["raw_unavailable"] for d in manifest["documents"]]
        assert raw_flags == [False, True]

        renumbered = tmp_path / "renumbered.pdf"
        result = combiner.renumber_documents_in_combined_pdf(
            str(out), str(renumbered), numbering_type="basic", document_prefix="資料"
        )
        assert result.success is True
        assert "資料2" in result.error_message  # スキップ通知

        manifest2 = combiner.load_combine_manifest(str(renumbered)).manifest
        labels = [d["document_number"] for d in manifest2["documents"]]
        # aは再採番、bはraw不明のため元のラベル(資料2)のまま
        assert labels == ["資料1", "資料2"]

    def test_renumber_survives_rename_and_move(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        moved_dir = tmp_path / "moved"
        moved_dir.mkdir()
        renamed = moved_dir / "提出用.pdf"
        shutil.move(str(out), str(renamed))

        result = combiner.renumber_documents_in_combined_pdf(
            str(renamed), str(tmp_path / "out.pdf"), numbering_type="basic", document_prefix="資料"
        )
        assert result.success is True


class TestDocumentNumberSelfEmbedding:
    """資料NO挿入済みPDF単体に資料番号を埋め込み、セッションをまたいで
    結合しても「(番号なし)」にならないようにする機能のテスト。

    実務では「資料NO挿入 → そのまま結合」だけでなく、一度ファイルとして
    保存してから後日改めて結合タブへドラッグ＆ドロップするケースがあるため、
    document_metadataがなくても各PDFファイル自体から資料番号を復元できる
    必要がある。
    """

    def test_stamped_pdf_embeds_recoverable_document_number(self, combiner, tmp_path):
        src = _make_pdf(tmp_path / "src.pdf", 1)
        num_result = combiner.add_document_numbers(
            pdf_paths=[str(src)], output_path="", document_number="1",
            document_prefix="資料", output_dir=str(tmp_path),
        )
        assert num_result.success is True
        stamped_path = num_result.processed_files[0]

        stamp = combiner.read_embedded_document_stamp(stamped_path)
        assert stamp is not None
        assert stamp["document_number"] == "資料1"
        assert stamp["stamp_settings"]["number_part"] == "1"
        assert stamp["stamp_settings"]["document_prefix"] == "資料"

    def test_unstamped_pdf_has_no_embedded_document_stamp(self, combiner, tmp_path):
        src = _make_pdf(tmp_path / "plain.pdf", 1)
        assert combiner.read_embedded_document_stamp(str(src)) is None

    def test_combine_recovers_document_number_without_explicit_metadata(self, combiner, tmp_path):
        a = _make_pdf(tmp_path / "a.pdf", 1)
        b = _make_pdf(tmp_path / "b.pdf", 1)
        num_result = combiner.add_sequential_document_numbers(
            pdf_paths=[str(a), str(b)], output_dir=str(tmp_path),
            numbering_type="basic", document_prefix="資料",
        )
        assert num_result.success is True

        # 資料NOタブ→結合タブの自動連携（document_metadata）を使わず、
        # 手動でファイルを選び直したケースを再現する。
        out = tmp_path / "combined.pdf"
        combine_result = combiner.combine_pdfs(num_result.processed_files, str(out))
        assert combine_result.success is True

        manifest = combiner.load_combine_manifest(str(out)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2"]


class TestReCombineAlreadyCombinedPdf:
    """「ページ番号」タブ（結合とは別のタブ）で、結合済みPDFに後からページ番号を
    付ける操作は、内部的にcombine_pdfs([結合済みPDF], ...)を呼んでいる。

    この結合済みPDF自体が既に資料1/資料2/資料3という構成情報を持っている場合、
    それを1個の「番号なし」資料として扱ってしまうと、以後の資料差し替えで
    対象PDF全体（他の資料も含めて）が丸ごと入れ替わってしまう。
    元の資料構成を維持したまま展開されるべき。
    """

    def test_combining_already_combined_pdf_preserves_document_boundaries(self, combiner, tmp_path):
        out1 = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=False)

        # 「ページ番号」タブが行うのと同じ呼び出し（結合済みPDF1個をcombine_pdfsに渡す）
        out2 = tmp_path / "with_pn.pdf"
        result = combiner.combine_pdfs(
            [str(out1)], str(out2), add_page_numbers=True, start_page=1, start_number=1,
        )
        assert result.success is True
        assert _page_footer_numbers(out2) == ["1", "2", "3"]

        manifest = combiner.load_combine_manifest(str(out2)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2", "資料3"]

    def test_replace_after_pagenumber_tab_only_affects_target_document(self, combiner, tmp_path):
        out1 = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=False)
        out2 = tmp_path / "with_pn.pdf"
        combiner.combine_pdfs([str(out1)], str(out2), add_page_numbers=True, start_page=1, start_number=1)

        new_file = _make_pdf(tmp_path / "new.pdf", 1)
        out3 = tmp_path / "replaced.pdf"
        result = combiner.replace_document_in_combined_pdf(str(out2), "資料2", str(new_file), str(out3))
        assert result.success is True

        manifest = combiner.load_combine_manifest(str(out3)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        # 資料1・資料3はそのまま残り、資料2だけが差し替わる
        assert labels == ["資料1", "資料2", "資料3"]
        assert _page_footer_numbers(out3) == ["1", "2", "3"]


class TestApplyDocumentOperations:
    """資料の追加・差し替え・削除を「操作の一覧」としてまとめて渡し、
    1回の実行で1つの出力ファイルだけを作る機能のテスト。

    従来は差し替えダイアログで操作するたびに毎回新しいファイルが
    作られていた（資料2に追加→ファイル作成、続けて資料1を差し替え→
    別のファイル作成）ため、中間ファイルが増えて分かりにくいという
    フィードバックを受けて追加した。
    """

    def test_applies_two_replaces_in_one_output_file(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=False)
        new1 = _make_pdf(tmp_path / "new1.pdf", 1)
        new2 = _make_pdf(tmp_path / "new2.pdf", 1)
        final = tmp_path / "final.pdf"
        files_before = {p.name for p in tmp_path.iterdir()}

        operations = [
            {"type": "replace", "document_number": "資料1", "new_source_path": str(new1)},
            {"type": "replace", "document_number": "資料2", "new_source_path": str(new2)},
        ]
        result = combiner.apply_document_operations(str(out), operations, str(final))
        assert result.success is True

        manifest = combiner.load_combine_manifest(str(final)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料2", "資料3"]

        # 中間ファイルが最終出力ファイル以外に残っていないこと
        files_after = {p.name for p in tmp_path.iterdir()}
        assert files_after - files_before == {"final.pdf"}

    def test_applies_insert_then_delete(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path, add_page_numbers=True)
        new_doc = _make_pdf(tmp_path / "new.pdf", 1)
        final = tmp_path / "final.pdf"

        operations = [
            {
                "type": "insert", "insert_after_document_number": "資料1",
                "document_number": "資料1.5", "new_source_path": str(new_doc),
                "stamp_settings": None,
            },
            {"type": "delete", "document_number": "資料3"},
        ]
        result = combiner.apply_document_operations(str(out), operations, str(final))
        assert result.success is True

        manifest = combiner.load_combine_manifest(str(final)).manifest
        labels = [d["document_number"] for d in manifest["documents"]]
        assert labels == ["資料1", "資料1.5", "資料2"]
        assert _page_footer_numbers(final) == ["1", "2", "3"]

    def test_empty_operation_list_returns_error(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        result = combiner.apply_document_operations(str(out), [], str(tmp_path / "final.pdf"))
        assert result.success is False

    def test_stops_and_reports_error_on_unknown_document_number(self, combiner, tmp_path):
        out = _combine_three_stamped_docs(combiner, tmp_path)
        new_doc = _make_pdf(tmp_path / "new.pdf", 1)
        final = tmp_path / "final.pdf"

        operations = [
            {"type": "replace", "document_number": "資料99", "new_source_path": str(new_doc)},
        ]
        result = combiner.apply_document_operations(str(out), operations, str(final))
        assert result.success is False
        assert not final.exists()
