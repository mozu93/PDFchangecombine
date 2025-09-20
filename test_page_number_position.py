"""
270度回転PDFでのページ番号位置の詳細分析
"""
import fitz
from pathlib import Path

def analyze_page_number_position():
    """ページ番号位置の詳細分析"""
    print("=== ページ番号位置分析 ===")

    # 保存されたファイルを確認
    saved_file = r"C:\Users\taka\Desktop\12月正副会頭会議資料\popopopop.pdf"

    if not Path(saved_file).exists():
        print(f"保存されたファイルが見つかりません: {saved_file}")
        return

    try:
        doc = fitz.open(saved_file)
        first_page = doc[0]

        print(f"ページ回転: {first_page.rotation}度")
        print(f"ページサイズ(rect): {first_page.rect}")
        print(f"ページサイズ(mediabox): {first_page.mediabox}")

        # ページのテキストを取得
        text_instances = first_page.get_text("dict")

        print(f"\n=== ページ内のテキスト情報 ===")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text and text.isdigit():  # ページ番号らしきテキスト
                            bbox = span["bbox"]
                            print(f"数字テキスト '{text}': 位置 {bbox}")
                            print(f"  左下: ({bbox[0]:.1f}, {bbox[1]:.1f})")
                            print(f"  右上: ({bbox[2]:.1f}, {bbox[3]:.1f})")

        # 現在の座標計算方法をシミュレート
        print(f"\n=== 現在の座標計算シミュレーション ===")

        # 0度状態での計算（現在のコード）
        test_page = doc[0]
        original_rotation = test_page.rotation

        if original_rotation != 0:
            test_page.set_rotation(0)

        page_number_text = "1"
        font_name = "cour"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        x_calculated = (test_page.rect.width - text_width) / 2
        y_calculated = test_page.rect.height - 28.35

        print(f"0度時の計算座標: x={x_calculated:.1f}, y={y_calculated:.1f}")
        print(f"0度時のページサイズ: {test_page.rect.width:.1f} x {test_page.rect.height:.1f}")

        # 回転を戻す
        if original_rotation != 0:
            test_page.set_rotation(original_rotation)

        print(f"270度時のページサイズ: {test_page.rect.width:.1f} x {test_page.rect.height:.1f}")

        # 理想的な位置の計算
        print(f"\n=== 理想的な位置（フッター中央下部）===")

        # 270度回転時の実際の表示を考慮した座標計算
        # 270度回転では、物理的なページの下部中央は、元の座標系では左側中央になる

        if original_rotation == 270:
            # 270度回転の場合の正しい座標計算
            # 実際の表示では、元の座標系の左端がフッターになる
            ideal_x = 28.35  # 左端から10mm（フッター位置）
            ideal_y = test_page.rect.height / 2 - text_width / 2  # 垂直中央

            print(f"270度回転時の理想座標: x={ideal_x:.1f}, y={ideal_y:.1f}")
            print("この座標は、実際の表示では下部中央に相当します")

        doc.close()

    except Exception as e:
        print(f"分析エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_page_number_position()