"""
最終修正版ページ番号位置のテスト
"""
import sys
import os
from pathlib import Path
import logging

# srcディレクトリをパスに追加
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/core')
sys.path.insert(0, 'src/utils')

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import fitz
import time

def test_final_page_position():
    """最終修正版ページ番号位置のテスト"""
    print("=== 最終修正版ページ番号位置テスト ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    try:
        # 元のPDFを開く
        reader = fitz.open(problem_pdf)
        print(f"元のPDF: {len(reader)}ページ, 回転: {reader[0].rotation}度")

        # 新しいドキュメントに結合
        writer = fitz.open()
        writer.insert_pdf(reader)
        reader.close()

        # クリーンなPDFを作成
        clean_doc = fitz.open()
        clean_doc.insert_pdf(writer)
        writer.close()
        writer = clean_doc

        # 最終修正版ページ番号挿入処理
        font_name = "cour"
        start_page = 1
        start_number = 1

        print(f"\n=== 最終修正版座標計算 ===")

        for page_num in range(min(3, len(writer))):  # 最初の3ページのみテスト
            page = writer[page_num]
            page_number_text = str(start_number + page_num)

            # 回転を考慮したページ番号配置
            original_rotation = page.rotation
            print(f"\nページ{page_num+1} 処理開始 (元回転: {original_rotation}度)")

            # 回転を一時的に0度にして正しい向きでページ番号を挿入
            if original_rotation != 0:
                page.set_rotation(0)
                print(f"  回転を0度にリセット")

            # 0度状態での座標計算（テキストが正しい向きで表示される）
            text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

            # 0度状態でのページサイズ取得
            page_width = page.rect.width
            page_height = page.rect.height

            print(f"  0度状態でのページサイズ: {page_width:.1f} x {page_height:.1f}")
            print(f"  テキスト幅: {text_width:.1f}")

            # 回転に応じた実際の表示位置を計算
            if original_rotation == 270:
                # 270度回転時：0度状態での右側中央が、実際の表示では下部中央になる
                x = page_width - 28.35  # 右端から10mm
                y = (page_height - text_width) / 2  # 垂直中央
                print(f"  270度回転補正: 右側中央 → 実際の下部中央")

            elif original_rotation == 90:
                # 90度回転時：0度状態での左側中央が、実際の表示では下部中央になる
                x = 28.35  # 左端から10mm
                y = (page_height + text_width) / 2  # 垂直中央
                print(f"  90度回転補正: 左側中央 → 実際の下部中央")

            elif original_rotation == 180:
                # 180度回転時：0度状態での上部中央が、実際の表示では下部中央になる
                x = (page_width - text_width) / 2  # 水平中央
                y = 28.35  # 上端から10mm
                print(f"  180度回転補正: 上部中央 → 実際の下部中央")

            else:
                # 0度回転：通常の下部中央
                x = (page_width - text_width) / 2  # 水平中央
                y = page_height - 28.35  # 下端から10mm
                print(f"  0度回転: 通常の下部中央")

            print(f"  計算座標: x={x:.1f}, y={y:.1f}")

            # ページ番号を挿入（0度状態で正しい向き）
            page.insert_text((x, y),
                           page_number_text,
                           fontname=font_name,
                           fontsize=12,
                           color=(0, 1, 0))  # 緑色で区別

            # 回転を元に戻す
            if original_rotation != 0:
                page.set_rotation(original_rotation)
                print(f"  回転を{original_rotation}度に復元")

        # 結果を保存
        output_file = "test_final_corrected_page_position.pdf"
        writer.save(output_file)
        writer.close()

        print(f"\n最終修正版テストファイル保存: {output_file}")

        # 結果検証
        result_doc = fitz.open(output_file)
        first_page = result_doc[0]

        print(f"\n=== 最終結果検証 ===")
        print(f"結果ページ回転: {first_page.rotation}度")

        # ページ番号の位置を確認
        text_instances = first_page.get_text("dict")

        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        color = span.get("color", 0)
                        if text.isdigit() and color != 0:  # 緑色のページ番号
                            bbox = span["bbox"]
                            print(f"最終修正版ページ番号 '{text}': 位置 ({bbox[0]:.1f}, {bbox[1]:.1f})")

                            # 270度回転PDFでの位置評価
                            if first_page.rotation == 270:
                                # 270度回転時の評価基準
                                page_rect = first_page.rect

                                # X座標評価（実際の表示での上下位置）
                                if bbox[1] > page_rect.height * 0.9:
                                    x_pos = "下部"
                                elif bbox[1] < page_rect.height * 0.1:
                                    x_pos = "上部"
                                else:
                                    x_pos = "中央"

                                # Y座標評価（実際の表示での左右位置）
                                if bbox[0] > page_rect.width * 0.6:
                                    y_pos = "右寄り"
                                elif bbox[0] < page_rect.width * 0.4:
                                    y_pos = "左寄り"
                                else:
                                    y_pos = "中央"

                                print(f"  270度回転表示での位置: {x_pos}, {y_pos}")

        result_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final_page_position()