"""
修正されたページ番号位置のテスト
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

# 簡易版テスト
import fitz
import time

class FileValidator:
    @staticmethod
    def is_readable_file(file_path):
        try:
            return os.access(file_path, os.R_OK)
        except:
            return False

def test_fixed_page_position():
    """修正されたページ番号位置のテスト"""
    print("=== 修正されたページ番号位置テスト ===")

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

        # 修正されたページ番号挿入処理
        font_name = "cour"
        start_page = 1
        start_number = 1

        print(f"\n=== 修正された座標計算 ===")

        for page_num in range(min(3, len(writer))):  # 最初の3ページのみテスト
            page = writer[page_num]
            page_number_text = str(start_number + page_num)

            # 修正された回転を考慮したページ番号配置
            original_rotation = page.rotation

            # 回転に応じた座標計算
            text_width = fitz.get_text_length(page_number_text, fontname=font_name, fontsize=12)

            if original_rotation == 270:
                # 270度回転の場合：実際の下部中央は元座標系の左側中央
                x = 28.35  # 左端から10mm（実際の表示では下部）
                y = (page.rect.height - text_width) / 2  # 垂直中央

            elif original_rotation == 90:
                # 90度回転の場合：実際の下部中央は元座標系の右側中央
                x = page.rect.width - 28.35  # 右端から10mm
                y = (page.rect.height + text_width) / 2  # 垂直中央

            elif original_rotation == 180:
                # 180度回転の場合：実際の下部中央は元座標系の上部中央
                x = (page.rect.width - text_width) / 2  # 水平中央
                y = 28.35  # 上端から10mm

            else:
                # 0度回転の場合：通常の下部中央
                x = (page.rect.width - text_width) / 2  # 水平中央
                y = page.rect.height - 28.35  # 下端から10mm

            print(f"ページ{page_num+1} (回転{original_rotation}度): x={x:.1f}, y={y:.1f}")

            # ページ番号を挿入（赤色で区別）
            page.insert_text((x, y),
                           page_number_text,
                           fontname=font_name,
                           fontsize=12,
                           color=(1, 0, 0))  # 赤色

        # 結果を保存
        output_file = "test_corrected_page_position.pdf"
        writer.save(output_file)
        writer.close()

        print(f"\n修正版テストファイル保存: {output_file}")

        # 結果検証
        result_doc = fitz.open(output_file)
        first_page = result_doc[0]

        # ページ番号の位置を確認
        text_instances = first_page.get_text("dict")

        print(f"\n=== 修正後のページ番号位置 ===")
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        color = span.get("color", 0)
                        if text.isdigit() and color != 0:  # 赤色のページ番号
                            bbox = span["bbox"]
                            print(f"修正版ページ番号 '{text}': 位置 ({bbox[0]:.1f}, {bbox[1]:.1f})")

        result_doc.close()

    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_page_position()