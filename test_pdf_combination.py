#!/usr/bin/env python3
"""
PDF結合機能テストスクリプト
"""

import sys
import os
from pathlib import Path

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.combiner import PDFCombiner
from src.utils.logger import logger

def test_pdf_combination():
    """PDF結合機能のテスト"""
    
    print("=== PDF結合機能テスト開始 ===")
    
    # テストファイルのパス
    test_dir = Path("test_pdfs")
    pdf_files = [
        str(test_dir / "test1.pdf"),
        str(test_dir / "test2.pdf"),
        str(test_dir / "test3.pdf")
    ]
    
    # 出力ファイル
    output_path = str(test_dir / "combined_test.pdf")
    
    # ファイルの存在確認
    print("\n1. テストファイルの存在確認:")
    for pdf_file in pdf_files:
        if Path(pdf_file).exists():
            file_size = Path(pdf_file).stat().st_size
            print(f"  OK {pdf_file} (サイズ: {file_size} bytes)")
        else:
            print(f"  NG {pdf_file} が見つかりません")
            return False
    
    # PDF結合実行
    print("\n2. PDF結合実行:")
    try:
        combiner = PDFCombiner()
        
        def progress_callback(message, progress):
            print(f"  進捗: {message} ({progress:.1f}%)")
        
        result = combiner.combine_pdfs(pdf_files, output_path, progress_callback)
        
        # 結果確認
        print("\n3. 結合結果:")
        if result.success:
            print(f"  OK 結合成功: {result.output_path}")
            print(f"  OK 処理ファイル数: {len(result.processed_files)}")
            print(f"  OK 総ページ数: {result.total_pages}")
            print(f"  OK 処理時間: {result.processing_time:.2f}秒")
            
            # 出力ファイルサイズ確認
            if Path(output_path).exists():
                output_size = Path(output_path).stat().st_size
                print(f"  OK 出力ファイルサイズ: {output_size} bytes")
            
            return True
        else:
            print(f"  NG 結合失敗: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"  NG 例外発生: {str(e)}")
        return False

def test_pdf_info():
    """PDF情報取得のテスト"""
    
    print("\n=== PDF情報取得テスト ===")
    
    test_dir = Path("test_pdfs")
    pdf_files = ["test1.pdf", "test2.pdf", "test3.pdf"]
    
    try:
        combiner = PDFCombiner()
        
        for pdf_file in pdf_files:
            pdf_path = str(test_dir / pdf_file)
            if Path(pdf_path).exists():
                info = combiner.get_pdf_info(pdf_path)
                print(f"\n{pdf_file}:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  NG {pdf_file} が見つかりません")
                
    except Exception as e:
        print(f"例外発生: {str(e)}")

if __name__ == "__main__":
    # PDF結合テスト
    success = test_pdf_combination()
    
    # PDF情報取得テスト
    test_pdf_info()
    
    print(f"\n=== テスト完了 ===")
    print(f"結果: {'成功' if success else '失敗'}")