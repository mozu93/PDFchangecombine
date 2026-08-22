# PDF変換・結合ツール

Microsoft Officeファイル（Word、Excel、PowerPoint）と画像ファイルをPDFに変換し、複数のPDFファイルを結合するデスクトップアプリケーション

> ⚠️ **Word・Excel・PowerPointへの変換にはMicrosoft Office（デスクトップ版）のインストールが必須です。**
> 変換処理はOffice本体のCOM APIを直接呼び出しており、Officeが無い環境ではこれらの変換は動作しません（PDF結合・画像変換・資料NO/ページ番号挿入はOffice不要）。

## ダウンロード

最新版のインストーラーは [Releases](https://github.com/mozu93/PDFchangecombine/releases/latest) から入手できます（`PDFConverter-setup.exe`）。

## 📖 ユーザーガイド

- **🚀 [クイックスタート](QUICK_START.md)**: 5分で基本操作を習得
- **📚 [詳細マニュアル](USER_MANUAL.md)**: 全機能の詳しい使い方
- **🛠️ [運用ガイド](PRODUCTION_DEPLOYMENT.md)**: 本番環境での配布・運用

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
- ドラッグ&ドロップによる順序変更（挿入位置を視覚的にハイライト表示）
- ファイル個別削除機能
- 一括クリア機能
- 奇数ページのPDFに白紙ページを挿入するオプション
- フッター中央へのページ番号挿入機能（開始ページ・開始番号指定可）
- 出力先に同名ファイルがある場合の上書き確認

### 資料構成変更機能（資料を差し替え...）
- 結合済みPDFの資料単位での差し替え・追加・削除
- 資料番号の一括リナンバリング
- 複数の変更をまとめて積み上げ、1回の実行で1つの出力ファイルに反映

### 資料番号挿入機能
- PDFに「資料1」「資料2」等の番号を自動挿入
- 任意番号モード（単一ファイル用）
- 連番モード（指定番号からの連続番号）
- ハイフン連番モード（プレフィックス付き連番）
- 全回転角度対応（0°/90°/180°/270°）
- 日本語フォント完全対応

### 連携機能
- 変換後の自動結合移行
- シームレスなワークフロー

## 技術スタック

- **言語**: Python 3.9+
- **GUIフレームワーク**: CustomTkinter
- **PDF処理**: PyMuPDF, reportlab
- **Office変換**: pywin32（Microsoft Office COM API、Word/Excel/PowerPoint本体を直接操作）
- **画像処理**: Pillow
- **パッケージング**: PyInstaller + Inno Setup

## 開発フェーズ

1. **基盤構築**: プロジェクト構造・GUI基盤
2. **コア機能開発**: PDF変換・結合機能
3. **統合・品質向上**: 連携機能・エラーハンドリング・テスト
4. **リリース準備**: パッケージング・コード署名

## 要件

- Windows 10/11 (64bit)
- Word/Excel/PowerPoint変換を使う場合はMicrosoft Office（デスクトップ版）が別途必要
- 起動時間: 5秒以内
- 変換時間: 10MBファイル 10秒以内
- メモリ使用量: アイドル時 200MB未満

インストーラー版（[Releases](https://github.com/mozu93/PDFchangecombine/releases/latest)）を使う場合、Pythonのインストールは不要です。

## 開発環境セットアップ

- Python 3.9以上

```bash
# 依存関係インストール
pip install -r requirements.txt

# アプリケーション実行
python src/main.py

# テスト実行
python -m pytest tests/ -q
```

## ライセンス

[MIT License](LICENSE)