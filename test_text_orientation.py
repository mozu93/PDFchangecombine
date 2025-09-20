"""
テキストの向き制御のテスト
"""
import fitz
from pathlib import Path

def test_text_orientation():
    """テキストの向き制御テスト"""
    print("=== テキストの向き制御テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        doc = fitz.open(problem_pdf)
        page = doc[0]

        original_rotation = page.rotation
        print(f"元のページ回転: {original_rotation}度")

        # 270度回転時のページサイズ
        rotated_width = page.rect.width
        rotated_height = page.rect.height
        print(f"270度回転時のサイズ: {rotated_width:.1f} x {rotated_height:.1f}")

        # 0度にリセット
        page.set_rotation(0)

        font_name = "cour"
        page_number_text = "1"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        page_width = page.rect.width
        page_height = page.rect.height

        print(f"0度時のサイズ: {page_width:.1f} x {page_height:.1f}")

        # 270度回転時の正しい座標
        x = 28.35  # 左端から10mm（実際の表示では下部）
        y = (page_height - text_width) / 2  # 垂直中央

        print(f"配置座標: x={x:.1f}, y={y:.1f}")

        # 方法1: 通常のinsert_text（横向きになる可能性）
        page.insert_text((x, y),
                        "1A",  # 識別用
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 0, 0))  # 赤色

        # 方法2: morphパラメータで向きを制御
        # 270度回転PDFで正しい向きにするためのmorph設定
        from fitz import Matrix

        # 270度回転を補正するための変換マトリックス
        # 反時計回りに90度回転させてテキストを正立にする
        morph = (fitz.Matrix(0, 1, -1, 0, 0, 0), fitz.Point(x + 20, y))

        page.insert_text((x + 20, y),
                        "1B",  # 識別用
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 1, 0),  # 緑色
                        morph=morph)

        # 方法3: 異なるmorph設定
        morph2 = (fitz.Matrix(1, 0, 0, 1, 0, 0), fitz.Point(x + 40, y))

        page.insert_text((x + 40, y),
                        "1C",  # 識別用
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 0, 1),  # 青色
                        morph=morph2)

        # 方法4: rotate パラメータを使用
        page.insert_text((x + 60, y),
                        "1D",  # 識別用
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 1, 0),  # 黄色
                        rotate=0)  # 強制的に0度

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = "test_text_orientation.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")
        print("\n各方法でのテキスト表示:")
        print("  1A (赤): 通常のinsert_text")
        print("  1B (緑): morph変換使用")
        print("  1C (青): 単位行列morph")
        print("  1D (黄): rotate=0指定")

        # 検証
        verify_doc = fitz.open(output_file)
        verify_page = verify_doc[0]

        print(f"\n=== 検証結果 ===")

        text_instances = verify_page.get_text("dict")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text in ["1A", "1B", "1C", "1D"]:
                            bbox = span["bbox"]
                            color = span.get("color", 0)
                            print(f"{text}: 位置 ({bbox[0]:.1f}, {bbox[1]:.1f})")

        verify_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_text_orientation()