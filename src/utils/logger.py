"""
ログ管理ユーティリティ
要件定義書 5.2.ログ・監視の要件に基づく実装
"""

import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import threading
from functools import wraps

from ..config import LOG_DIR, LOG_RETENTION_DAYS, APP_NAME


class AppLogger:
    """アプリケーションログ管理クラス"""
    
    _instance: Optional['AppLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'AppLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
            self._cleanup_old_logs()
    
    def _setup_logger(self) -> None:
        """ログ設定の初期化"""
        # ログディレクトリ作成
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # ログファイルパス
        log_filename = f"{APP_NAME}_{datetime.now().strftime('%Y%m%d')}.log"
        log_file_path = LOG_DIR / log_filename
        
        # ログフォーマット
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # ロガー設定
        self._logger = logging.getLogger(APP_NAME)
        self._logger.setLevel(logging.INFO)
        
        # コンソールハンドラ（開発時用）
        if not self._logger.handlers:  # 重複ハンドラ防止
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(log_format, date_format)
            console_handler.setFormatter(console_formatter)
            self._logger.addHandler(console_handler)
            
            # ファイルハンドラ
            try:
                file_handler = logging.FileHandler(
                    log_file_path, 
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.INFO)
                file_formatter = logging.Formatter(log_format, date_format)
                file_handler.setFormatter(file_formatter)
                self._logger.addHandler(file_handler)
            except Exception as e:
                self._logger.error(f"ログファイル作成エラー: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """古いログファイルの削除（要件定義書 5.2.保持期間）"""
        try:
            cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
            
            for log_file in LOG_DIR.glob(f"{APP_NAME}_*.log"):
                if log_file.is_file():
                    file_date_str = log_file.stem.split('_')[-1]
                    try:
                        file_date = datetime.strptime(file_date_str, '%Y%m%d')
                        if file_date < cutoff_date:
                            log_file.unlink()
                            self.info(f"古いログファイル削除: {log_file.name}")
                    except ValueError:
                        # 日付形式が正しくない場合はスキップ
                        continue
        except Exception as e:
            if self._logger:
                self._logger.error(f"ログクリーンアップエラー: {e}")
    
    def info(self, message: str) -> None:
        """INFOレベルログ出力"""
        if self._logger:
            self._logger.info(message)
    
    def warning(self, message: str) -> None:
        """WARNレベルログ出力"""
        if self._logger:
            self._logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False) -> None:
        """ERRORレベルログ出力"""
        if self._logger:
            self._logger.error(message, exc_info=exc_info)
    
    def log_file_operation(self, operation: str, file_path: str, success: bool = True) -> None:
        """ファイル操作のログ記録（個人情報マスキング対応）"""
        # ファイル名のみ記録（フルパスは記録しない）
        file_name = Path(file_path).name
        status = "成功" if success else "失敗"
        self.info(f"{operation}: {file_name} - {status}")
    
    def log_conversion_stats(self, total_files: int, successful: int, failed: int,
                           processing_time: float) -> None:
        """変換処理統計のログ記録"""
        self.info(
            f"変換処理完了 - "
            f"総ファイル数: {total_files}, "
            f"成功: {successful}, "
            f"失敗: {failed}, "
            f"処理時間: {processing_time:.2f}秒"
        )

    def log_structured(self, level: str, event: str, data: Dict[str, Any]) -> None:
        """構造化ログの記録"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'event': event,
            'data': data,
            'thread_id': threading.current_thread().ident
        }

        # JSON形式でログ出力
        json_msg = json.dumps(log_entry, ensure_ascii=False)

        if level.lower() == 'error':
            self.error(f"STRUCTURED: {json_msg}")
        elif level.lower() == 'warning':
            self.warning(f"STRUCTURED: {json_msg}")
        else:
            self.info(f"STRUCTURED: {json_msg}")

    def log_performance(self, operation: str, duration: float, metadata: Dict[str, Any] = None) -> None:
        """パフォーマンス監視ログ"""
        perf_data = {
            'operation': operation,
            'duration_seconds': round(duration, 3),
            'metadata': metadata or {}
        }
        self.log_structured('INFO', 'PERFORMANCE_METRIC', perf_data)

    def log_security_event(self, event_type: str, severity: str, details: Dict[str, Any]) -> None:
        """セキュリティイベントログ"""
        security_data = {
            'event_type': event_type,
            'severity': severity,
            'details': details
        }
        self.log_structured('WARNING', 'SECURITY_EVENT', security_data)

    def log_user_action(self, action: str, details: Dict[str, Any] = None) -> None:
        """ユーザーアクションログ（個人情報除外）"""
        user_data = {
            'action': action,
            'details': details or {}
        }
        self.log_structured('INFO', 'USER_ACTION', user_data)


# パフォーマンス監視デコレーター
def monitor_performance(operation_name: str = None):
    """パフォーマンス監視デコレーター"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 成功時のパフォーマンスログ
                logger.log_performance(op_name, duration, {
                    'status': 'success',
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })

                return result

            except Exception as e:
                duration = time.time() - start_time

                # エラー時のパフォーマンスログ
                logger.log_performance(op_name, duration, {
                    'status': 'error',
                    'error_type': type(e).__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })

                raise

        return wrapper
    return decorator


# ユーザーアクション監視デコレーター
def monitor_user_action(action_name: str = None):
    """ユーザーアクション監視デコレーター"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            action = action_name or f"UI_{func.__name__}"

            logger.log_user_action(action, {
                'timestamp': datetime.now().isoformat(),
                'function': f"{func.__module__}.{func.__name__}"
            })

            return func(*args, **kwargs)

        return wrapper
    return decorator


# シングルトンインスタンス
logger = AppLogger()