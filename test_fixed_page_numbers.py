"""
修正されたページ番号挿入機能のテスト
"""
import fitz
from pathlib import Path
import time
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixed_page_number_insertion():
    """修正されたページ番号挿入のテスト"""
    print("=== 修正されたページ番号挿入テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    try:
        # 修正されたページ番号挿入処理のテスト
        start_time = time.time()

        # 元のPDFを開く
        reader = fitz.open(problem_pdf)
        print(f"元のPDF: {len(reader)}ページ")

        # 新しいドキュメントに結合
        writer = fitz.open()
        writer.insert_pdf(reader)
        reader.close()

        # クリーンなPDFを作成
        clean_doc = fitz.open()
        clean_doc.insert_pdf(writer)
        writer.close()
        writer = clean_doc

        font_name = "cour"
        start_page = 1
        start_number = 1

        print(f"ページ番号挿入開始: {len(writer)}ページ")

        # 修正されたページ番号挿入ロジック
        for page_num in range(start_page - 1, len(writer)):
            page = writer[page_num]
            page_number_text = str(start_number + page_num - (start_page - 1))

            # 回転を考慮したページ番号配置
            original_rotation = page.rotation

            print(f"ページ{page_num+1}: 回転{original_rotation}度")

            # 一時的に回転を0度にして正確な座標計算
            if original_rotation != 0:
                page.set_rotation(0)

            # テキストの幅を計算して中央揃え（0度回転状態で）
            text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)
            x = (page.rect.width - text_width) / 2
            y = page.rect.height - 28.35  # 下から10mm

            print(f"  0度時座標: x={x:.2f}, y={y:.2f}")

            # ページ番号を挿入
            page.insert_text((x, y),
                           page_number_text,
                           fontname=font_name,
                           fontsize=12,
                           color=(0, 0, 0))

            # 回転を元に戻す
            if original_rotation != 0:
                page.set_rotation(original_rotation)

            # 最初の数ページだけ詳細出力
            if page_num < 3:
                print(f"  ページ番号'{page_number_text}'挿入完了")

        # 結果を保存
        output_file = "test_fixed_page_numbers_final.pdf"
        writer.save(output_file)
        writer.close()

        processing_time = time.time() - start_time

        print(f"\nページ番号挿入完了: {output_file}")
        print(f"処理時間: {processing_time:.2f}秒")

        # 結果検証
        result_doc = fitz.open(output_file)
        print(f"結果PDF: {len(result_doc)}ページ")

        # 最初のページでページ番号が正しく挿入されたか確認
        first_page = result_doc[0]
        first_page_text = first_page.get_text()

        print(f"最初のページテキスト（ページ番号含む）: {len(first_page_text)}文字")

        # ページ番号"1"が含まれているかチェック
        if "1" in first_page_text:
            print("✅ ページ番号が挿入されています")
        else:
            print("❌ ページ番号が見つかりません")

        result_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_page_number_insertion()