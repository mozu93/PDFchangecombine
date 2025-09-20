"""
最終修正のテスト - 270度回転PDFでのページ番号正立表示
"""
import fitz
from pathlib import Path

def test_final_fix():
    """最終修正のテスト"""
    print("=== 最終修正テスト: 270度回転PDFでのページ番号正立表示 ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        doc = fitz.open(problem_pdf)
        page = doc[0]

        original_rotation = page.rotation
        print(f"元のページ回転: {original_rotation}度")

        # 0度にリセット
        page.set_rotation(0)

        font_name = "cour"
        page_number_text = "1"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        page_width = page.rect.width
        page_height = page.rect.height

        # 修正された座標計算（combiner.pyと同じロジック）
        if original_rotation == 270:
            # 270度回転PDF: 0度状態での左側中央が実際の下部中央になる
            x = 28.35  # 左端から10mm（実際の表示では下部）
            y = (page_height - text_width) / 2  # 垂直中央
        else:
            # その他の回転: 通常の下部中央
            x = (page_width - text_width) / 2  # 水平中央
            y = page_height - 28.35  # 下端から10mm

        print(f"配置座標: x={x:.1f}, y={y:.1f}")

        # 修正されたページ番号挿入（combiner.pyと同じロジック）
        if original_rotation == 270:
            page.insert_text((x, y),
                            page_number_text,
                            fontname=font_name,
                            fontsize=12,
                            color=(1, 0, 0),  # 赤色で識別
                            rotate=90)
            print("270度回転PDF用: rotate=90パラメータでページ番号挿入")
        else:
            page.insert_text((x, y),
                            page_number_text,
                            fontname=font_name,
                            fontsize=12,
                            color=(1, 0, 0))
            print("通常PDF用: rotateパラメータなしでページ番号挿入")

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = "test_final_fix.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")
        print("\n期待される結果:")
        print("- ページ番号が下部中央に配置される")
        print("- 数字が縦向き（正立）で表示される")
        print("- PDFビューアーで確認してください")

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final_fix()