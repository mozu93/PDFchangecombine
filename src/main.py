"""
PDF変換・結合ツール メインエントリーポイント
要件定義書に基づくアプリケーションのメイン実行ファイル
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gui.unified_window import UnifiedWindow
from src.utils.logger import logger
from src.config import APP_NAME, APP_VERSION


def main():
    """メインアプリケーション実行"""
    try:
        logger.info(f"{APP_NAME} v{APP_VERSION} 起動開始")
        
        # 統合ウィンドウ作成・実行
        app = UnifiedWindow()
        app.run()
        
        logger.info(f"{APP_NAME} 正常終了")
        
    except Exception as e:
        logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()