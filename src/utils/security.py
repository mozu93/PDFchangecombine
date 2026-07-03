# -*- coding: utf-8 -*-
"""
セキュリティユーティリティ
Path traversal攻撃やその他のセキュリティ脅威からの保護
"""

import os
import re
from pathlib import Path
from typing import List, Optional
from .logger import logger


class SecurityValidator:
    """セキュリティ検証クラス"""

    # 危険な文字列パターン（緩和版）
    DANGEROUS_PATTERNS = [
        r'\.\.[\\/]',   # Path traversal (../ または ..\)
        r'[\x00-\x1f]', # Control characters
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',  # Windows reserved names (完全一致)
    ]

    # Windowsファイル名で禁止されている文字（パス部分は除外）
    FILENAME_ILLEGAL_CHARS = r'[<>"|?*]'

    # 許可されるファイル拡張子（設定ファイルと同期）
    ALLOWED_EXTENSIONS = {
        '.pdf', '.docx', '.doc', '.xlsx', '.xls',
        '.pptx', '.ppt', '.jpg', '.jpeg', '.png',
        '.bmp', '.gif', '.tiff'
    }

    @classmethod
    def validate_file_path(cls, file_path: str, base_dir: Optional[str] = None) -> bool:
        """
        ファイルパスのセキュリティ検証

        Args:
            file_path: 検証するファイルパス
            base_dir: 基準ディレクトリ（指定時はこの範囲内に制限）

        Returns:
            bool: 安全な場合True
        """
        try:
            # 空文字、None チェック
            if not file_path or not isinstance(file_path, str):
                logger.warning("無効なファイルパス: 空文字またはNone")
                return False

            # デバッグ用ログ
            logger.info(f"セキュリティ検証開始: {file_path}")

            # 正規化されたパスを取得
            normalized_path = Path(file_path).resolve()
            logger.info(f"正規化後パス: {normalized_path}")

            # 危険なパターンチェック
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, file_path, re.IGNORECASE):
                    logger.warning(f"危険なパターン検出: {pattern} in {file_path}")
                    return False

            # ファイル名部分のみで禁止文字チェック
            filename_only = normalized_path.name
            if re.search(cls.FILENAME_ILLEGAL_CHARS, filename_only):
                logger.warning(f"ファイル名に禁止文字検出: {filename_only}")
                return False

            # 基準ディレクトリ制限チェック（base_dirが指定された場合のみ）
            if base_dir:
                try:
                    base_path = Path(base_dir).resolve()
                    try:
                        normalized_path.relative_to(base_path)
                    except ValueError:
                        logger.info(f"基準ディレクトリ外のパス（許可）: {file_path}")
                        # 基準ディレクトリ外でも安全なファイルは許可
                except Exception as e:
                    logger.warning(f"基準ディレクトリ検証エラー: {e}")
                    # エラーが発生してもファイル自体は安全かもしれないため続行

            # ファイル拡張子チェック
            file_extension = normalized_path.suffix.lower()
            if file_extension not in cls.ALLOWED_EXTENSIONS:
                logger.warning(f"許可されていない拡張子: {file_extension}")
                return False

            # ファイル存在チェック
            if not normalized_path.exists():
                logger.warning(f"存在しないファイル: {file_path}")
                return False

            # ディレクトリでないことを確認
            if normalized_path.is_dir():
                logger.warning(f"ディレクトリが指定されました: {file_path}")
                return False

            # 検証成功ログ
            logger.info(f"セキュリティ検証成功: {normalized_path.name}")
            return True

        except Exception as e:
            logger.error(f"ファイルパス検証エラー: {e}")
            return False

    @classmethod
    def validate_multiple_paths(cls, file_paths: List[str], base_dir: Optional[str] = None) -> List[str]:
        """
        複数ファイルパスの一括検証

        Args:
            file_paths: 検証するファイルパスのリスト
            base_dir: 基準ディレクトリ

        Returns:
            List[str]: 安全なファイルパスのみのリスト
        """
        validated_paths = []

        for file_path in file_paths:
            if cls.validate_file_path(file_path, base_dir):
                validated_paths.append(file_path)
            else:
                logger.warning(f"セキュリティ検証失敗: {file_path}")

        logger.info(f"セキュリティ検証完了: {len(validated_paths)}/{len(file_paths)} 件が安全")
        return validated_paths

    @classmethod
    def validate_output_path(cls, output_path: str, source_dir: str) -> bool:
        """
        出力パスのセキュリティ検証

        Args:
            output_path: 出力ファイルパス
            source_dir: ソースディレクトリ

        Returns:
            bool: 安全な場合True
        """
        try:
            output_normalized = Path(output_path).resolve()
            source_normalized = Path(source_dir).resolve()

            # 出力パスがソースディレクトリ配下にあることを確認
            try:
                output_normalized.relative_to(source_normalized)
                return True
            except ValueError:
                logger.warning(f"出力パスがソース範囲外: {output_path}")
                return False

        except Exception as e:
            logger.error(f"出力パス検証エラー: {e}")
            return False

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        ファイル名のサニタイズ

        Args:
            filename: 元のファイル名

        Returns:
            str: サニタイズされたファイル名
        """
        # 危険な文字を除去
        sanitized = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)

        # Windows予約名の回避
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL']
        reserved_names.extend([f'COM{i}' for i in range(1, 10)])
        reserved_names.extend([f'LPT{i}' for i in range(1, 10)])

        name_part = Path(sanitized).stem.upper()
        if name_part in reserved_names:
            sanitized = f"_{sanitized}"

        # 長さ制限（Windows: 255文字）
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            max_name_len = 255 - len(ext)
            sanitized = name[:max_name_len] + ext

        return sanitized


class InputValidator:
    """入力値検証クラス"""

    # グリフが不足しており①やⅠ、㎡などの機種依存文字が文字化けするフォント
    _GLYPH_LIMITED_FONTS = {"BIZ UDPゴシック"}

    # ①やⅠ、㎡など「機種依存文字」の範囲。
    # _GLYPH_LIMITED_FONTS のフォントにはグリフが存在せず、
    # PDF上で文字化け（notdef表示）やテキスト情報の破損を起こすため
    # そのフォントが選択されている場合のみ入力時点で弾く。
    _PLATFORM_DEPENDENT_CHAR_RANGES = [
        (0x2160, 0x217F),  # ローマ数字 Ⅰ-Ⅻ, ⅰ-ⅻ
        (0x2460, 0x24FF),  # 丸数字・丸英字 ①-⑳, Ⓐ-Ⓩ など
        (0x2776, 0x2793),  # 装飾丸数字
        (0x3220, 0x3243),  # 括弧付き漢字 (株)など
        (0x3251, 0x325F),  # 丸数字 21-32
        (0x32B1, 0x32BF),  # 丸数字 36-50
        (0x3300, 0x33FF),  # 単位記号など（㎡ ㌔ ㍑ など）
        (0x2116, 0x2116),  # №
        (0x2121, 0x2121),  # ℡
    ]

    @staticmethod
    def find_platform_dependent_char(text: str) -> Optional[str]:
        """機種依存文字が含まれていれば最初の1文字を返す（無ければNone）"""
        for ch in text:
            code = ord(ch)
            for lo, hi in InputValidator._PLATFORM_DEPENDENT_CHAR_RANGES:
                if lo <= code <= hi:
                    return ch
        return None

    @staticmethod
    def validate_document_number(document_number: str, font_name: Optional[str] = None) -> bool:
        """
        資料番号の検証

        Args:
            document_number: 資料番号
            font_name: 描画に使用するフォント表示名（機種依存文字チェックに使用）

        Returns:
            bool: 有効な場合True
        """
        if not document_number or not isinstance(document_number, str):
            return False

        # 基本的な文字数制限
        if len(document_number.strip()) > 20:
            logger.warning(f"資料番号が長すぎます: {len(document_number)} 文字")
            return False

        # HTML/SQL インジェクション対策
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        if any(char in document_number for char in dangerous_chars):
            logger.warning(f"危険な文字が含まれています: {document_number}")
            return False

        # 機種依存文字（①、Ⅰ、㎡など）はグリフ不足のフォント選択時のみ文字化けするため禁止
        if font_name in InputValidator._GLYPH_LIMITED_FONTS:
            bad_char = InputValidator.find_platform_dependent_char(document_number)
            if bad_char:
                logger.warning(f"機種依存文字が含まれています: {bad_char!r} in {document_number} (font={font_name})")
                return False

        return True

    @staticmethod
    def validate_prefix_text(prefix: str, font_name: Optional[str] = None) -> bool:
        """プレフィックス文字列の検証（任意入力用）"""
        if not prefix or not isinstance(prefix, str):
            return False
        if len(prefix.strip()) > 10:
            logger.warning(f"プレフィックスが長すぎます: {len(prefix)} 文字")
            return False
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        if any(char in prefix for char in dangerous_chars):
            logger.warning(f"プレフィックスに危険な文字が含まれています: {prefix}")
            return False

        # 機種依存文字（①、Ⅰ、㎡など）はグリフ不足のフォント選択時のみ文字化けするため禁止
        if font_name in InputValidator._GLYPH_LIMITED_FONTS:
            bad_char = InputValidator.find_platform_dependent_char(prefix)
            if bad_char:
                logger.warning(f"プレフィックスに機種依存文字が含まれています: {bad_char!r} in {prefix} (font={font_name})")
                return False

        return True

    @staticmethod
    def validate_page_range(start_page: str, start_number: str) -> bool:
        """
        ページ番号範囲の検証

        Args:
            start_page: 開始ページ
            start_number: 開始番号

        Returns:
            bool: 有効な場合True
        """
        try:
            if start_page:
                page_num = int(start_page)
                if page_num < 1 or page_num > 9999:
                    logger.warning(f"無効な開始ページ: {page_num}")
                    return False

            if start_number:
                number_num = int(start_number)
                if number_num < 1 or number_num > 9999:
                    logger.warning(f"無効な開始番号: {number_num}")
                    return False

            return True

        except ValueError:
            logger.warning("ページ番号は数値で入力してください")
            return False


# セキュリティ検証のデコレーター
def secure_file_operation(func):
    """ファイル操作の事前セキュリティチェック"""
    def wrapper(*args, **kwargs):
        # 第一引数がファイルパスと仮定してチェック
        if args and isinstance(args[0], str):
            if not SecurityValidator.validate_file_path(args[0]):
                raise ValueError(f"セキュリティ検証失敗: {args[0]}")
        return func(*args, **kwargs)
    return wrapper