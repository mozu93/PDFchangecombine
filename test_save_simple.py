"""
PDF保存問題の簡易調査
"""
import fitz
import os
from pathlib import Path
import traceback

def test_save_issues():
    """PDF保存問題の調査"""
    print("=== PDF保存問題調査 ===")

    problem_pdf = r"C:\Users\taka\Desktop\12月正副会頭会議資料\【資料1】令和5年度第1回臨時議員総会提案事項について.pdf"

    if not Path(problem_pdf).exists():
        print(f"テストファイルが存在しません: {problem_pdf}")
        return

    print(f"元ファイル: {Path(problem_pdf).name}")
    print(f"元ファイルサイズ: {Path(problem_pdf).stat().st_size:,} bytes")

    # 1. 基本的な保存テスト
    print("\n1. 基本的な保存テスト")
    try:
        doc = fitz.open(problem_pdf)
        basic_output = "test_basic_save.pdf"

        print(f"ページ数: {len(doc)}")
        print(f"最初のページ回転: {doc[0].rotation}度")

        doc.save(basic_output)
        doc.close()

        if Path(basic_output).exists():
            size = Path(basic_output).stat().st_size
            print(f"[SUCCESS] 基本保存: {size:,} bytes")
        else:
            print("[FAILED] 基本保存失敗")

    except Exception as e:
        print(f"[ERROR] 基本保存: {e}")
        traceback.print_exc()

    # 2. 現在のコードと同じオプションで保存
    print("\n2. 現在のコード設定での保存テスト")
    try:
        doc = fitz.open(problem_pdf)
        current_output = "test_current_options.pdf"

        # 現在のコードと同じオプション: garbage=0, deflate=False
        doc.save(current_output, garbage=0, deflate=False)
        doc.close()

        if Path(current_output).exists():
            size = Path(current_output).stat().st_size
            print(f"[SUCCESS] 現在設定保存: {size:,} bytes")
        else:
            print("[FAILED] 現在設定保存失敗")

    except Exception as e:
        print(f"[ERROR] 現在設定保存: {e}")
        traceback.print_exc()

    # 3. ページ番号付きで保存
    print("\n3. ページ番号付き保存テスト")
    try:
        doc = fitz.open(problem_pdf)

        # 最初のページにテストテキスト追加
        page = doc[0]
        original_rotation = page.rotation

        print(f"元の回転: {original_rotation}度")

        # 回転を一時的に0度にしてテキスト追加
        if original_rotation != 0:
            page.set_rotation(0)

        # テストテキスト挿入
        x = page.rect.width / 2
        y = page.rect.height - 50
        page.insert_text((x, y), "TEST-1", fontname="cour", fontsize=12, color=(1, 0, 0))

        # 回転を元に戻す
        if original_rotation != 0:
            page.set_rotation(original_rotation)

        print("テストテキスト挿入完了")

        # 保存
        modified_output = "test_with_modifications.pdf"
        doc.save(modified_output, garbage=0, deflate=False)
        doc.close()

        if Path(modified_output).exists():
            size = Path(modified_output).stat().st_size
            print(f"[SUCCESS] 修正版保存: {size:,} bytes")

            # 保存されたファイルの検証
            verify_doc = fitz.open(modified_output)
            verify_page = verify_doc[0]
            verify_text = verify_page.get_text()
            verify_doc.close()

            if "TEST-1" in verify_text:
                print("[SUCCESS] テキストが正しく保存されました")
            else:
                print("[WARNING] テキストが見つかりません")
                print(f"検出されたテキスト: {len(verify_text)}文字")

        else:
            print("[FAILED] 修正版保存失敗")

    except Exception as e:
        print(f"[ERROR] 修正版保存: {e}")
        traceback.print_exc()

    # 4. 環境情報
    print("\n4. 環境情報")
    try:
        print(f"現在のディレクトリ: {os.getcwd()}")
        print(f"書き込み権限: {os.access('.', os.W_OK)}")

        # ディスク容量チェック（簡易）
        import shutil
        total, used, free = shutil.disk_usage(".")
        print(f"空き容量: {free // (1024**3)} GB")

    except Exception as e:
        print(f"[ERROR] 環境情報取得: {e}")

    # 5. 作成されたファイルの一覧
    print("\n5. 作成されたファイル")
    test_files = ["test_basic_save.pdf", "test_current_options.pdf", "test_with_modifications.pdf"]
    for file in test_files:
        if Path(file).exists():
            size = Path(file).stat().st_size
            print(f"  {file}: {size:,} bytes")
        else:
            print(f"  {file}: [NOT_FOUND]")

if __name__ == "__main__":
    test_save_issues()