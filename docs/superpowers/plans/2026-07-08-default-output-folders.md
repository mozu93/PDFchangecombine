# 出力先の既定フォルダ化・永続化廃止 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 出力先の記憶を廃止し、既定で「変換元フォルダ配下の機能別フォルダ(PDF変換済/資料NO挿入済/PDF結合済/ページ番号挿入済)」に保存する。PDF結合のファイル名を `【結合】先頭ファイル名.pdf` に変更する。

**Architecture:** 出力先の解決(手動指定 or 既定サブフォルダ)を `OutputManager.resolve_output_dir` に集約し、GUI側は実行直前に解決・フォルダ作成して具体パスをコア処理へ渡す。コア処理(converter/combiner)のインターフェースは変更しない。

**Tech Stack:** Python 3.11 / customtkinter / pytest

**Spec:** `docs/superpowers/specs/2026-07-07-default-output-folders-design.md`

## Global Constraints

- 既定フォルダ名(正確に): PDF変換 → `PDF変換済`、資料NO挿入 → `資料NO挿入済`、PDF結合 → `PDF結合済`、ページ番号挿入 → `ページ番号挿入済`
- 基準は**リスト先頭のファイルの親フォルダ**
- 手動指定(📂 変更)時はそのフォルダ**直下**に保存(サブフォルダを作らない)。指定はアプリ終了まで有効
- 既定フォルダ作成失敗時はエラー表示して中断(親フォルダへ黙ってフォールバックしない)
- 既存の `OUTPUT_FOLDER_NAME = "変換済"`(コア側フォールバック・要件F-104)と `SOURCE_ARCHIVE_FOLDER_NAME = "変換元"`(退避)は変更しない
- コミットメッセージは日本語・Conventional Commits 形式(既存リポジトリの慣例)

---

### Task 1: 出力先解決ヘルパーと機能別フォルダ名定数(TDD)

**Files:**
- Modify: `src/config.py:41` 付近(定数追加)
- Modify: `src/utils/file_utils.py`(`OutputManager` にメソッド追加)
- Test: `tests/test_file_utils.py`

**Interfaces:**
- Produces: `OutputManager.resolve_output_dir(override: str, files: List[str], subfolder_name: str) -> str`
  (override非空→そのまま返す / files空→`""` / それ以外→`str(Path(files[0]).parent / subfolder_name)`)
- Produces: `src/config.py` の定数
  `CONVERSION_OUTPUT_FOLDER_NAME = "PDF変換済"`, `DOCUMENT_OUTPUT_FOLDER_NAME = "資料NO挿入済"`,
  `COMBINATION_OUTPUT_FOLDER_NAME = "PDF結合済"`, `PAGENUMBER_OUTPUT_FOLDER_NAME = "ページ番号挿入済"`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_file_utils.py` の末尾(既存クラスの外)に追加:

```python
class TestResolveOutputDir:
    """resolve_output_dir のテスト"""

    def test_手動指定があればそのまま返す(self):
        result = OutputManager.resolve_output_dir(
            r"C:\out", [r"C:\src\a.pdf"], "PDF変換済")
        assert result == r"C:\out"

    def test_未指定なら先頭ファイルの親フォルダ配下のサブフォルダ(self):
        result = OutputManager.resolve_output_dir(
            "", [str(Path("C:/src/a.pdf")), str(Path("D:/other/b.pdf"))], "PDF変換済")
        assert result == str(Path("C:/src") / "PDF変換済")

    def test_ファイルなしなら空文字(self):
        assert OutputManager.resolve_output_dir("", [], "PDF変換済") == ""
```

ファイル冒頭の import に `Path`・`OutputManager` が既にあることを確認(`from pathlib import Path` がなければ追加)。

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_file_utils.py -k ResolveOutputDir -v`
Expected: FAIL(`AttributeError: ... has no attribute 'resolve_output_dir'`)

- [ ] **Step 3: 実装**

`src/config.py` の `OUTPUT_FOLDER_NAME = "変換済"` の直後に追加:

```python
# 機能別の既定出力フォルダ名（変換元ファイルの親フォルダ配下に作成）
CONVERSION_OUTPUT_FOLDER_NAME = "PDF変換済"
DOCUMENT_OUTPUT_FOLDER_NAME = "資料NO挿入済"
COMBINATION_OUTPUT_FOLDER_NAME = "PDF結合済"
PAGENUMBER_OUTPUT_FOLDER_NAME = "ページ番号挿入済"
```

`src/utils/file_utils.py` の `OutputManager` クラス(`get_unique_output_path` の後)に追加。
`from typing import List` が冒頭になければ追加:

```python
    @staticmethod
    def resolve_output_dir(override: str, files: List[str], subfolder_name: str) -> str:
        """
        出力先フォルダを解決する。

        Args:
            override: 手動指定された出力先（空文字なら既定動作）
            files: 対象ファイルのリスト（先頭ファイルの親フォルダが基準）
            subfolder_name: 既定時に作成する機能別フォルダ名

        Returns:
            str: 解決済み出力先パス。files が空で override も無い場合は空文字
        """
        if override:
            return override
        if not files:
            return ""
        return str(Path(files[0]).parent / subfolder_name)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_file_utils.py -v`
Expected: 全件 PASS(既存テスト含む)

- [ ] **Step 5: コミット**

```bash
git add src/config.py src/utils/file_utils.py tests/test_file_utils.py
git commit -m "feat: 出力先解決ヘルパーと機能別フォルダ名定数を追加"
```

---

### Task 2: 出力先の永続化を廃止

**Files:**
- Modify: `src/utils/settings.py:23-27`
- Modify: `src/gui/unified_window.py:2866-2875`(`_apply_settings`)、`src/gui/unified_window.py:2893-2899`(`_collect_current_settings`)

**Interfaces:**
- Consumes: なし
- Produces: `settings.json` から `conversion_output_dir` / `document_output_dir` / `combination_output_dir` / `pagenumber_output_dir` が消える(読み込み時、旧ファイルの残存キーは `load_settings()` の既知キーマージにより自然に無視される)

- [ ] **Step 1: `DEFAULT_SETTINGS` から4キーを削除**

`src/utils/settings.py` の `DEFAULT_SETTINGS` から以下4行を削除:

```python
    "conversion_output_dir": "",
    "document_output_dir": "",
    "combination_output_dir": "",
    "pagenumber_output_dir": "",
```

- [ ] **Step 2: `_apply_settings` から復元処理を削除**

`src/gui/unified_window.py` `_apply_settings` 内の以下4行を削除
(**注意**: 直後の `_update_*_output_dir_label()` 4行は起動時のラベル初期化に必要なので残す):

```python
        self.conversion_output_dir = s.get("conversion_output_dir", "")
        self.document_output_dir = s.get("document_output_dir", "")
        self.combination_output_dir = s.get("combination_output_dir", "")
        self.pagenumber_output_dir = s.get("pagenumber_output_dir", "")
```

- [ ] **Step 3: `_collect_current_settings` から4項目を削除**

```python
            "conversion_output_dir": self.conversion_output_dir,
            "document_output_dir": self.document_output_dir,
            "combination_output_dir": self.combination_output_dir,
            "pagenumber_output_dir": self.pagenumber_output_dir,
```

- [ ] **Step 4: 検証**

Run: `python -m py_compile src/utils/settings.py src/gui/unified_window.py && python -m pytest tests/ -q`
Expected: コンパイル成功、全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/utils/settings.py src/gui/unified_window.py
git commit -m "feat: 出力先フォルダの永続化を廃止（毎回既定に戻す）"
```

---

### Task 3: ファイル追加時の自動セット削除とラベル表示の更新

**Files:**
- Modify: `src/gui/unified_window.py`(auto-set 4箇所、ラベル更新関数4つ、`_update_*_display` 3つ、`_set_pagenumber_file`/`_clear_pagenumber_file`、ツールチップ4箇所、import)

**Interfaces:**
- Consumes: Task 1 の `OutputManager.resolve_output_dir` と config 定数4つ
- Produces: `self.*_output_dir` は「手動指定があった場合のみ非空」という不変条件

- [ ] **Step 1: import を追加**

`src/gui/unified_window.py` 冒頭の `from ..config import ...`(既存の import 群)に4定数を追加:
`CONVERSION_OUTPUT_FOLDER_NAME, DOCUMENT_OUTPUT_FOLDER_NAME, COMBINATION_OUTPUT_FOLDER_NAME, PAGENUMBER_OUTPUT_FOLDER_NAME`
(config からの import が無い場合は `from ..config import` 行を新設。`OutputManager` は既に import 済みであることを確認)

- [ ] **Step 2: ファイル追加時の自動セット4箇所を削除**

以下の4ブロックを削除する:

`_add_conversion_files` 内(1296-1299付近):
```python
                # 出力先未設定の場合は最初のファイルの親フォルダを自動設定
                if not self.conversion_output_dir:
                    self.conversion_output_dir = str(Path(new_files[0]).parent)
                    self._update_conversion_output_dir_label()
```

結合タブのファイル追加内(1321-1324付近):
```python
                # 出力先未設定の場合は最初のファイルの親フォルダを自動設定
                if not self.combination_output_dir:
                    self.combination_output_dir = str(Path(new_files[0]).parent)
                    self._update_combination_output_dir_label()
```

資料NO挿入タブのファイル追加内(1437-1440付近):
```python
                    # 出力先未設定の場合は最初のファイルの親フォルダを自動設定
                    if not self.document_output_dir:
                        self.document_output_dir = str(Path(new_files[0]).parent)
                        self._update_document_output_dir_label()
```

`_set_pagenumber_file` 内(2679-2681付近):
```python
        if not self.pagenumber_output_dir:
            self.pagenumber_output_dir = str(Path(path).parent)
            self._update_pagenumber_output_dir_label()
```

- [ ] **Step 3: ラベル更新関数4つを新仕様に書き換え**

表示ルール: 手動指定→指定パス / 未指定+ファイルあり→解決済み既定パス / 未指定+ファイルなし→説明文。
4関数(`_update_conversion_output_dir_label` ほか)を以下の形に書き換える:

```python
    def _update_conversion_output_dir_label(self) -> None:
        resolved = OutputManager.resolve_output_dir(
            self.conversion_output_dir, self.conversion_files, CONVERSION_OUTPUT_FOLDER_NAME)
        if resolved:
            self.conversion_output_dir_label.configure(
                text=self._shorten_path(resolved), text_color=CLR_DARK_TEXT)
        else:
            self.conversion_output_dir_label.configure(
                text="変換元フォルダ内に「PDF変換済」を作成（既定）", text_color=CLR_GRAY_TEXT)
```

同様に:
- `_update_combination_output_dir_label`: `self.combination_files` / `COMBINATION_OUTPUT_FOLDER_NAME` / 説明文「変換元フォルダ内に「PDF結合済」を作成（既定）」
- `_update_document_output_dir_label`: `self.document_number_files` / `DOCUMENT_OUTPUT_FOLDER_NAME` / 説明文「変換元フォルダ内に「資料NO挿入済」を作成（既定）」
- `_update_pagenumber_output_dir_label`: `self.pagenumber_files` / `PAGENUMBER_OUTPUT_FOLDER_NAME` / 説明文「元ファイルのフォルダ内に「ページ番号挿入済」を作成（既定）」

- [ ] **Step 4: リスト変化時にラベルを更新**

- `_update_conversion_display`(1891付近)の末尾に `self._update_conversion_output_dir_label()` を追加
- `_update_combination_display`(1914付近)の末尾に `self._update_combination_output_dir_label()` を追加
- `_update_document_number_display`(1659付近)の末尾に `self._update_document_output_dir_label()` を追加
- `_set_pagenumber_file`(2667付近)の末尾に `self._update_pagenumber_output_dir_label()` を追加
- `_clear_pagenumber_file`(2683付近)の末尾に `self._update_pagenumber_output_dir_label()` を追加

- [ ] **Step 5: ツールチップの表示値を解決済みパスに変更**

4箇所の `_attach_tooltip(..., lambda: self.*_output_dir)`(404, 580, 819, 2502付近)を、
Step 3 と同じ解決結果を返す lambda に変更:

```python
        self._attach_tooltip(self.conversion_output_dir_label,
            lambda: OutputManager.resolve_output_dir(
                self.conversion_output_dir, self.conversion_files, CONVERSION_OUTPUT_FOLDER_NAME))
```
(他3タブも対応するリスト・定数で同様)

- [ ] **Step 6: 検証**

Run: `python -m py_compile src/gui/unified_window.py && python -m pytest tests/ -q`
Expected: コンパイル成功、全テスト PASS

- [ ] **Step 7: コミット**

```bash
git add src/gui/unified_window.py
git commit -m "feat: 出力先の自動セットを廃止し既定フォルダをラベル表示"
```

---

### Task 4: 実行時の出力先解決(4機能)と結合ファイル名変更

**Files:**
- Modify: `src/gui/unified_window.py`(`_prepare_output_dir` 新設、変換・結合・資料NO・ページ番号の実行パス)

**Interfaces:**
- Consumes: Task 1 のヘルパー・定数、Task 3 の不変条件
- Produces: `self._prepare_output_dir(override: str, files: List[str], subfolder_name: str) -> Optional[str]`
  (解決+`mkdir(parents=True, exist_ok=True)`。失敗時はエラー表示して `None`)

- [ ] **Step 1: `_prepare_output_dir` ヘルパーを追加**

`_change_conversion_output_dir`(2032付近)の直前に追加:

```python
    def _prepare_output_dir(self, override: str, files: List[str], subfolder_name: str) -> Optional[str]:
        """実行直前に出力先を解決し、フォルダを作成して返す。作成失敗時は None"""
        out_dir = OutputManager.resolve_output_dir(override, files, subfolder_name)
        if not out_dir:
            return None
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_handler.handle_error(
                e, ErrorSeverity.WARNING, "出力先フォルダ作成",
                f"出力先フォルダを作成できませんでした:\n{out_dir}")
            return None
        return out_dir
```

- [ ] **Step 2: PDF変換の実行パスを変更**

`_start_conversion`(2118付近)の `if not files_to_convert: return` の直後に追加:

```python
        out_dir = self._prepare_output_dir(
            self.conversion_output_dir, files_to_convert, CONVERSION_OUTPUT_FOLDER_NAME)
        if not out_dir:
            return
```

スレッド起動を `args=(list(files_to_convert), out_dir)` に変更し、
`_run_conversion` のシグネチャを `def _run_conversion(self, files_to_convert: List[str], out_dir: str) -> None:` に、
2183付近の呼び出しを次に変更:

```python
                result = self.pdf_converter._convert_single_file(file_path, split_sheets, out_dir)
```

- [ ] **Step 3: PDF結合の出力先とファイル名を変更**

2292-2299付近を以下に置き換え(`from datetime import datetime` と timestamp 行は削除):

```python
        # 出力先を解決（未指定なら 先頭ファイルの親フォルダ\PDF結合済）
        out_dir = self._prepare_output_dir(
            self.combination_output_dir, self.combination_files, COMBINATION_OUTPUT_FOLDER_NAME)
        if not out_dir:
            return

        # 先頭ファイル名から出力ファイル名を生成（同名があれば連番付与）
        filename = f"【結合】{Path(self.combination_files[0]).stem}.pdf"
        output_path = OutputManager.get_unique_output_path(out_dir, filename)
```

- [ ] **Step 4: 資料NO挿入の実行パスを変更**

`_start_sequential_number_insertion`(1685付近)で:

1. 確認ダイアログ表示前(1740付近)の `out_dir_disp = ...` を以下に置き換え:

```python
            out_dir = self._prepare_output_dir(
                self.document_output_dir, self.document_number_files, DOCUMENT_OUTPUT_FOLDER_NAME)
            if not out_dir:
                return
            out_dir_disp = out_dir
```

2. スレッド起動(1769付近)の `args` 末尾に `out_dir` を追加:

```python
            thread = threading.Thread(target=self._run_sequential_number_insertion, args=(prefix, numbering_type, number_value, rename_file, a3_compat, selected_font, insert_all_pages, doc_font_size, out_dir))
```

3. `_run_sequential_number_insertion`(1781付近)のシグネチャ末尾に `out_dir: str = ""` を追加し、
   1801付近と1820付近の `output_dir=self.document_output_dir,` を両方 `output_dir=out_dir,` に変更。

- [ ] **Step 5: ページ番号挿入の実行パスを変更**

1. 確認ダイアログ前(2706付近)の `out_dir_disp = ...` を以下に置き換え:

```python
        out_dir = self._prepare_output_dir(
            self.pagenumber_output_dir, self.pagenumber_files, PAGENUMBER_OUTPUT_FOLDER_NAME)
        if not out_dir:
            return
        out_dir_disp = out_dir
```

2. スレッド起動(2728付近)の `args` 末尾に `out_dir` を追加し、
   `_run_pagenumber_insertion`(2734付近)のシグネチャ末尾に `out_dir: str = ""` を追加。

3. 2761-2763付近を以下に置き換え(mkdir はヘルパー実施済みだが移動直前の再作成は無害なので残してよい):

```python
                effective_out_dir = out_dir or str(pdf_path_obj.parent)
                Path(effective_out_dir).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: 検証**

Run: `python -m py_compile src/gui/unified_window.py && python -m pytest tests/ -q`
Expected: コンパイル成功、全テスト PASS

- [ ] **Step 7: コミット**

```bash
git add src/gui/unified_window.py
git commit -m "feat: 実行時に機能別既定フォルダへ出力・結合ファイル名を【結合】に変更"
```

---

### Task 5: 統合検証とマニュアル更新

**Files:**
- Modify: `MANUAL.md`(出力先の説明箇所)
- Test: 手動確認(GUI)

**Interfaces:**
- Consumes: Task 1-4 のすべて

- [ ] **Step 1: 全テスト実行**

Run: `python -m pytest tests/ -q`
Expected: 全件 PASS

- [ ] **Step 2: アプリを起動して手動確認**

Run: `python -m src.main`(バックグラウンド起動)

確認項目:
1. PDF変換: ファイル追加→出力先ラベルに `...\PDF変換済` が表示→変換実行→`PDF変換済` フォルダに出力される
2. PDF結合: 2ファイル結合→`PDF結合済\【結合】先頭ファイル名.pdf` が生成される
3. 資料NO挿入: 確認ダイアログの出力先に `...\資料NO挿入済` が表示され、そこへ出力される
4. ページ番号挿入: `...\ページ番号挿入済` へ出力される
5. 📂 変更で任意フォルダ指定→その直下に保存される(サブフォルダなし)
6. アプリ再起動→出力先が既定(説明文表示)に戻っている
7. `%APPDATA%\PDF変換・結合ツール\settings.json` に `*_output_dir` キーが保存されない

- [ ] **Step 3: MANUAL.md の出力先説明を更新**

`MANUAL.md` 内で出力先(「最初のファイルと同じフォルダ」「前回の出力先」等)に言及している箇所を grep で特定し、新仕様(機能別既定フォルダ・記憶なし・`【結合】ファイル名.pdf`)に書き換える。

- [ ] **Step 4: コミット**

```bash
git add MANUAL.md
git commit -m "docs: 出力先の新仕様（機能別既定フォルダ）に合わせてマニュアル更新"
```
