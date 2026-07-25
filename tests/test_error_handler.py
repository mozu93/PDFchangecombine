"""
エラーハンドリングユーティリティ（ErrorHandler / ErrorSeverity）のテスト
要件定義書 5.1.エラーハンドリング要件・5.6.テスト自動化の実装
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.error_handler import ErrorHandler, ErrorSeverity


@pytest.fixture
def handler():
    """sys.excepthookを汚さないよう退避・復元しつつ、GUIなしのErrorHandlerを提供する"""
    original_hook = sys.excepthook
    h = ErrorHandler(parent_window=None)
    yield h
    sys.excepthook = original_hook


class TestErrorSeverity:
    def test_severity_values(self):
        assert ErrorSeverity.FATAL.value == "致命的エラー"
        assert ErrorSeverity.CRITICAL.value == "重大エラー"
        assert ErrorSeverity.WARNING.value == "警告"
        assert ErrorSeverity.INFO.value == "情報"


class TestErrorHandlerCounting:
    def test_warning_increments_warning_count_only(self, handler):
        handler.handle_error(ValueError("x"), ErrorSeverity.WARNING)
        assert handler.warning_count == 1
        assert handler.error_count == 0

    def test_critical_increments_error_count(self, handler):
        handler.handle_error(ValueError("x"), ErrorSeverity.CRITICAL)
        assert handler.error_count == 1
        assert handler.warning_count == 0

    def test_info_does_not_increment_any_count(self, handler):
        handler.handle_error(ValueError("x"), ErrorSeverity.INFO)
        assert handler.error_count == 0
        assert handler.warning_count == 0

    def test_multiple_errors_accumulate_in_statistics(self, handler):
        handler.handle_error(ValueError("x"), ErrorSeverity.WARNING)
        handler.handle_error(ValueError("y"), ErrorSeverity.WARNING)
        handler.handle_error(ValueError("z"), ErrorSeverity.CRITICAL)

        stats = handler.get_error_statistics()
        assert stats == {
            "error_count": 1,
            "warning_count": 2,
            "total_issues": 3,
        }


class TestErrorHandlerFatal:
    def test_fatal_exits_process(self, handler):
        with pytest.raises(SystemExit) as excinfo:
            handler.handle_error(RuntimeError("boom"), ErrorSeverity.FATAL)
        assert excinfo.value.code == 1
        assert handler.error_count == 1

    def test_fatal_runs_callback_before_exit(self, handler):
        called = []
        with pytest.raises(SystemExit):
            handler.handle_error(
                RuntimeError("boom"), ErrorSeverity.FATAL,
                callback=lambda: called.append(True)
            )
        assert called == [True]


class TestErrorHandlerCallback:
    def test_callback_runs_for_non_fatal_severity(self, handler):
        called = []
        handler.handle_error(
            ValueError("x"), ErrorSeverity.WARNING,
            callback=lambda: called.append(True)
        )
        assert called == [True]

    def test_callback_exception_does_not_propagate(self, handler):
        def failing_callback():
            raise RuntimeError("callback failed")

        # 例外を投げずに完了すること
        handler.handle_error(
            ValueError("x"), ErrorSeverity.WARNING, callback=failing_callback
        )


class TestGenerateUserMessage:
    def test_conversion_context_file_not_found(self, handler):
        msg = handler._generate_user_message(FileNotFoundError(), ErrorSeverity.CRITICAL, "変換処理")
        assert "ファイルが見つかりません" in msg

    def test_conversion_context_permission_error(self, handler):
        msg = handler._generate_user_message(PermissionError(), ErrorSeverity.CRITICAL, "変換処理")
        assert "アクセスできません" in msg

    def test_combination_context_file_not_found(self, handler):
        msg = handler._generate_user_message(FileNotFoundError(), ErrorSeverity.CRITICAL, "結合処理")
        assert "結合対象のPDFファイルが見つかりません" in msg

    def test_save_context_permission_error(self, handler):
        msg = handler._generate_user_message(PermissionError(), ErrorSeverity.CRITICAL, "保存処理")
        assert "書き込み権限がありません" in msg

    def test_generic_context_memory_error(self, handler):
        msg = handler._generate_user_message(MemoryError(), ErrorSeverity.WARNING, "")
        assert "メモリが不足しています" in msg

    def test_generic_context_unknown_exception(self, handler):
        msg = handler._generate_user_message(RuntimeError("weird"), ErrorSeverity.WARNING, "")
        assert "RuntimeError" in msg

    def test_fatal_appends_restart_instruction(self, handler):
        msg = handler._generate_user_message(RuntimeError(), ErrorSeverity.FATAL, "")
        assert "再起動してください" in msg

    def test_warning_appends_continue_instruction(self, handler):
        msg = handler._generate_user_message(RuntimeError(), ErrorSeverity.WARNING, "")
        assert "処理は継続されます" in msg


class TestHandleUncaughtException:
    def test_keyboard_interrupt_delegates_to_original_hook(self, handler, monkeypatch):
        calls = []
        monkeypatch.setattr(sys, "__excepthook__", lambda *a: calls.append(a))

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()

        handler._handle_uncaught_exception(exc_type, exc_value, exc_tb)
        assert len(calls) == 1

    def test_other_exception_treated_as_fatal(self, handler):
        try:
            raise RuntimeError("uncaught")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        with pytest.raises(SystemExit):
            handler._handle_uncaught_exception(exc_type, exc_value, exc_tb)
        assert handler.error_count == 1
