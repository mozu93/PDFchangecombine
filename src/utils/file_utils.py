"""
ファイル操作ユーティリティ
要件定義書 F-102 対応形式判定機能の実装
"""

import os
from pathlib import Path
from typing import List, Dict, Set
from ..config import (
    SUPPORTED_OFFICE_EXTENSIONS, 
    SUPPORTED_IMAGE_EXTENSIONS, 
    SUPPORTED_PDF_EXTENSIONS,
    ALL_SUPPORTED_EXTENSIONS,
    OUTPUT_FOLDER_NAME,
    MAX_FILE_SIZE_MB
)
from .logger import logger


class FileValidator:
    """ファイル検証クラス"""
    
    @staticmethod
    def is_supported_file(file_path: str) -> bool:
        """
        対応形式判定（要件定義書 F-102）
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: 対応形式の場合True
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in ALL_SUPPORTED_EXTENSIONS
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        ファイル種別の取得
        
        Args:
            file_path: ファイルパス
            
        Returns:
            str: ファイル種別 ('word'|'excel'|'powerpoint'|'image'|'pdf'|'unknown')
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in SUPPORTED_OFFICE_EXTENSIONS['word']:
            return 'word'
        elif file_ext in SUPPORTED_OFFICE_EXTENSIONS['excel']:
            return 'excel'
        elif file_ext in SUPPORTED_OFFICE_EXTENSIONS['powerpoint']:
            return 'powerpoint'
        elif file_ext in SUPPORTED_IMAGE_EXTENSIONS:
            return 'image'
        elif file_ext in SUPPORTED_PDF_EXTENSIONS:
            return 'pdf'
        else:
            return 'unknown'
    
    @staticmethod
    def is_valid_file_size(file_path: str) -> bool:
        """
        ファイルサイズ検証
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: 制限内サイズの場合True
        """
        try:
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            return file_size_mb <= MAX_FILE_SIZE_MB
        except OSError:
            return False
    
    @staticmethod
    def is_readable_file(file_path: str) -> bool:
        """
        ファイル読み取り可能性チェック
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: 読み取り可能な場合True
        """
        try:
            path = Path(file_path)
            return path.is_file() and os.access(path, os.R_OK)
        except OSError:
            return False


class FileScanner:
    """ファイルスキャンクラス"""
    
    @staticmethod
    def scan_files_from_paths(paths: List[str]) -> Dict[str, List[str]]:
        """
        パスリストから対応ファイルを再帰的にスキャン（要件定義書 F-101）
        
        Args:
            paths: ファイル/フォルダパスのリスト
            
        Returns:
            Dict: {'valid': [有効ファイルリスト], 'invalid': [無効ファイルリスト], 'scan_time': float}
        """
        import time
        start_time = time.time()
        
        result = {'valid': [], 'invalid': []}
        
        for path_str in paths:
            path = Path(path_str)
            
            if path.is_file():
                FileScanner._process_file(path, result)
            elif path.is_dir():
                FileScanner._process_directory(path, result)
            else:
                logger.warning(f"無効なパス: {path_str}")
                result['invalid'].append(path_str)
        
        result['scan_time'] = time.time() - start_time
        logger.info(f"スキャン完了 - 有効: {len(result['valid'])}, 無効: {len(result['invalid'])}")
        return result
    
    @staticmethod
    def _process_file(file_path: Path, result: Dict[str, List[str]]) -> None:
        """単一ファイルの処理"""
        file_str = str(file_path)
        
        if not FileValidator.is_readable_file(file_str):
            logger.warning(f"読み取り不可ファイル: {file_path.name}")
            result['invalid'].append(file_str)
            return
        
        if not FileValidator.is_supported_file(file_str):
            logger.info(f"非対応形式ファイル（無視）: {file_path.name}")
            result['invalid'].append(file_str)
            return
        
        if not FileValidator.is_valid_file_size(file_str):
            logger.warning(f"ファイルサイズ超過: {file_path.name}")
            result['invalid'].append(file_str)
            return
        
        result['valid'].append(file_str)
        logger.info(f"有効ファイル検出: {file_path.name}")
    
    @staticmethod
    def _process_directory(dir_path: Path, result: Dict[str, List[str]]) -> None:
        """ディレクトリの再帰的処理（要件定義書 F-101）"""
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    FileScanner._process_file(file_path, result)
        except PermissionError:
            logger.error(f"ディレクトリアクセス権限なし: {dir_path}")
            result['invalid'].append(str(dir_path))


def _get_onedrive_sync_roots() -> list:
    """
    レジストリからOneDrive・SharePoint同期ルートパス一覧を取得する（Windows限定）。
    HKCU\SOFTWARE\Microsoft\OneDrive\Accounts 配下の全アカウントを走査する。
    """
    sync_roots = []
    if os.name != 'nt':
        return sync_roots
    try:
        import winreg
        accounts_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\OneDrive\Accounts"
        )
        i = 0
        while True:
            try:
                account_name = winreg.EnumKey(accounts_key, i)
                account_key = winreg.OpenKey(accounts_key, account_name)
                # UserFolder: OneDrive / OneDrive for Business のルートパス
                try:
                    user_folder, _ = winreg.QueryValueEx(account_key, "UserFolder")
                    if user_folder:
                        sync_roots.append(user_folder)
                except FileNotFoundError:
                    pass
                # ScopeIdToMountPointPathCache: SharePointサイトの同期パス
                try:
                    cache_key = winreg.OpenKey(
                        account_key, "ScopeIdToMountPointPathCache"
                    )
                    j = 0
                    while True:
                        try:
                            _, mount_path, _ = winreg.EnumValue(cache_key, j)
                            if mount_path:
                                sync_roots.append(mount_path)
                            j += 1
                        except OSError:
                            break
                except FileNotFoundError:
                    pass
                i += 1
            except OSError:
                break
    except Exception:
        pass
    return sync_roots


def is_cloud_sync_path(path: str) -> bool:
    """
    クラウド同期パス（OneDrive・SharePoint等）かどうかを判定する。

    判定基準（順に確認）:
    1. パス文字列に 'onedrive' が含まれる（大文字小文字無視）
    2. 環境変数 OneDrive / OneDriveConsumer / OneDriveCommercial のパス配下
    3. レジストリに登録されたOneDrive・SharePoint同期ルート配下（組織名不問）
    """
    path_lower = path.lower()

    # 1. 文字列チェック
    if 'onedrive' in path_lower:
        return True

    # 2. 環境変数チェック
    for env_var in ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial'):
        od_path = os.environ.get(env_var, '')
        if od_path and path_lower.startswith(od_path.lower()):
            return True

    # 3. レジストリから取得した同期ルートと照合
    for sync_root in _get_onedrive_sync_roots():
        if sync_root and path_lower.startswith(sync_root.lower()):
            return True

    return False


class OutputManager:
    """出力管理クラス"""
    
    @staticmethod
    def create_output_directory(source_file_path: str) -> str:
        """
        変換済フォルダの作成（要件定義書 F-104）
        
        Args:
            source_file_path: 変換元ファイルパス
            
        Returns:
            str: 出力ディレクトリパス
        """
        source_dir = Path(source_file_path).parent
        output_dir = source_dir / OUTPUT_FOLDER_NAME
        
        try:
            output_dir.mkdir(exist_ok=True)
            logger.info(f"出力ディレクトリ準備完了: {output_dir}")
            return str(output_dir)
        except OSError as e:
            logger.error(f"出力ディレクトリ作成エラー: {e}")
            raise
    
    @staticmethod
    def generate_output_filename(source_file_path: str, target_extension: str = '.pdf') -> str:
        """
        出力ファイル名の生成（要件定義書 F-104）
        
        Args:
            source_file_path: 変換元ファイルパス
            target_extension: 出力拡張子
            
        Returns:
            str: 出力ファイル名
        """
        source_path = Path(source_file_path)
        return source_path.stem + target_extension
    
    @staticmethod
    def get_output_file_path(source_file_path: str) -> str:
        """
        完全な出力ファイルパスの取得
        
        Args:
            source_file_path: 変換元ファイルパス
            
        Returns:
            str: 完全な出力ファイルパス
        """
        output_dir = OutputManager.create_output_directory(source_file_path)
        output_filename = OutputManager.generate_output_filename(source_file_path)
        return str(Path(output_dir) / output_filename)