"""
シンプルなテキスト回転制御テスト
"""
import fitz
from pathlib import Path

def test_simple_rotation():
    """シンプルなテキスト回転制御テスト"""
    print("=== シンプルなテキスト回転制御テスト ===")

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

        # 270度回転時の正しい座標
        x = 28.35
        y = (page_height - text_width) / 2

        print(f"配置座標: x={x:.1f}, y={y:.1f}")

        # 方法1: rotateパラメータなし（デフォルト）
        page.insert_text((x, y),
                        "1",
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 0, 0))  # 赤色

        # 方法2: rotate=0指定
        page.insert_text((x + 20, y),
                        "2",
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 1, 0),  # 緑色
                        rotate=0)

        # 方法3: rotate=90指定
        page.insert_text((x + 40, y),
                        "3",
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 0, 1),  # 青色
                        rotate=90)

        # 方法4: rotate=270指定
        page.insert_text((x + 60, y),
                        "4",
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 0, 1),  # マゼンタ色
                        rotate=270)

        # 方法5: rotate=-90指定
        page.insert_text((x + 80, y),
                        "5",
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 1, 0),  # 黄色
                        rotate=-90)

        # 回転を元に戻す前に、どれが正しい向きかチェック
        print("\n0度状態でのテキスト配置完了")

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = "test_simple_rotation.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")
        print("\n各rotateパラメータでのテスト:")
        print("  1 (赤): rotateなし")
        print("  2 (緑): rotate=0")
        print("  3 (青): rotate=90")
        print("  4 (マゼンタ): rotate=270")
        print("  5 (黄): rotate=-90")

        print("\nPDFビューアーで開いて、どの数字が正しい向き（縦向き）で表示されているか確認してください。")

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_rotation()