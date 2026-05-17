#!/usr/bin/env python3
"""
実行ファイルビルドスクリプト
要件定義書 5.7.配布・更新要件に基づく実行ファイル生成
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

def check_dependencies():
    """必要な依存関係チェック"""
    print("依存関係チェック中...")
    
    required_packages = [
        'pyinstaller',
        'customtkinter',
        'tkinterdnd2',
        'pillow',
        'reportlab',
        'PyMuPDF',
        'python-docx',
        'openpyxl',
        'python-pptx'
    ]
    
    missing_packages = []

    # パッケージ名とインポート名のマッピング
    import_mapping = {
        'pyinstaller': 'PyInstaller',
        'customtkinter': 'customtkinter',
        'tkinterdnd2': 'tkinterdnd2',
        'pillow': 'PIL',
        'reportlab': 'reportlab',
        'PyMuPDF': 'fitz',
        'python-docx': 'docx',
        'openpyxl': 'openpyxl',
        'python-pptx': 'pptx'
    }

    for package in required_packages:
        try:
            import_name = import_mapping.get(package, package.replace('-', '_'))
            __import__(import_name)
            print(f"  OK {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  NG {package}")

    if missing_packages:
        print(f"\\n未インストールパッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    print("全ての依存関係が満たされています\\n")
    return True

def clean_build_directories():
    """ビルドディレクトリのクリーンアップ"""
    print("ビルドディレクトリクリーンアップ中...")
    
    cleanup_dirs = ['build/work', 'dist', '__pycache__']
    cleanup_files = ['*.spec']
    
    for dir_path in cleanup_dirs:
        if Path(dir_path).exists():
            shutil.rmtree(dir_path)
            print(f"  削除: {dir_path}")
    
    for pattern in cleanup_files:
        for file_path in Path('.').glob(pattern):
            file_path.unlink()
            print(f"  削除: {file_path}")

    print("クリーンアップ完了\\n")

def build_executable():
    """実行ファイルビルド実行"""
    print("実行ファイルビルド開始...")
    
    # PyInstallerコマンド構築（ワンフォルダ形式）
    cmd = [
        'pyinstaller',
        '--onedir',  # ワンフォルダ形式に変更
        '--noconsole',
        '--name=PDFConverter',
        '--distpath=dist',
        '--workpath=build/work',
        '--specpath=build',
        
        # パス設定
        f'--path={PROJECT_ROOT}',
        f'--path={PROJECT_ROOT / "src"}',
        
        # 隠蔽インポート
        '--hidden-import=customtkinter',
        '--hidden-import=tkinterdnd2',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=reportlab',
        '--hidden-import=reportlab.pdfgen.canvas',
        '--hidden-import=fitz',
        '--hidden-import=PyMuPDF',
        '--hidden-import=docx',
        '--hidden-import=openpyxl',
        '--hidden-import=pptx',
        
        # 除外モジュール
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=pytest',
        
        # メインスクリプト
        str(PROJECT_ROOT / 'src' / 'main.py')
    ]
    
    # Windowsの場合はバージョン情報追加
    if sys.platform.startswith('win'):
        version_file = create_version_file()
        if version_file.exists():
            cmd.append(f'--version-file={version_file}')
    
    # ビルド実行
    print(f"実行コマンド: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\\nビルド完了!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\\nビルドエラー: {e}")
        return False

def create_version_file():
    """Windowsバージョン情報ファイル作成"""
    version_content = '''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(u'040904B0', [
        StringStruct(u'CompanyName', u'PDF Tools'),
        StringStruct(u'FileDescription', u'PDF変換・結合ツール'),
        StringStruct(u'FileVersion', u'1.14.1'),
        StringStruct(u'InternalName', u'PDFConverter'),
        StringStruct(u'LegalCopyright', u'© 2025 PDF Tools'),
        StringStruct(u'OriginalFilename', u'PDFConverter.exe'),
        StringStruct(u'ProductName', u'PDF変換・結合ツール'),
        StringStruct(u'ProductVersion', u'1.14.1')
      ])
    ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    version_file = PROJECT_ROOT / 'build' / 'version_info.txt'
    version_file.parent.mkdir(exist_ok=True)
    
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(version_content)
    
    return version_file

def verify_build():
    """ビルド結果検証"""
    print("\\nビルド結果検証中...")

    # ワンフォルダ形式の場合のパス
    if sys.platform.startswith('win'):
        exe_path = PROJECT_ROOT / 'dist' / 'PDFConverter' / 'PDFConverter.exe'
        dist_folder = PROJECT_ROOT / 'dist' / 'PDFConverter'
    elif sys.platform.startswith('darwin'):
        exe_path = PROJECT_ROOT / 'dist' / 'PDFConverter' / 'PDFConverter'  # macOS
        dist_folder = PROJECT_ROOT / 'dist' / 'PDFConverter'
    else:
        exe_path = PROJECT_ROOT / 'dist' / 'PDFConverter' / 'PDFConverter'  # Linux
        dist_folder = PROJECT_ROOT / 'dist' / 'PDFConverter'
    
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        print(f"実行ファイル生成成功: {exe_path}")
        print(f"実行ファイルサイズ: {file_size:.1f} MB")

        # 配布フォルダのサイズ確認
        if dist_folder.exists():
            total_size = sum(f.stat().st_size for f in dist_folder.rglob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            file_count = len(list(dist_folder.rglob('*')))
            print(f"配布フォルダサイズ: {total_size_mb:.1f} MB ({file_count} ファイル)")
            print(f"配布フォルダ: {dist_folder}")

        # 実行権限確認 (Unix系)
        if not sys.platform.startswith('win'):
            if os.access(exe_path, os.X_OK):
                print("実行権限: OK")
            else:
                print("実行権限: なし（chmod +x が必要）")

        return True
    else:
        print(f"実行ファイルが見つかりません: {exe_path}")
        return False

def main():
    """メイン処理"""
    print("PDF変換・結合ツール ビルドスクリプト")
    print("=" * 50)
    
    # 前処理
    if not check_dependencies():
        sys.exit(1)
    
    clean_build_directories()
    
    # ビルド実行
    if not build_executable():
        print("\\nビルドに失敗しました")
        sys.exit(1)
    
    # 検証
    if verify_build():
        print("\\nビルド成功! dist/フォルダを確認してください")
        
        # 次のステップ案内
        print("\\n次のステップ:")
        print("  1. dist/PDFConverter フォルダ全体をテスト環境にコピー")
        print("  2. PDFConverter.exe をテスト実行")
        print("  3. 各種ファイル形式での変換テスト")
        print("  4. PDF結合機能のテスト")
        print("  5. エラーハンドリングの確認")
        
        # 配布準備
        if sys.platform.startswith('win'):
            print("  6. コード署名の実施 (signtool)")
        
    else:
        print("\\nビルド検証に失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main()