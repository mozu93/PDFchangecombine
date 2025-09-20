"""
全回転角度でのページ番号表示テスト
90度、180度、270度の回転PDFでの表示確認
"""
import fitz
from pathlib import Path

def create_rotated_test_pdfs():
    """各回転角度のテストPDFを作成"""
    print("=== 各回転角度のテストPDF作成 ===")

    # ベースとなるA4サイズの白紙PDF作成
    base_doc = fitz.open()
    base_page = base_doc.new_page(width=595.2, height=841.9)  # A4サイズ

    # 各回転角度でPDF作成
    rotations = [0, 90, 180, 270]

    for rotation in rotations:
        doc = fitz.open()
        page = doc.new_page(width=595.2, height=841.9)

        # ページに回転を適用
        page.set_rotation(rotation)

        # 参考用テキストを挿入（回転の確認用）
        if rotation == 0:
            page.insert_text((50, 50), f"回転: {rotation}度", fontsize=20)

        # 保存
        filename = f"test_rotation_{rotation}.pdf"
        doc.save(filename)
        doc.close()
        print(f"作成: {filename} (回転: {rotation}度)")

    base_doc.close()

def test_page_number_for_rotation(rotation):
    """指定された回転角度でのページ番号挿入テスト"""
    print(f"\n--- {rotation}度回転PDFテスト ---")

    input_file = f"test_rotation_{rotation}.pdf"
    if not Path(input_file).exists():
        print(f"テストファイルが見つかりません: {input_file}")
        return

    try:
        doc = fitz.open(input_file)
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

        print(f"0度時のサイズ: {page_width:.1f} x {page_height:.1f}")

        # 回転別の座標計算とrotateパラメータ
        if original_rotation == 0:
            # 0度: 通常の下部中央
            x = (page_width - text_width) / 2
            y = page_height - 28.35
            rotate_param = 0
        elif original_rotation == 90:
            # 90度回転: 右側中央が下部になる
            x = page_width - 28.35
            y = (page_height - text_width) / 2
            rotate_param = -90  # テキストを正立にする
        elif original_rotation == 180:
            # 180度回転: 上部中央が下部になる
            x = (page_width - text_width) / 2
            y = 28.35
            rotate_param = 180  # テキストを正立にする
        elif original_rotation == 270:
            # 270度回転: 左側中央が下部になる
            x = 28.35
            y = (page_height - text_width) / 2
            rotate_param = -90  # テキストを正立にする（修正済み）
        else:
            # その他の角度: デフォルト
            x = (page_width - text_width) / 2
            y = page_height - 28.35
            rotate_param = 0

        print(f"計算座標: x={x:.1f}, y={y:.1f}")
        print(f"rotateパラメータ: {rotate_param}")

        # ページ番号挿入
        page.insert_text((x, y),
                        page_number_text,
                        fontname=font_name,
                        fontsize=12,
                        color=(1, 0, 0),  # 赤色
                        rotate=rotate_param)

        # 回転を元に戻す
        page.set_rotation(original_rotation)

        # 保存
        output_file = f"test_result_{rotation}.pdf"
        doc.save(output_file)
        doc.close()

        print(f"結果保存: {output_file}")

    except Exception as e:
        print(f"テストエラー ({rotation}度): {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン処理"""
    print("=== 全回転角度でのページ番号表示テスト ===")

    # テストPDF作成
    create_rotated_test_pdfs()

    # 各回転角度でテスト
    rotations = [0, 90, 180, 270]
    for rotation in rotations:
        test_page_number_for_rotation(rotation)

    print("\n=== テスト完了 ===")
    print("各test_result_*.pdfファイルをPDFビューアーで確認してください")
    print("期待される結果: 全ての回転角度でページ番号が下部中央に正立で表示される")

if __name__ == "__main__":
    main()