# GUI リデザイン仕様書

**日付:** 2026-05-16  
**対象ファイル:** `src/gui/unified_window.py`, `src/gui/draggable_list.py`

---

## 概要

現状のGUIはチェックボックスを多用しているが、その役割が直感的でない（変換タブでは「削除対象の選択」、結合タブでは「移動・削除対象の選択」）。これを廃止し、行クリック選択＋ホバー削除ボタンに統一することで、操作性とデザイン品質を向上させる。

---

## デザイン決定事項

| 項目 | 決定内容 |
|---|---|
| アプローチ | シンプル行選択型（チェックボックス全廃） |
| カラーテーマ | クリーンブルー（青グラデーションヘッダー、白ベース） |
| 削除操作 | 行クリック複数選択＋ツールバー削除 ＋ ホバー×ボタン（1件即削除） |
| ファイル表示 | 種別バッジ（Word/Excel/PPT/PDF/画像）＋ファイルパス補足 |
| オプション | トグルスイッチ化（CTkSwitch） |

---

## アーキテクチャ

### 変更対象ファイル

- `src/gui/unified_window.py` — メインUI全体
- `src/gui/draggable_list.py` — `DraggableListItem` / `DraggableFileList`

### 変更しないもの

- コア処理（`src/core/converter.py`, `src/core/combiner.py`）
- ドラッグ＆ドロップのロジック（`src/utils/drag_drop.py`）
- ファイルスキャン・セキュリティ検証（`src/utils/`）

---

## コンポーネント設計

### 1. カラー定数（`unified_window.py` 上部に定義）

```python
BLUE_PRIMARY   = ("#2B6CB0", "#3182CE")   # ヘッダー・ボタングラデーション
BLUE_LIGHT     = "#EBF8FF"                # 選択行背景
BLUE_BORDER    = "#90CDF4"                # 選択行ボーダー
BLUE_ACCENT    = "#3182CE"                # 左ボーダーライン・バッジ
WHITE          = "white"
GRAY_BG        = "#F7FAFC"                # ツールバー背景
GRAY_BORDER    = "#E2E8F0"                # 通常ボーダー
RED_LIGHT      = "#FED7D7"                # ×ボタン背景
RED_TEXT       = "#C53030"                # ×ボタン文字
```

### 2. `DraggableListItem`（`draggable_list.py`）

**廃止：**
- `ctk.CTkCheckBox` の削除

**追加：**
- 行全体クリックで選択トグル（`is_selected` フラグ管理は現状維持）
- ホバーで×ボタン（`ctk.CTkButton`）を表示／非表示（`<Enter>` / `<Leave>` イベント）
- ファイル種別バッジラベル（拡張子から自動判定）
- 選択時: 左ボーダー3px `#3182CE` ＋ 背景 `#EBF8FF`
- 非選択時: 透明ボーダー＋白背景

**種別バッジの色定義：**

| 拡張子 | ラベル | 色 |
|---|---|---|
| .docx / .doc | Word | `#3182CE`（青） |
| .xlsx / .xls | Excel | `#38A169`（緑） |
| .pptx / .ppt | PPT | `#DD6B20`（オレンジ） |
| .pdf | PDF | `#E53E3E`（赤） |
| 画像系 | 画像 | `#805AD5`（紫） |

### 3. ツールバー（各タブ共通パターン）

```
[ 📂 ファイル追加 ]  [ ✕ 選択削除 ]  [ 🗑️ 全クリア ]  ... [ N ファイル · M件選択中 ]
```

- ツールバー全体を `CTkFrame`（背景 `#F7FAFC`、ボーダー `#E2E8F0`）で囲む
- ファイルなし時: 「選択削除」「全クリア」を `state="disabled"`
- 選択なし時: 「選択削除」を `state="disabled"`

結合・資料NOタブのみ ↑ ↓ ボタンも同ツールバーに配置。

### 4. ファイルリストコンテナ

- 外枠: `border=1px solid #E2E8F0`, `border-radius=8px`, 白背景
- ヘッダー行: `背景 #EBF8FF`, `border-bottom #BEE3F8`, ラベルテキスト（例: `📁 変換対象ファイル`）

### 5. ヘッダー

CustomTkinterはCSS的なグラデーションに非対応のため、単色で実装する。

```python
ctk.CTkFrame(fg_color="#2B6CB0", corner_radius=6)
# 内部: アイコン(📄) + タイトルテキスト（白）
```

### 6. タブバー

アンダーライン型: 選択タブは下ボーダー `#2B6CB0` (2px) ＋ 青テキスト、非選択はグレー。CustomTkinterの `CTkTabview` の `segmented_button_selected_color` を白系に、選択インジケーターで代替。

### 7. オプション（CTkSwitch）

変換タブの「Excelシート分割」と結合タブの「白紙挿入」「ページ番号」を `CTkCheckBox` → `CTkSwitch` に変更。

**ページ番号オプション:** スイッチON時のみ開始ページ・開始番号の入力欄を有効化（現状ロジック維持）。

---

## 変換タブ固有の変更

**現状:**
- `self.file_checkboxes` でチェックボックスを管理
- 「選択クリア」ボタンがチェック済みのもののみ削除

**変更後:**
- `self.file_checkboxes` を廃止
- ファイルは `DraggableFileList` と同様の行選択UIで管理
- `DraggableFileList` をドラッグ無効モード（`drag_enabled=False`）で流用する。`DraggableListItem` のドラッグイベントを無効化するフラグを追加することで対応。新クラスは作らない。
- 「選択削除」: 選択行のみ `self.conversion_files` から削除

---

## データフローの変更

### 変換タブ

```
変更前: conversion_files[] + file_checkboxes{} → _clear_files()でチェック状態を見て削除
変更後: conversion_files[] + 選択状態list[] → _delete_selected_conversion()で削除
```

### 結合・資料NOタブ

`DraggableFileList` の内部 `selected_files` リストは既存のまま活用。`DraggableListItem` のチェックボックスを行クリック選択に置き換えるのみ。

---

## エラー・エッジケース

- 全ファイル選択中に「選択削除」→ リストが空になる（既存の空状態表示ロジックをそのまま使用）
- ホバー×ボタンによる削除確認ダイアログ: **出さない**（即削除、Undo不要）
- 「全クリア」のみ確認ダイアログを維持

---

## テスト方針

既存のコアロジックは変更しないため、`tests/` のテストはそのまま通るはず。GUIの動作確認は手動で行う：

1. ファイル追加 → 行クリックで選択 → ツールバー削除
2. ファイル行にマウスオーバー → ×ボタン表示 → クリックで即削除
3. 複数選択 → まとめて削除
4. ドラッグ並び替え（結合・資料NOタブ）
5. Excel分割スイッチON/OFF
6. ページ番号スイッチON → 入力欄有効化

---

## 実装しないこと（スコープ外）

- ダークモード最適化（SystemテーマはCustomTkinterに委ねる）
- アニメーション・トランジション
- ファイルプレビュー
- 設定画面・テーマ切り替えUI
