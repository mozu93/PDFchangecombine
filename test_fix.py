"""
修正されたPDFCombinerクラスのテスト
"""
import sys
import os
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, 'src')

# 必要なモジュールを直接インポート
import logging
logging.basicConfig(level=logging.INFO)

# combiner.pyを直接インポートできるよう修正
sys.path.insert(0, 'src/core')
sys.path.insert(0, 'src/utils')

# モジュールの直接インポート
import combiner
PDFCombiner = combiner.PDFCombiner

def test_fixed_combiner():
    """修正されたPDFCombinerのテスト"""
    print("=== 修正されたPDFCombinerのテスト ===")

    # 問題のPDFファイル
    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    # PDFCombinerインスタンス作成
    combiner = PDFCombiner()

    # 出力ファイル
    output_file = "test_fixed_output.pdf"

    print(f"入力ファイル: {Path(problem_pdf).name}")
    print(f"出力ファイル: {output_file}")

    # 白紙ページ挿入ありでテスト
    print("\n--- 白紙ページ挿入ありのテスト ---")
    result1 = combiner.combine_pdfs(
        pdf_paths=[problem_pdf],
        output_path=output_file,
        add_blank_page=True,
        add_page_numbers=False
    )

    if result1.success:
        print(f"✅ 結合成功: {result1.total_pages}ページ")
        print(f"処理時間: {result1.processing_time:.2f}秒")

        # 結果ファイルの確認
        if Path(output_file).exists():
            import fitz
            result_doc = fitz.open(output_file)
            print(f"結果ページ数: {len(result_doc)}")

            # 最後のページが白紙ページか確認
            if len(result_doc) > 21:  # 元が21ページなので22ページ目が追加されているはず
                last_page = result_doc[-1]
                print(f"最終ページ回転: {last_page.rotation}")
                print(f"最終ページサイズ: {last_page.rect}")

                # 白紙ページかチェック（テキストが無い、画像が無い）
                text = last_page.get_text()
                images = last_page.get_images()
                print(f"最終ページテキスト文字数: {len(text)}")
                print(f"最終ページ画像数: {len(images)}")

                if len(text) == 0 and len(images) == 0:
                    print("✅ 白紙ページが正しく追加されました")
                else:
                    print("⚠️ 最終ページが白紙ではないかもしれません")

            result_doc.close()
        else:
            print("❌ 結果ファイルが作成されませんでした")
    else:
        print(f"❌ 結合失敗: {result1.error_message}")

    # ページ番号ありでもテスト
    print("\n--- ページ番号挿入ありのテスト ---")
    output_file2 = "test_fixed_output_with_numbers.pdf"

    result2 = combiner.combine_pdfs(
        pdf_paths=[problem_pdf],
        output_path=output_file2,
        add_blank_page=True,
        add_page_numbers=True,
        start_page=1,
        start_number=1
    )

    if result2.success:
        print(f"✅ ページ番号付き結合成功: {result2.total_pages}ページ")
        print(f"処理時間: {result2.processing_time:.2f}秒")
    else:
        print(f"❌ ページ番号付き結合失敗: {result2.error_message}")

    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_fixed_combiner()