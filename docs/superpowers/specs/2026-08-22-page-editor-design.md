# ページ編集機能 設計仕様書

- 日付: 2026-08-22
- 対象: PDFchangecombine
- ステータス: 承認済み（実装計画待ち）

## 背景・目的

現行アプリは「変換」「資料NO挿入」「PDF結合」「ページ番号挿入」の4タブに加え、PDF結合タブ内に「資料を差し替え」機能（資料＝文書単位での差し替え・追加・削除）を持つ。しかし、より細かい**ページ単位**での編集（不要な1ページだけ削除する、スキャンミスで順序が入れ替わったページを直す、別PDFの数ページだけ挿入する等）に対応する手段が無い。

これを解消するため、実際のPDFページをサムネイルで見ながら直接操作できる新タブ「ページ編集」を追加する。

## スコープ

**含む**
- 1つのメインPDFを開き、そのページをサムネイル一覧で確認しながら「削除」「並べ替え」「抽出（別ファイルとして書き出し）」「挿入（別PDFの全ページを指定位置へ）」を行う
- 編集結果を新規PDFとして保存（既存の非破壊出力方針を踏襲。元ファイルは変更しない）

**含まない（今回のスコープ外）**
- 挿入元PDFからのページ選択（常に挿入元PDFの全ページを挿入する。ユーザー確認済み）
- 抽出後に元のページ一覧からページを除去する「カット」動作（抽出は常にコピー。ユーザー確認済み）
- 複数のメインPDFを同時に開いて横断編集すること（1セッション＝1メインPDF）
- 数百ページ級PDFでのサムネイル仮想化・遅延描画（初期実装は全ページ事前レンダリング。パフォーマンス上の問題が実際に確認されてから対応）
- ページの回転・トリミング等、削除・並べ替え・抽出・挿入以外のページ単位編集

## 全体構成

- **新タブ「ページ編集」**: サイドバーに5番目のタブとして追加。アイコン✂️、専用アクセントカラー（既存4色: 青/緑/オレンジ/紫と重複しない新色を`theme.py`に追加）
- **新コアモジュール** `src/core/page_editor.py`: ページ単位の削除・抽出・挿入・並べ替えロジック。PyMuPDF (`fitz`) を使用し、既存`combiner.py`の`fitz.open()` / `insert_pdf()`のイディオムに合わせる
- **新GUIコンポーネント** `src/gui/page_thumbnail_grid.py`: サムネイルグリッド表示・チェックボックス選択・ドラッグ並べ替えを担当する独立ウィジェット
- `unified_window.py`側は他タブと同様に既存の共通処理（`OutputManager.resolve_output_dir`/`get_unique_output_path`、`_apply_output_summary`、`CompletionBanner`、`_resolve_overwrite`）をそのまま再利用する

## コアモジュール（`src/core/page_editor.py`）

### データモデル

```python
@dataclass
class PageRef:
    doc: fitz.Document   # ページの取得元（メインPDF or 挿入元PDF）
    page_index: int      # doc内でのページ番号（0始まり）
```

編集セッション中は `List[PageRef]` を「現在の並び」として保持する。削除・挿入・並べ替えは実際のPDFバイトを操作せず、この参照リストの並べ替え・追加・除去のみで完結させる（軽量・即時反映向き）。挿入元PDFの`fitz.Document`はセッション中クローズせず保持し、保存またはセッション終了時にまとめて解放する。

### 主な関数

| 関数 | シグネチャ | 役割 |
|---|---|---|
| `load_pages` | `(path: str) -> List[PageRef]` | PDFを開き全ページの`PageRef`を生成 |
| `insert_pages` | `(pages: List[PageRef], after_index: int, insert_path: str) -> List[PageRef]` | 指定PDFを開き、全ページ分の`PageRef`を`after_index`の直後に挿入した新リストを返す |
| `delete_pages` | `(pages: List[PageRef], indices: Set[int]) -> List[PageRef]` | 指定インデックスを除いた新リストを返す |
| `reorder_pages` | `(pages: List[PageRef], new_order: List[int]) -> List[PageRef]` | ドラッグ後の並びを反映した新リストを返す |
| `extract_pages` | `(pages: List[PageRef], indices: Set[int], output_path: str) -> PageEditResult` | 選択ページのみを新規PDFとして書き出す（`pages`自体は変更しない） |
| `save_pages` | `(pages: List[PageRef], output_path: str) -> PageEditResult` | 現在の並びを1つの新規PDFとして書き出す。連続する同一doc・連番ページはまとめて`insert_pdf(doc, from_page=, to_page=)`で効率化する |
| `close_session` | `(pages: List[PageRef]) -> None` | セッション終了時に開いている全docをクローズ（同一docの重複クローズを避けるため`set`で去重してから閉じる） |

`close_session`の呼び出しタイミング: (1) 「元に戻す」で`load_pages`を再実行する直前（古いセッションのdocを先にクローズしてから再ロードする）、(2) 「保存」完了後、(3) 新しいメインPDFを読み込む直前、(4) アプリ終了処理（`_on_closing`）。挿入元として現在編集中のメインPDFと同じファイルを指定した場合は、独立した`fitz.Document`ハンドルとして開き別ソースとして扱う（特別扱いは不要）。

`PageEditResult`は既存`CombineResult`と同じ形（`output_path: str`, `success: bool`, `error_message: str`）に揃える。

### エラーハンドリング（コア層）

- 挿入元PDF・メインPDFが存在しない/破損/パスワード保護されている場合、`fitz.open()`の例外を捕捉し、当該関数は例外を再送出せず`PageEditResult(success=False, error_message=...)`（`insert_pages`/`load_pages`は例外送出、呼び出し元GUI層で捕捉）を返すか送出する。GUI層は`error_handler.handle_error(..., ErrorSeverity.WARNING, "ページ挿入")`等でユーザー通知し、その操作だけを中止する（他の状態には影響させない）

## GUIコンポーネント（`src/gui/page_thumbnail_grid.py`）

### サムネイル表示

- 各`PageRef`ごとに`page.get_pixmap(matrix=fitz.Matrix(scale, scale))`で幅150px程度の低解像度サムネイルを生成し`PIL.ImageTk`で表示
- 初期実装ではロード時に全ページをバックグラウンドスレッドで順次レンダリングし、進捗バー「サムネイル読み込み中... (12/48)」を表示する（既存の変換・結合処理と同じ非同期パターン。メインスレッドのUI更新は`root.after`経由）
- サムネイルは`CTkFrame`のグリッドに並べ、各セルに「チェックボックス＋ページ番号ラベル＋サムネイル画像」を配置

### 選択・操作

- チェックボックスで複数選択 → ツールバーに「🗑 削除」「📤 抽出...」ボタン（1件以上選択時に活性化）
- 「➕ この後に挿入...」ボタンは1件だけ選択時のみ活性化（挿入位置の一意性を保つため、0件・複数選択時は無効化）
- ドラッグ&ドロップでサムネイルの並べ替え（`draggable_list.py`のドラッグ中ハイライト・挿入位置表示のロジックを画像グリッド向けに移植）

### その他のUI

- 「↺ 元に戻す」: 読み込み直後の状態に全リセット（`load_pages`を再実行）
- 「💾 保存」: 現在の並びを新規PDFとして出力。保存先サマリー行・完了バナーは他タブの共通部品（`_create_output_summary_row`, `CompletionBanner`）を使用
- 抽出は独立動作のため、実行後も編集中のグリッドはそのまま変化しない

## データフロー

1. PDFをドラッグ&ドロップ／ファイル選択でタブに追加 → `load_pages()`をバックグラウンドスレッドで実行 → サムネイル順次描画
2. ユーザーが削除・挿入・並べ替えを操作 → メモリ上の`List[PageRef]`を即時更新 → グリッド再描画
3. 「保存」→ `save_pages()`をバックグラウンドスレッドで実行 → 完了バナー表示（他タブと同じ「保存先」「フォルダを開く」導線）
4. 「抽出」→ 保存先を選ぶダイアログ（または保存先サマリー行と同様の既定フォルダ）を経て`extract_pages()`を実行 → 簡易完了通知

## エラーハンドリング（GUI層）

- 挿入元PDFがパスワード保護・破損している場合、その挿入操作だけを中止しユーザーに警告表示（他の編集状態は保持）
- 0ページ選択で「削除」「抽出」ボタンをdisabled制御し、実行前バリデーションでも二重チェック
- 大量ページ処理中の進捗表示は既存の`ctk.CTkProgressBar`パターンを踏襲
- 出力先の同名ファイル衝突は既存の`_resolve_overwrite`をそのまま再利用

## テスト方針

- `tests/test_page_editor.py`（新規）: `page_editor.py`のコアロジックを`test_pdfs/`の既存フィクスチャ（`test1.pdf`, `test2.pdf`, `test3.pdf`等）を使いGUI抜きでテスト
  - `load_pages`でページ数・順序が正しいこと
  - `delete_pages`で指定インデックス除外後の並びが正しいこと
  - `insert_pages`で挿入位置・挿入ページ数が正しいこと
  - `reorder_pages`で並び替え結果が正しいこと
  - `extract_pages`/`save_pages`で出力PDFのページ数・内容（先頭ページのテキスト等で簡易検証）が正しいこと
  - 不正な挿入元パス（存在しない/破損PDF）でエラーになることの確認
- GUI部分（`page_thumbnail_grid.py`）はサムネイル生成・選択状態管理など、既存`tests/test_gui_helpers.py`と同程度の軽量な単体テストに留める。実際の描画確認はアプリ起動での目視確認で代替する

## 未確定・今後の検討事項

- 5番目のタブに使うアクセントカラーの具体的な色コードは実装時に決定する（既存4色と衝突しないこと以外は未指定）
- 数百ページ級PDFでのサムネイル読み込み時間が実用上問題になった場合、表示範囲のみ描画する仮想化を別途検討する
