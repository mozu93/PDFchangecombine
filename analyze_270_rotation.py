"""
270度回転PDFの座標系詳細分析
"""
import fitz
from pathlib import Path

def analyze_270_rotation_coordinates():
    """270度回転PDFの座標系を詳細分析"""
    print("=== 270度回転PDF座標系分析 ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが見つかりません: {problem_pdf}")
        return

    try:
        doc = fitz.open(problem_pdf)
        page = doc[0]

        print(f"元のページ回転: {page.rotation}度")
        print(f"270度回転時のページサイズ: {page.rect}")
        print(f"MediaBox: {page.mediabox}")

        # 0度にリセットしたときのサイズ
        page.set_rotation(0)
        print(f"0度リセット時のページサイズ: {page.rect}")

        # 270度回転の座標変換を理解するためのテスト
        print(f"\n=== 270度回転での座標変換理論 ===")

        # 0度状態でのページサイズ
        width_0 = page.rect.width   # 841.92
        height_0 = page.rect.height # 595.20

        print(f"0度時: 幅={width_0:.1f}, 高さ={height_0:.1f}")

        # 270度回転時の変換理論
        print(f"\n270度回転時の座標変換:")
        print(f"  - 元の(x, y) → 回転後(y, width-x)")
        print(f"  - 0度時の下部中央: ({width_0/2:.1f}, {height_0-28.35:.1f})")
        print(f"  - 270度回転後の位置: ({height_0-28.35:.1f}, {width_0/2:.1f})")

        # 実際のフッター中央の正しい座標
        print(f"\n=== 正しいフッター中央の座標（0度状態で計算） ===")

        # 270度回転PDF向けの正しい座標計算
        # 実際の表示でのフッター中央 = 0度状態での上部中央
        correct_x = width_0 / 2      # 水平中央
        correct_y = 28.35            # 上端から10mm（実際の表示では下部）

        print(f"正しい座標（0度状態）: x={correct_x:.1f}, y={correct_y:.1f}")
        print(f"この位置が実際の表示では下部中央になります")

        # テスト用にページ番号を配置
        page.insert_text((correct_x - 3.6, correct_y), "TEST",
                        fontname="cour", fontsize=12, color=(1, 0, 0))

        # 270度に戻す
        page.set_rotation(270)

        # 保存してテスト
        test_output = "test_correct_coordinates.pdf"
        doc.save(test_output)
        doc.close()

        print(f"\nテスト結果保存: {test_output}")

        # 検証
        verify_doc = fitz.open(test_output)
        verify_page = verify_doc[0]

        print(f"\n=== 検証結果 ===")
        print(f"検証ページ回転: {verify_page.rotation}度")

        # テキスト位置確認
        text_instances = verify_page.get_text("dict")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text == "TEST":
                            bbox = span["bbox"]
                            print(f"TESTテキスト位置: ({bbox[0]:.1f}, {bbox[1]:.1f})")

                            # 270度回転での位置評価
                            page_rect = verify_page.rect

                            # 下部判定（270度回転時）
                            if bbox[1] > page_rect.height * 0.8:
                                pos_y = "下部"
                            elif bbox[1] < page_rect.height * 0.2:
                                pos_y = "上部"
                            else:
                                pos_y = "中央"

                            # 中央判定
                            if abs(bbox[0] - page_rect.width/2) < 50:
                                pos_x = "中央"
                            else:
                                pos_x = "端"

                            print(f"実際の表示位置: {pos_y} {pos_x}")

        verify_doc.close()

    except Exception as e:
        print(f"分析エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_270_rotation_coordinates()