"""
270度回転PDFの真の中央配置テスト
"""
import fitz
from pathlib import Path

def test_true_center():
    """270度回転PDFの真の中央配置"""
    print("=== 270度回転PDF真の中央配置テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        doc = fitz.open(problem_pdf)
        page = doc[0]

        original_rotation = page.rotation
        print(f"元のページ回転: {original_rotation}度")

        # 270度回転時の実際のページサイズ
        rotated_width = page.rect.width   # 595.2
        rotated_height = page.rect.height # 841.9

        print(f"270度回転時のサイズ: {rotated_width:.1f} x {rotated_height:.1f}")

        # 270度回転時の真の中央位置
        true_center_x = rotated_width / 2
        footer_y = rotated_height - 28.35  # 下から10mm

        print(f"270度回転時の真の中央: x={true_center_x:.1f}")
        print(f"フッター位置: y={footer_y:.1f}")

        # 0度にリセット
        page.set_rotation(0)

        font_name = "cour"
        page_number_text = "1"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        # 0度状態でのページサイズ
        page_width_0 = page.rect.width   # 841.9
        page_height_0 = page.rect.height # 595.2

        print(f"0度時のサイズ: {page_width_0:.1f} x {page_height_0:.1f}")

        # 270度回転を考慮した座標変換
        # 270度回転時の中央(297.6, 813.57) = 0度時の(813.57, 297.6)の変換

        # 270度回転での真の中央を0度座標系に変換
        # 270度回転: (x, y) -> (y, width - x)
        # 逆変換: (x, y) -> (height - y, x)

        x_in_0_degree = page_height_0 - footer_y  # 595.2 - 813.57 = 負の値になる問題
        y_in_0_degree = true_center_x

        print(f"0度変換座標（計算1）: x={x_in_0_degree:.1f}, y={y_in_0_degree:.1f}")

        # 正しい変換方法
        # 270度回転時の目標位置: 下部中央
        # これは0度時の右側中央に対応する

        x_correct = page_width_0 - 28.35  # 右端から10mm
        y_correct = (page_height_0 - text_width) / 2  # 垂直中央

        print(f"0度変換座標（修正版）: x={x_correct:.1f}, y={y_correct:.1f}")

        # ページ番号を挿入
        page.insert_text((x_correct, y_correct),
                        page_number_text,
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 1, 1))  # シアン色

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = "test_true_center.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")

        # 検証
        verify_doc = fitz.open(output_file)
        verify_page = verify_doc[0]

        print(f"\n=== 真の中央配置検証 ===")

        text_instances = verify_page.get_text("dict")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        color = span.get("color", 0)
                        if text == "1" and color != 0:
                            bbox = span["bbox"]
                            print(f"真の中央配置ページ番号位置: ({bbox[0]:.1f}, {bbox[1]:.1f})")

                            # 270度回転時の真の中央との比較
                            page_rect = verify_page.rect
                            true_center = page_rect.width / 2

                            distance_from_center = abs(bbox[0] - true_center)
                            print(f"真の中央({true_center:.1f})からの距離: {distance_from_center:.1f}px")

                            if distance_from_center < 10:
                                print("✓ 完全な中央配置達成")
                            elif distance_from_center < 30:
                                print("○ ほぼ中央配置")
                            else:
                                print("△ まだ調整が必要")

        verify_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_true_center()