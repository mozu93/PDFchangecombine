"""
PDF保存失敗の原因調査
"""
import fitz
import os
from pathlib import Path
import tempfile
import time

def test_save_scenarios():
    """様々な保存シナリオのテスト"""
    print("=== PDF保存問題の調査 ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    # 1. 基本的な保存テスト
    print("\n1. 基本的な保存テスト")
    try:
        doc = fitz.open(problem_pdf)
        basic_output = "test_basic_save.pdf"

        doc.save(basic_output)
        doc.close()

        if Path(basic_output).exists():
            print(f"OK 基本保存成功: {basic_output}")
            print(f"ファイルサイズ: {Path(basic_output).stat().st_size:,} bytes")
        else:
            print("NG 基本保存失敗")

    except Exception as e:
        print(f"ERROR 基本保存エラー: {e}")

    # 2. 異なる保存オプションのテスト
    print("\n2. 保存オプションテスト")

    save_options = [
        ("deflate=True", {"deflate": True}),
        ("garbage=4", {"garbage": 4}),
        ("linear=True", {"linear": True}),
        ("clean=True", {"clean": True}),
        ("deflate=False,garbage=0", {"deflate": False, "garbage": 0}),  # 現在のコード
    ]

    for desc, options in save_options:
        try:
            doc = fitz.open(problem_pdf)
            output_file = f"test_save_{desc.replace('=', '_').replace(',', '_').replace(' ', '_')}.pdf"

            doc.save(output_file, **options)
            doc.close()

            if Path(output_file).exists():
                size = Path(output_file).stat().st_size
                print(f"OK {desc}: {size:,} bytes")
            else:
                print(f"NG {desc}: ファイル作成失敗")

        except Exception as e:
            print(f"ERROR {desc}: {e}")

    # 3. 長いファイルパスのテスト
    print("\n3. 長いファイルパスのテスト")
    try:
        doc = fitz.open(problem_pdf)
        long_path = "test_" + "a" * 200 + ".pdf"

        doc.save(long_path)
        doc.close()

        if Path(long_path).exists():
            print("✅ 長いパス保存成功")
        else:
            print("❌ 長いパス保存失敗")

    except Exception as e:
        print(f"❌ 長いパスエラー: {e}")

    # 4. Unicode文字を含むファイルパスのテスト
    print("\n4. Unicode文字ファイルパステスト")
    try:
        doc = fitz.open(problem_pdf)
        unicode_path = "テスト用_日本語ファイル名_結合結果.pdf"

        doc.save(unicode_path)
        doc.close()

        if Path(unicode_path).exists():
            print("✅ Unicode パス保存成功")
        else:
            print("❌ Unicode パス保存失敗")

    except Exception as e:
        print(f"❌ Unicode パスエラー: {e}")

    # 5. 一時ディレクトリでの保存テスト
    print("\n5. 一時ディレクトリ保存テスト")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = fitz.open(problem_pdf)
            temp_output = Path(temp_dir) / "temp_output.pdf"

            doc.save(str(temp_output))
            doc.close()

            if temp_output.exists():
                print("✅ 一時ディレクトリ保存成功")
            else:
                print("❌ 一時ディレクトリ保存失敗")

    except Exception as e:
        print(f"❌ 一時ディレクトリエラー: {e}")

    # 6. 権限問題のテスト
    print("\n6. 権限問題テスト")

    # Cドライブルートでの保存試行（権限エラーが予想される）
    try:
        doc = fitz.open(problem_pdf)
        restricted_path = "C:/test_restricted.pdf"

        doc.save(restricted_path)
        doc.close()

        if Path(restricted_path).exists():
            print("✅ 制限パス保存成功（予期しない）")
        else:
            print("⚠️ 制限パス保存失敗（予想通り）")

    except Exception as e:
        print(f"⚠️ 制限パスエラー（予想通り）: {e}")

    # 7. ページ番号付きドキュメントの保存テスト
    print("\n7. ページ番号付きドキュメント保存テスト")
    try:
        # ページ番号を追加したドキュメントを保存
        doc = fitz.open(problem_pdf)

        # 最初のページにページ番号追加
        page = doc[0]
        original_rotation = page.rotation

        if original_rotation != 0:
            page.set_rotation(0)

        page.insert_text((100, 100), "テストページ番号", fontname="cour", fontsize=12)

        if original_rotation != 0:
            page.set_rotation(original_rotation)

        modified_output = "test_with_page_numbers.pdf"
        doc.save(modified_output, deflate=False, garbage=0)
        doc.close()

        if Path(modified_output).exists():
            print("✅ ページ番号付き保存成功")

            # 保存されたファイルを検証
            verify_doc = fitz.open(modified_output)
            verify_text = verify_doc[0].get_text()
            verify_doc.close()

            if "テストページ番号" in verify_text:
                print("✅ ページ番号が正しく保存されました")
            else:
                print("⚠️ ページ番号が見つかりません")
        else:
            print("❌ ページ番号付き保存失敗")

    except Exception as e:
        print(f"❌ ページ番号付き保存エラー: {e}")
        import traceback
        traceback.print_exc()

    # 8. 現在の作業ディレクトリ情報
    print("\n8. 環境情報")
    print(f"現在のディレクトリ: {os.getcwd()}")
    print(f"書き込み権限: {os.access('.', os.W_OK)}")
    print(f"実行権限: {os.access('.', os.X_OK)}")

if __name__ == "__main__":
    test_save_scenarios()