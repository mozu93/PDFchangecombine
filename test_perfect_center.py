"""
完全な中央配置のテスト
"""
import fitz
from pathlib import Path

def test_perfect_center():
    """完全な中央配置テスト"""
    print("=== 完全な中央配置テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        # 270度回転PDFでの完全中央配置計算
        doc = fitz.open(problem_pdf)
        page = doc[0]

        original_rotation = page.rotation
        print(f"元のページ回転: {original_rotation}度")

        # 270度回転時のページサイズを確認
        rotated_width = page.rect.width   # 595.2
        rotated_height = page.rect.height # 841.9

        print(f"270度回転時のサイズ: {rotated_width:.1f} x {rotated_height:.1f}")

        # 0度にリセット
        page.set_rotation(0)

        font_name = "cour"
        page_number_text = "1"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        page_width = page.rect.width
        page_height = page.rect.height

        print(f"0度時のサイズ: {page_width:.1f} x {page_height:.1f}")

        # 完全な中央配置の計算
        # 270度回転での完全中央 = 0度状態での正確な中央
        x = (page_width - text_width) / 2  # 水平中央
        y = page_height - 28.35  # フッター位置

        print(f"計算座標: x={x:.1f}, y={y:.1f}")

        # ページ番号を挿入
        page.insert_text((x, y),
                        page_number_text,
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 0, 1))  # マゼンタ色

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = "test_perfect_center.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")

        # 検証
        verify_doc = fitz.open(output_file)
        verify_page = verify_doc[0]

        print(f"\n=== 完全中央配置検証 ===")

        # テキスト位置確認
        text_instances = verify_page.get_text("dict")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        color = span.get("color", 0)
                        if text == "1" and color != 0:
                            bbox = span["bbox"]
                            print(f"最終ページ番号位置: ({bbox[0]:.1f}, {bbox[1]:.1f})")

                            # 完全中央の判定
                            page_rect = verify_page.rect
                            center_x = page_rect.width / 2

                            # 中央からの距離
                            distance_from_center = abs(bbox[0] - center_x)
                            print(f"中央からの距離: {distance_from_center:.1f}px")

                            if distance_from_center < 10:
                                print("✓ 完全な中央配置")
                            elif distance_from_center < 30:
                                print("○ ほぼ中央配置")
                            else:
                                print("△ 中央からずれています")

                            # 下部の判定
                            if bbox[1] > page_rect.height * 0.7:
                                print("✓ 下部に配置")
                            else:
                                print("△ 下部ではありません")

        verify_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_perfect_center()