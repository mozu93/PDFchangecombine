"""fitz操作直列化ワーカーのテスト"""

import threading
import time

import pytest

from src.gui.page_edit_worker import PageEditWorker


class FakeUi:
    """root.after の代わり。溜めたコールバックを drain() で実行する"""

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()

    def post(self, fn):
        with self._lock:
            self._queue.append(fn)

    def drain(self, timeout: float = 3.0):
        """1件以上溜まるまで待ってから、溜まっている分を全部実行する"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if self._queue:
                    pending, self._queue = self._queue, []
                    break
            time.sleep(0.01)
        else:
            raise AssertionError("UIコールバックが届きませんでした")
        for fn in pending:
            fn()


@pytest.fixture
def ui():
    return FakeUi()


@pytest.fixture
def worker(ui):
    w = PageEditWorker(ui.post)
    yield w
    w.shutdown()


class TestSubmit:
    def test_ジョブの戻り値がon_doneに渡る(self, worker, ui):
        results = []
        worker.submit(lambda gen: 42, on_done=results.append)
        ui.drain()
        assert results == [42]

    def test_ジョブの例外がon_errorに渡る(self, worker, ui):
        errors = []
        worker.submit(
            lambda gen: (_ for _ in ()).throw(RuntimeError("boom")),
            on_error=errors.append,
        )
        ui.drain()
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)

    def test_例外が出てもワーカーは生き続ける(self, worker, ui):
        worker.submit(lambda gen: (_ for _ in ()).throw(RuntimeError("boom")))
        ui.drain()
        results = []
        worker.submit(lambda gen: "ok", on_done=results.append)
        ui.drain()
        assert results == ["ok"]

    def test_ジョブは投入順に直列実行される(self, worker, ui):
        order = []

        def make(n):
            def job(gen):
                order.append(("start", n))
                time.sleep(0.02)
                order.append(("end", n))
                return n
            return job

        for n in range(3):
            worker.submit(make(n))
        for _ in range(3):
            ui.drain()

        # 直列なら必ず start,end,start,end... の順になる
        assert order == [
            ("start", 0), ("end", 0),
            ("start", 1), ("end", 1),
            ("start", 2), ("end", 2),
        ]

    def test_ジョブには現在の世代番号が渡る(self, worker, ui):
        seen = []
        worker.submit(lambda gen: seen.append(gen))
        ui.drain()
        assert seen == [worker.current_generation]


class TestGeneration:
    def test_bumpで世代が進む(self, worker):
        before = worker.current_generation
        after = worker.bump_generation()
        assert after == before + 1
        assert worker.current_generation == after

    def test_古い世代はstale判定される(self, worker):
        old = worker.current_generation
        worker.bump_generation()
        assert worker.is_stale(old) is True
        assert worker.is_stale(worker.current_generation) is False

    def test_実行中のジョブは自分でstaleを検知して中断できる(self, worker, ui):
        processed = []
        started = threading.Event()

        def long_job(gen):
            started.set()
            for i in range(100):
                if worker.is_stale(gen):
                    return "cancelled"
                processed.append(i)
                time.sleep(0.005)
            return "finished"

        results = []
        worker.submit(long_job, on_done=results.append)
        assert started.wait(3.0)
        worker.bump_generation()
        ui.drain()
        assert results == ["cancelled"]
        assert len(processed) < 100


class TestBusy:
    def test_初期状態はbusyではない(self, worker):
        assert worker.is_busy is False

    def test_ジョブ実行中はbusyになる(self, worker, ui):
        started = threading.Event()
        release = threading.Event()

        def job(gen):
            started.set()
            release.wait(3.0)

        worker.submit(job)
        assert started.wait(3.0)
        # キューからは取り出し済みだが実行中なので busy であること
        assert worker.is_busy is True
        release.set()
        ui.drain()

    def test_ジョブ完了後はbusyでなくなる(self, worker, ui):
        worker.submit(lambda gen: None)
        ui.drain()
        assert worker.is_busy is False


class TestShutdown:
    def test_shutdown後にsubmitしても例外にならない(self, ui):
        w = PageEditWorker(ui.post)
        w.shutdown()
        w.submit(lambda gen: None)  # 黙って無視されること

    def test_shutdownは二重に呼んでも安全(self, ui):
        w = PageEditWorker(ui.post)
        w.shutdown()
        w.shutdown()
