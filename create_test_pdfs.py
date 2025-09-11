#!/usr/bin/env python3
"""
テスト用PDFファイル作成スクリプト
PDF結合機能のテスト用に複数のPDFファイルを作成
"""

import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def create_test_pdfs():
    """テスト用PDFファイルを作成"""
    
    # テストディレクトリ作成
    test_dir = Path("test_pdfs")
    test_dir.mkdir(exist_ok=True)
    
    # 3つのテスト用PDFを作成
    pdf_configs = [
        {
            "filename": "test1.pdf",
            "title": "テストPDF 1",
            "content": ["これは最初のテストPDFです。", "PDF結合機能のテスト用です。", "ページ1の内容です。"]
        },
        {
            "filename": "test2.pdf", 
            "title": "テストPDF 2",
            "content": ["これは2番目のテストPDFです。", "結合テスト用のサンプルです。", "ページ2の内容です。"]
        },
        {
            "filename": "test3.pdf",
            "title": "テストPDF 3", 
            "content": ["これは3番目のテストPDFです。", "最後のテストファイルです。", "ページ3の内容です。"]
        }
    ]
    
    for config in pdf_configs:
        pdf_path = test_dir / config["filename"]
        
        # PDFを作成
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4
        
        # タイトル
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 100, config["title"])
        
        # 内容
        c.setFont("Helvetica", 12)
        y_position = height - 150
        
        for line in config["content"]:
            c.drawString(50, y_position, line)
            y_position -= 25
        
        # ページ番号
        c.setFont("Helvetica", 10)
        c.drawString(width - 100, 50, f"Page 1")
        
        c.save()
        print(f"作成完了: {pdf_path}")
    
    print(f"\nテスト用PDFファイルが {test_dir} に作成されました。")
    return test_dir

if __name__ == "__main__":
    create_test_pdfs()