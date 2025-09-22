# -*- coding: utf-8 -*-
"""
本番配布用ビルドスクリプト
セキュリティチェック、テスト実行、バイナリビルドを自動化
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path
import time

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent

def run_command(command, description, check=True):
    """コマンド実行とエラーハンドリング"""
    print(f"\n🔄 {description}")
    print(f"実行: {command}")

    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        else:
            result = subprocess.run(command, check=check, capture_output=True, text=True)

        if result.stdout:
            print(f"✅ 出力: {result.stdout.strip()}")

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: {e}")
        if e.stdout:
            print(f"標準出力: {e.stdout}")
        if e.stderr:
            print(f"標準エラー: {e.stderr}")
        return False

def check_dependencies():
    """依存関係チェック"""
    print("📋 依存関係チェック")

    required_packages = [
        'customtkinter',
        'PyMuPDF',
        'reportlab',
        'pyinstaller',
        'psutil'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}: インストール済み")
        except ImportError:
            print(f"❌ {package}: 未インストール")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n❌ 不足パッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドで不足パッケージをインストール:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True

def run_security_tests():
    """セキュリティテスト実行"""
    print("\n🔐 セキュリティテスト実行")

    # バンディットによる静的解析（オプション）
    bandit_available = run_command("bandit --version", "Banditセキュリティスキャナー確認", check=False)

    if bandit_available:
        return run_command(
            f"bandit -r {PROJECT_ROOT}/src -f json -o security_report.json",
            "セキュリティ脆弱性スキャン",
            check=False
        )
    else:
        print("ℹ️ Banditが利用できないため、手動セキュリティチェックのみ実行")
        return True

def run_production_tests():
    """本番用テストスイート実行"""
    print("\n🧪 本番用テストスイート実行")

    test_script = PROJECT_ROOT / "tests" / "test_production_ready.py"

    if not test_script.exists():
        print("❌ 本番用テストファイルが見つかりません")
        return False

    return run_command([
        sys.executable, str(test_script)
    ], "包括テストスイート実行")

def update_production_config():
    """本番用設定に更新"""
    print("\n⚙️ 本番用設定に更新")

    config_file = PROJECT_ROOT / "src" / "config.py"

    if not config_file.exists():
        print("❌ 設定ファイルが見つかりません")
        return False

    # バックアップ作成
    backup_file = config_file.with_suffix('.py.dev_backup')
    shutil.copy2(config_file, backup_file)
    print(f"✅ 開発設定をバックアップ: {backup_file}")

    # 本番設定に変更
    content = config_file.read_text(encoding='utf-8')
    content = content.replace('PRODUCTION_MODE = False', 'PRODUCTION_MODE = True')
    content = content.replace('DEBUG_MODE = True', 'DEBUG_MODE = False')

    config_file.write_text(content, encoding='utf-8')
    print("✅ 本番モードに設定変更完了")

    return True

def build_executable():
    """実行ファイルビルド"""
    print("\n🏗️ 実行ファイルビルド")

    main_script = PROJECT_ROOT / "src" / "main.py"

    if not main_script.exists():
        print("❌ メインスクリプトが見つかりません")
        return False

    # PyInstallerコマンド構築
    command = [
        "pyinstaller",
        "--onefile",              # 単一実行ファイル
        "--windowed",             # Windowsアプリ（コンソールなし）
        "--name", "PDF変換結合ツール",
        "--icon", "icon.ico" if (PROJECT_ROOT / "icon.ico").exists() else "",
        "--add-data", f"{PROJECT_ROOT}/src;src",
        "--hidden-import", "customtkinter",
        "--hidden-import", "fitz",
        "--hidden-import", "reportlab",
        str(main_script)
    ]

    # アイコンファイルがない場合は除外
    if not (PROJECT_ROOT / "icon.ico").exists():
        command = [cmd for cmd in command if cmd != "--icon" and not cmd.endswith("icon.ico")]

    return run_command(command, "PyInstallerによる実行ファイルビルド")

def create_distribution_package():
    """配布パッケージ作成"""
    print("\n📦 配布パッケージ作成")

    dist_dir = PROJECT_ROOT / "dist"
    package_dir = PROJECT_ROOT / "PDF変換結合ツール_v1.0.0"

    if package_dir.exists():
        shutil.rmtree(package_dir)

    package_dir.mkdir()

    # 実行ファイルコピー
    exe_file = dist_dir / "PDF変換結合ツール.exe"
    if exe_file.exists():
        shutil.copy2(exe_file, package_dir)
        print("✅ 実行ファイルをコピー")
    else:
        print("❌ 実行ファイルが見つかりません")
        return False

    # ドキュメントコピー
    docs_to_copy = [
        "README.md",
        "PRODUCTION_DEPLOYMENT.md",
        "LICENSE"
    ]

    for doc in docs_to_copy:
        doc_path = PROJECT_ROOT / doc
        if doc_path.exists():
            shutil.copy2(doc_path, package_dir)
            print(f"✅ {doc} をコピー")

    # 配布用ZIPファイル作成
    zip_path = PROJECT_ROOT / "PDF変換結合ツール_v1.0.0"
    shutil.make_archive(str(zip_path), 'zip', str(package_dir))
    print(f"✅ 配布用ZIPファイル作成: {zip_path}.zip")

    return True

def restore_dev_config():
    """開発設定に復元"""
    print("\n🔄 開発設定に復元")

    config_file = PROJECT_ROOT / "src" / "config.py"
    backup_file = config_file.with_suffix('.py.dev_backup')

    if backup_file.exists():
        shutil.copy2(backup_file, config_file)
        backup_file.unlink()
        print("✅ 開発設定に復元完了")
        return True
    else:
        print("⚠️ バックアップファイルが見つかりません")
        return False

def main():
    """メインビルドプロセス"""
    print("🚀 PDF変換・結合ツール - 本番配布ビルド開始")
    print("=" * 60)

    start_time = time.time()

    try:
        # 1. 依存関係チェック
        if not check_dependencies():
            print("❌ 依存関係チェック失敗")
            return False

        # 2. セキュリティテスト
        if not run_security_tests():
            print("⚠️ セキュリティテストで問題が検出されました")
            # 続行するかユーザーに確認
            response = input("続行しますか? (y/N): ")
            if response.lower() != 'y':
                return False

        # 3. 本番用テスト実行
        if not run_production_tests():
            print("❌ 本番用テスト失敗")
            return False

        # 4. 本番用設定に更新
        if not update_production_config():
            print("❌ 本番設定更新失敗")
            return False

        # 5. 実行ファイルビルド
        if not build_executable():
            print("❌ 実行ファイルビルド失敗")
            return False

        # 6. 配布パッケージ作成
        if not create_distribution_package():
            print("❌ 配布パッケージ作成失敗")
            return False

        # 成功
        build_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("🎉 本番配布ビルド完了！")
        print(f"⏱️ ビルド時間: {build_time:.2f}秒")
        print("📦 配布ファイル: PDF変換結合ツール_v1.0.0.zip")
        print("📋 配布前に PRODUCTION_DEPLOYMENT.md を必ず確認してください")
        return True

    except KeyboardInterrupt:
        print("\n❌ ビルドが中断されました")
        return False

    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        return False

    finally:
        # 開発設定に復元
        restore_dev_config()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)