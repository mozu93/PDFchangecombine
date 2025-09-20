"""
問題のPDFファイルの詳細分析スクリプト
"""
import fitz
import sys
from pathlib import Path

def analyze_pdf(pdf_path):
    """PDFファイルの詳細分析"""
    print(f"=== PDF分析: {Path(pdf_path).name} ===")

    try:
        # 基本情報
        print(f"ファイルサイズ: {Path(pdf_path).stat().st_size:,} bytes")

        # PyMuPDFで開く
        doc = fitz.open(pdf_path)
        print(f"ページ数: {doc.page_count}")
        print(f"暗号化: {doc.is_encrypted}")
        # print(f"PDFバージョン: {doc.pdf_version()}")  # この機能は利用不可
        print(f"メタデータ: {doc.metadata}")

        # 各ページの情報
        print("\n=== ページ詳細 ===")
        for i, page in enumerate(doc):
            print(f"ページ {i+1}:")
            print(f"  サイズ: {page.rect.width:.2f} x {page.rect.height:.2f}")
            print(f"  回転: {page.rotation}")

            # ページの内容チェック
            try:
                text = page.get_text()
                print(f"  テキスト文字数: {len(text)}")

                # 画像数
                image_list = page.get_images()
                print(f"  画像数: {len(image_list)}")

                # フォント情報
                fonts = page.get_fonts()
                print(f"  フォント数: {len(fonts)}")
                if fonts:
                    print(f"  フォント: {[f[3] for f in fonts[:3]]}")  # 最初の3つのフォント名

            except Exception as e:
                print(f"  ページ内容エラー: {e}")

        # 白紙ページ追加テスト
        print("\n=== 白紙ページ追加テスト ===")
        try:
            temp_doc = fitz.open()
            temp_doc.insert_pdf(doc)

            if len(temp_doc) % 2 != 0:
                print("奇数ページ検出 - 白紙ページ追加テスト実行")
                last_page = temp_doc[-1]
                print(f"最終ページサイズ: {last_page.rect.width} x {last_page.rect.height}")

                # 白紙ページ追加
                new_page = temp_doc.new_page(width=last_page.rect.width, height=last_page.rect.height)
                print(f"白紙ページ追加完了: ページ{len(temp_doc)}")
                print(f"新しいページサイズ: {new_page.rect.width} x {new_page.rect.height}")
            else:
                print("偶数ページのため白紙ページ追加不要")

            temp_doc.close()
            print("白紙ページ追加テスト成功")

        except Exception as e:
            print(f"白紙ページ追加テストエラー: {e}")
            import traceback
            traceback.print_exc()

        # ページ番号追加テスト
        print("\n=== ページ番号追加テスト ===")
        try:
            test_doc = fitz.open()
            test_doc.insert_pdf(doc)

            font_name = "cour"
            page = test_doc[0]  # 最初のページでテスト
            page_number_text = "1"

            # テキストの幅を計算して中央揃え
            text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)
            x = (page.rect.width - text_width) / 2
            y = page.rect.height - 28.35  # 下から10mm

            print(f"ページ番号位置: x={x:.2f}, y={y:.2f}")
            print(f"テキスト幅: {text_width:.2f}")

            page.insert_text((x, y),
                           page_number_text,
                           fontname=font_name,
                           fontsize=12,
                           color=(0, 0, 0))

            test_doc.close()
            print("ページ番号追加テスト成功")

        except Exception as e:
            print(f"ページ番号追加テストエラー: {e}")
            import traceback
            traceback.print_exc()

        doc.close()

    except Exception as e:
        print(f"PDF分析エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"
    analyze_pdf(pdf_path)