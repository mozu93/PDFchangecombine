"""
シンプルなフッター配置のテスト
"""
import fitz
from pathlib import Path

def test_simple_footer():
    """シンプルなフッター配置テスト"""
    print("=== シンプルなフッター配置テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        # 元のPDFを開く
        doc = fitz.open(problem_pdf)
        page = doc[0]

        print(f"元のページ回転: {page.rotation}度")

        # 元の回転を記録
        original_rotation = page.rotation

        # 0度にリセット
        page.set_rotation(0)
        print(f"0度リセット後のページサイズ: {page.rect}")

        # シンプルなフッター中央配置
        font_name = "cour"
        page_number_text = "1"
        text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

        page_width = page.rect.width
        page_height = page.rect.height

        # フッター中央
        x = (page_width - text_width) / 2  # 水平中央
        y = page_height - 28.35  # 下端から10mm

        print(f"0度状態でのフッター中央座標: x={x:.1f}, y={y:.1f}")

        # ページ番号を挿入
        page.insert_text((x, y),
                        page_number_text,
                        fontname=font_name,
                        fontsize=12,
                        color=(0, 0, 1))  # 青色

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        print(f"回転を{original_rotation}度に復元")

        # 保存
        output_file = "test_simple_footer.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")

        # 検証
        verify_doc = fitz.open(output_file)
        verify_page = verify_doc[0]

        print(f"\n=== 検証結果 ===")
        print(f"最終ページ回転: {verify_page.rotation}度")

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
                            print(f"ページ番号位置: ({bbox[0]:.1f}, {bbox[1]:.1f})")

                            # 270度回転での位置評価
                            page_rect = verify_page.rect

                            # Y座標での上下判定（270度回転時）
                            if bbox[1] > page_rect.height * 0.7:
                                y_pos = "下部"
                            elif bbox[1] < page_rect.height * 0.3:
                                y_pos = "上部"
                            else:
                                y_pos = "中央"

                            # X座標での左右判定
                            center_x = page_rect.width / 2
                            if abs(bbox[0] - center_x) < 30:
                                x_pos = "中央"
                            elif bbox[0] < center_x:
                                x_pos = "左寄り"
                            else:
                                x_pos = "右寄り"

                            print(f"実際の表示位置: {y_pos} {x_pos}")

        verify_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_footer()