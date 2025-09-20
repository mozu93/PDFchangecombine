"""
回転PDFでの白紙ページ挿入問題の詳細テスト
"""
import fitz
from pathlib import Path

def test_rotation_handling(pdf_path):
    """回転PDFでの白紙ページ挿入テスト"""
    print(f"=== 回転PDF白紙ページ挿入テスト ===")

    try:
        # 元のPDFを開く
        original_doc = fitz.open(pdf_path)
        print(f"元PDFページ数: {len(original_doc)}")

        # 最終ページの詳細情報
        last_page = original_doc[-1]
        print(f"最終ページ回転: {last_page.rotation}")
        print(f"最終ページサイズ(rect): {last_page.rect}")
        print(f"最終ページサイズ(mediabox): {last_page.mediabox}")

        # 現在のコードと同じ処理
        print("\n--- 現在のコード（問題のあるコード）---")
        temp_doc1 = fitz.open()
        temp_doc1.insert_pdf(original_doc)

        if len(temp_doc1) % 2 != 0:
            last_page1 = temp_doc1[-1]
            print(f"挿入前最終ページ: 回転={last_page1.rotation}, サイズ={last_page1.rect}")

            # 問題のあるコード：回転を考慮せずサイズ指定
            new_page1 = temp_doc1.new_page(width=last_page1.rect.width, height=last_page1.rect.height)
            print(f"新規ページ: 回転={new_page1.rotation}, サイズ={new_page1.rect}")

            # 保存してテスト
            temp_doc1.save("test_current_method.pdf")
            print("現在のメソッドでのテストPDF作成完了")

        temp_doc1.close()

        # 修正版：回転を考慮した処理
        print("\n--- 修正版コード（回転考慮）---")
        temp_doc2 = fitz.open()
        temp_doc2.insert_pdf(original_doc)

        if len(temp_doc2) % 2 != 0:
            last_page2 = temp_doc2[-1]

            # 回転を考慮したサイズ計算
            if last_page2.rotation in [90, 270]:
                # 90度または270度回転の場合、幅と高さを入れ替える
                width = last_page2.rect.height
                height = last_page2.rect.width
            else:
                width = last_page2.rect.width
                height = last_page2.rect.height

            print(f"計算されたサイズ: width={width}, height={height}")

            # 新しいページを作成し、同じ回転を適用
            new_page2 = temp_doc2.new_page(width=width, height=height)

            # 回転設定（安全な方法）
            rotation = last_page2.rotation
            if rotation != 0:
                page_index = len(temp_doc2) - 1  # 最後に追加されたページのインデックス
                actual_page = temp_doc2[page_index]
                actual_page.set_rotation(rotation)

            print(f"新規ページ（修正版）: インデックス={len(temp_doc2)-1}, 想定回転={rotation}")

            # 保存してテスト
            temp_doc2.save("test_fixed_method.pdf")
            print("修正版メソッドでのテストPDF作成完了")

        temp_doc2.close()

        # さらなる修正版：mediaboxを使用
        print("\n--- 修正版コード（mediabox使用）---")
        temp_doc3 = fitz.open()
        temp_doc3.insert_pdf(original_doc)

        if len(temp_doc3) % 2 != 0:
            last_page3 = temp_doc3[-1]

            # mediaboxを使用してより正確なサイズを取得
            mediabox = last_page3.mediabox
            print(f"Mediabox: {mediabox}")

            # 新しいページを作成
            new_page3 = temp_doc3.new_page(width=mediabox.width, height=mediabox.height)

            # 回転設定（安全な方法）
            rotation = last_page3.rotation
            if rotation != 0:
                page_index = len(temp_doc3) - 1
                actual_page = temp_doc3[page_index]
                actual_page.set_rotation(rotation)

            print(f"新規ページ（mediabox版）: インデックス={len(temp_doc3)-1}, 想定回転={rotation}")

            # 保存してテスト
            temp_doc3.save("test_mediabox_method.pdf")
            print("mediabox版メソッドでのテストPDF作成完了")

        temp_doc3.close()
        original_doc.close()

        # 結果ファイルの検証
        print("\n=== 結果検証 ===")
        for filename in ["test_current_method.pdf", "test_fixed_method.pdf", "test_mediabox_method.pdf"]:
            if Path(filename).exists():
                test_doc = fitz.open(filename)
                print(f"{filename}: {len(test_doc)}ページ")

                if len(test_doc) > 0:
                    last_test_page = test_doc[-1]
                    print(f"  最終ページ: 回転={last_test_page.rotation}, サイズ={last_test_page.rect}")

                test_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"
    test_rotation_handling(pdf_path)