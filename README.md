# PDF変換・結合ツール

Microsoft Officeファイル（Word、Excel、PowerPoint）と画像ファイルをPDFに変換し、複数のPDFファイルを結合するデスクトップアプリケーション

## 機能

### PDF変換機能
- Word (.docx, .doc) → PDF変換
- Excel (.xlsx, .xls) → PDF変換  
- PowerPoint (.pptx, .ppt) → PDF変換
- 画像ファイル (.jpg, .jpeg, .png, .bmp, .gif, .tiff) → PDF変換
- ドラッグ&ドロップによる一括変換
- フォルダ内ファイルの再帰的検索

### PDF結合機能
- 複数PDFファイルの結合
- ドラッグ&ドロップによる順序変更
- ファイル個別削除機能
- 一括クリア機能
- 奇数ページのPDFに白紙ページを挿入するオプション
- フッター中央へのページ番号挿入機能（開始ページ・開始番号指定可）

### 連携機能
- 変換後の自動結合移行
- シームレスなワークフロー

## 技術スタック

- **言語**: Python 3.9+
- **GUIフレームワーク**: CustomTkinter
- **PDF処理**: PyMuPDF, reportlab
- **Office変換**: python-docx, openpyxl, python-pptx
- **画像処理**: Pillow
- **パッケージング**: PyInstaller

## 開発フェーズ

1. **基盤構築**: プロジェクト構造・GUI基盤
2. **コア機能開発**: PDF変換・結合機能
3. **統合・品質向上**: 連携機能・エラーハンドリング・テスト
4. **リリース準備**: パッケージング・コード署名

## 要件

- Python 3.9以上
- Windows 10+ / macOS 10.15+
- 起動時間: 5秒以内
- 変換時間: 10MBファイル 10秒以内
- メモリ使用量: アイドル時 200MB未満

## セットアップ

```bash
# 依存関係インストール
pip install -r requirements.txt

# アプリケーション実行
python src/main.py
```