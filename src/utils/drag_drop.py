"""
ドラッグ&ドロップ機能ユーティリティ
要件定義書 F-101, F-201 ドラッグ&ドロップ機能の実装
"""

import tkinter as tk
from typing import List, Callable, Optional
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("ドラッグ&ドロップライブラリ未インストール: tkinterdnd2が必要です")
    DND_FILES = None
    TkinterDnD = None

from .logger import logger
from .file_utils import FileScanner


class DragDropHandler:
    """ドラッグ&ドロップ処理管理クラス"""
    
    def __init__(self):
        self.is_dnd_available = DND_FILES is not None
        if not self.is_dnd_available:
            logger.warning("ドラッグ&ドロップ機能が利用できません（tkinterdnd2未インストール）")
        else:
            logger.info("ドラッグ&ドロップ機能利用可能")
    
    def setup_drag_drop(self, widget: tk.Widget, 
                       drop_callback: Callable[[List[str]], None],
                       file_filter: Optional[Callable[[str], bool]] = None) -> bool:
        """
        ウィジェットにドラッグ&ドロップ機能を設定
        
        Args:
            widget: 対象ウィジェット
            drop_callback: ドロップ時のコールバック関数
            file_filter: ファイルフィルタ関数（None=全て受け入れ）
            
        Returns:
            bool: 設定成功時True
        """
        if not self.is_dnd_available:
            logger.warning("ドラッグ&ドロップ機能が利用できません")
            return False
        
        try:
            # ドロップイベントハンドラー作成
            def on_drop(event):
                return self._handle_drop_event(event, drop_callback, file_filter)
            
            # ドラッグイベントハンドラー作成
            def on_drag_enter(event):
                return self._handle_drag_enter(event, widget)
            
            def on_drag_leave(event):
                return self._handle_drag_leave(event, widget)
            
            # イベント登録
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind('<<Drop>>', on_drop)
            widget.dnd_bind('<<DragEnter>>', on_drag_enter)
            widget.dnd_bind('<<DragLeave>>', on_drag_leave)
            
            logger.info(f"ドラッグ&ドロップ機能設定完了: {widget.__class__.__name__}")
            return True
            
        except Exception as e:
            logger.error(f"ドラッグ&ドロップ設定エラー: {str(e)}")
            return False
    
    def _handle_drop_event(self, event, callback: Callable[[List[str]], None],
                          file_filter: Optional[Callable[[str], bool]]) -> str:
        """ドロップイベント処理"""
        try:
            # ドロップされたファイル/フォルダパスを取得
            dropped_paths = self._parse_drop_data(event.data)
            
            if not dropped_paths:
                logger.warning("ドロップデータが空です")
                return "break"
            
            logger.info(f"ドロップ検出: {len(dropped_paths)}個のアイテム")
            
            # ファイルスキャン実行（フォルダ内再帰検索含む）
            scan_result = FileScanner.scan_files_from_paths(dropped_paths)
            valid_files = scan_result['valid']
            
            # ファイルフィルタ適用
            if file_filter:
                valid_files = [f for f in valid_files if file_filter(f)]
                logger.info(f"フィルタ後ファイル数: {len(valid_files)}")
            
            if valid_files:
                # コールバック実行
                callback(valid_files)
                logger.info(f"ドロップ処理完了: {len(valid_files)}ファイル")
            else:
                logger.info("対応ファイルが見つかりませんでした")
            
            return "break"
            
        except Exception as e:
            logger.error(f"ドロップイベント処理エラー: {str(e)}")
            return "break"
    
    def _handle_drag_enter(self, event, widget: tk.Widget) -> str:
        """ドラッグ進入時の視覚効果"""
        try:
            # ウィジェットのハイライト表示
            if hasattr(widget, 'configure'):
                original_bg = widget.cget('bg') if hasattr(widget, 'cget') else None
                if original_bg:
                    widget.configure(bg='lightblue')
            
            logger.debug("ドラッグ進入")
            return "break"
            
        except Exception as e:
            logger.error(f"ドラッグ進入処理エラー: {str(e)}")
            return "break"
    
    def _handle_drag_leave(self, event, widget: tk.Widget) -> str:
        """ドラッグ退出時の視覚効果解除"""
        try:
            # ウィジェットの通常表示に戻す
            if hasattr(widget, 'configure'):
                # 元の背景色に戻す（簡易実装）
                if hasattr(widget, 'cget'):
                    try:
                        widget.configure(bg='SystemButtonFace')  # デフォルト色
                    except:
                        pass
            
            logger.debug("ドラッグ退出")
            return "break"
            
        except Exception as e:
            logger.error(f"ドラッグ退出処理エラー: {str(e)}")
            return "break"
    
    def _parse_drop_data(self, drop_data: str) -> List[str]:
        """ドロップデータの解析"""
        try:
            # ドロップデータは波括弧で囲まれたパスのリスト形式
            # 例: "{C:/path/file1.txt} {C:/path/file2.pdf}"
            
            paths = []
            current_path = ""
            in_braces = False
            
            for char in drop_data:
                if char == '{':
                    in_braces = True
                    current_path = ""
                elif char == '}':
                    if in_braces and current_path.strip():
                        paths.append(current_path.strip())
                    in_braces = False
                    current_path = ""
                elif in_braces:
                    current_path += char
                elif char == ' ' and current_path.strip():
                    # 波括弧なしの場合はスペース区切り
                    paths.append(current_path.strip())
                    current_path = ""
                elif char != ' ':
                    current_path += char
            
            # 最後のパスを追加
            if current_path.strip() and not in_braces:
                paths.append(current_path.strip())
            
            # パスの正規化
            normalized_paths = []
            for path in paths:
                try:
                    normalized_path = str(Path(path).resolve())
                    normalized_paths.append(normalized_path)
                except Exception:
                    logger.warning(f"パス正規化失敗: {path}")
                    continue
            
            return normalized_paths
            
        except Exception as e:
            logger.error(f"ドロップデータ解析エラー: {str(e)}")
            return []
    
    def create_pdf_filter(self) -> Callable[[str], bool]:
        """PDFファイル専用フィルタ作成"""
        def pdf_filter(file_path: str) -> bool:
            return Path(file_path).suffix.lower() == '.pdf'
        return pdf_filter
    
    def create_office_image_filter(self) -> Callable[[str], bool]:
        """Office・画像ファイル専用フィルタ作成"""
        def office_image_filter(file_path: str) -> bool:
            from ..config import ALL_SUPPORTED_EXTENSIONS
            file_ext = Path(file_path).suffix.lower()
            return file_ext in ALL_SUPPORTED_EXTENSIONS
        return office_image_filter


# グローバルハンドラーインスタンス
drag_drop_handler = DragDropHandler()