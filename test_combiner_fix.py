"""
修正されたPDF結合機能の簡易テスト
"""
import fitz
from pathlib import Path
import time
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixed_blank_page_insertion():
    """修正された白紙ページ挿入のテスト"""
    print("=== 修正された白紙ページ挿入テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    try:
        # 元のPDFを開く
        reader = fitz.open(problem_pdf)
        print(f"元のPDF: {len(reader)}ページ（奇数ページ）")

        # 修正された白紙ページ挿入処理
        start_time = time.time()

        # 新しいドキュメントに結合
        writer = fitz.open()

        # 奇数ページのため白紙ページを追加
        if len(reader) % 2 != 0:
            temp_doc = fitz.open()
            temp_doc.insert_pdf(reader)

            # 最終ページの情報を安全に取得
            last_page_index = len(temp_doc) - 1
            last_page = temp_doc[last_page_index]

            # 回転とサイズ情報を取得
            rotation = last_page.rotation
            mediabox = last_page.mediabox

            print(f"最終ページ回転: {rotation}度")
            print(f"最終ページmediabox: {mediabox}")

            # 回転を考慮したサイズで白紙ページを作成
            blank_page = temp_doc.new_page(width=mediabox.width, height=mediabox.height)

            # 回転情報を適用
            if rotation != 0:
                blank_page_index = len(temp_doc) - 1
                temp_doc[blank_page_index].set_rotation(rotation)
                print(f"白紙ページに{rotation}度回転を適用")

            writer.insert_pdf(temp_doc)
            temp_doc.close()

        reader.close()

        # 結果を保存
        output_file = "test_rotation_fixed.pdf"
        writer.save(output_file)
        writer.close()

        processing_time = time.time() - start_time

        # 結果検証
        result_doc = fitz.open(output_file)
        print(f"\n結果: {len(result_doc)}ページ（期待値: 22ページ）")
        print(f"処理時間: {processing_time:.2f}秒")

        if len(result_doc) >= 22:
            # 最後のページ（白紙ページ）を確認
            blank_page_result = result_doc[-1]
            print(f"白紙ページ回転: {blank_page_result.rotation}度")
            print(f"白紙ページサイズ: {blank_page_result.rect}")

            # 白紙ページの内容確認
            text = blank_page_result.get_text()
            images = blank_page_result.get_images()
            print(f"白紙ページテキスト文字数: {len(text)}")
            print(f"白紙ページ画像数: {len(images)}")

            # 元のページと比較
            original_page = result_doc[-2]  # 最後から2番目（元の最終ページ）
            print(f"元最終ページ回転: {original_page.rotation}度")

            if blank_page_result.rotation == original_page.rotation:
                print("✅ 白紙ページの回転が正しく設定されました")
            else:
                print("❌ 白紙ページの回転が正しくありません")

            if len(text) == 0 and len(images) == 0:
                print("✅ 白紙ページが正しく作成されました")
            else:
                print("⚠️ 白紙ページに予期しない内容があります")

        result_doc.close()

        print(f"\n✅ テスト完了: {output_file}")

    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_blank_page_insertion()