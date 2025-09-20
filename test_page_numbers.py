"""
270度回転PDFでのページ番号挿入問題の分析
"""
import fitz
from pathlib import Path

def test_page_number_insertion():
    """ページ番号挿入の詳細テスト"""
    print("=== ページ番号挿入テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    try:
        # 元のPDFを開く
        doc = fitz.open(problem_pdf)
        first_page = doc[0]

        print(f"ページ回転: {first_page.rotation}度")
        print(f"ページサイズ(rect): {first_page.rect}")
        print(f"ページサイズ(mediabox): {first_page.mediabox}")

        # 現在のコード（問題のあるコード）
        print("\n--- 現在のコード（問題版）---")

        # クリーンなPDFを作成
        clean_doc = fitz.open()
        clean_doc.insert_pdf(doc)

        font_name = "cour"
        page = clean_doc[0]  # 最初のページでテスト
        page_number_text = "1"

        # 現在のコードと同じ座標計算
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)
        x = (page.rect.width - text_width) / 2
        y = page.rect.height - 28.35  # 下から10mm

        print(f"計算された座標: x={x:.2f}, y={y:.2f}")
        print(f"テキスト幅: {text_width:.2f}")
        print(f"rect寸法: width={page.rect.width}, height={page.rect.height}")

        # テキスト挿入
        page.insert_text((x, y), page_number_text, fontname=font_name, fontsize=12, color=(0, 0, 0))
        clean_doc.save("test_current_page_numbers.pdf")
        clean_doc.close()

        # 修正版1: 回転を考慮した座標計算
        print("\n--- 修正版1: 回転考慮座標計算 ---")

        fixed_doc1 = fitz.open()
        fixed_doc1.insert_pdf(doc)

        page1 = fixed_doc1[0]
        rotation = page1.rotation

        if rotation == 270:
            # 270度回転の場合、座標系を調整
            # 270度回転では、元の(x,y)は新しい座標系では(y, width-x)になる

            # フッター中央を目指すなら、回転後の座標系で計算
            mediabox = page1.mediabox
            print(f"mediabox: {mediabox}")

            # 回転前の実際のページサイズ
            actual_width = mediabox.width
            actual_height = mediabox.height

            # 270度回転の場合の座標計算
            # 目標：フッター中央下部
            target_x_unrotated = actual_width / 2 - text_width / 2  # 中央
            target_y_unrotated = 28.35  # 下から10mm

            # 270度回転後の座標変換
            x_rotated = target_y_unrotated
            y_rotated = actual_width - target_x_unrotated

            print(f"回転前目標座標: x={target_x_unrotated:.2f}, y={target_y_unrotated:.2f}")
            print(f"270度回転後座標: x={x_rotated:.2f}, y={y_rotated:.2f}")

        else:
            # 0度回転の場合は現在のまま
            x_rotated = (page1.rect.width - text_width) / 2
            y_rotated = page1.rect.height - 28.35

        page1.insert_text((x_rotated, y_rotated), page_number_text, fontname=font_name, fontsize=12, color=(1, 0, 0))  # 赤色で区別
        fixed_doc1.save("test_fixed1_page_numbers.pdf")
        fixed_doc1.close()

        # 修正版2: PyMuPDFの座標変換を使用
        print("\n--- 修正版2: PyMuPDF座標変換使用 ---")

        fixed_doc2 = fitz.open()
        fixed_doc2.insert_pdf(doc)

        page2 = fixed_doc2[0]

        # 回転を一時的に0度にして座標計算
        original_rotation = page2.rotation
        if original_rotation != 0:
            page2.set_rotation(0)

        # 0度での座標計算
        text_width_0 = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)
        x_0 = (page2.rect.width - text_width_0) / 2
        y_0 = page2.rect.height - 28.35

        print(f"0度回転時の座標: x={x_0:.2f}, y={y_0:.2f}")

        # テキスト挿入
        page2.insert_text((x_0, y_0), page_number_text, fontname=font_name, fontsize=12, color=(0, 1, 0))  # 緑色で区別

        # 回転を元に戻す
        if original_rotation != 0:
            page2.set_rotation(original_rotation)

        fixed_doc2.save("test_fixed2_page_numbers.pdf")
        fixed_doc2.close()

        doc.close()

        print("\n=== テスト完了 ===")
        print("作成されたファイル:")
        print("- test_current_page_numbers.pdf（現在のコード）")
        print("- test_fixed1_page_numbers.pdf（修正版1：座標変換）")
        print("- test_fixed2_page_numbers.pdf（修正版2：回転リセット）")

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_page_number_insertion()