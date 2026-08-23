"""
ページ編集タブ用のワーカースレッド

fitz.Document はスレッドセーフではないため、サムネイル生成・保存・抽出・
挿入・クローズをすべてこの単一スレッドで直列に実行する。複数スレッドから
同時に Document へ触れる経路を構造的に作らないための仕組み。

UIへの通知は post_to_ui（実体は root.after）経由で行うので、
このモジュール自体は tkinter に依存せずテストできる。
"""

import queue
import threading
from typing import Any, Callable, Optional

from ..utils.logger import logger

# job は世代番号を1つ受け取り、任意の値を返す
Job = Callable[[int], Any]
PostToUi = Callable[[Callable[[], None]], None]


class PageEditWorker:
    """fitz操作を1本のスレッドで直列実行するワーカー"""

    def __init__(self, post_to_ui: PostToUi) -> None:
        self._post_to_ui = post_to_ui
        self._queue: "queue.Queue[Optional[tuple]]" = queue.Queue()
        self._generation = 0
        self._gen_lock = threading.Lock()
        self._active = False
        self._busy_lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="PageEditWorker", daemon=True
        )
        self._thread.start()

    # ── 世代番号（実行中ジョブの中断用） ──

    @property
    def current_generation(self) -> int:
        with self._gen_lock:
            return self._generation

    def bump_generation(self) -> int:
        """世代を進める。実行中のジョブは is_stale() で検知して中断する"""
        with self._gen_lock:
            self._generation += 1
            return self._generation

    def is_stale(self, generation: int) -> bool:
        """渡された世代が既に古いか（＝ジョブを中断すべきか）"""
        with self._gen_lock:
            return generation != self._generation

    # ── ジョブ投入 ──

    @property
    def is_busy(self) -> bool:
        """実行中または待機中のジョブがあるか。

        キューの空判定だけでは「get() 済みで実行中」を取りこぼすため、
        実行中フラグと併せて判定する。
        """
        with self._busy_lock:
            return self._active or not self._queue.empty()

    def submit(self, job: Job,
               on_done: Optional[Callable[[Any], None]] = None,
               on_error: Optional[Callable[[Exception], None]] = None) -> None:
        """ジョブをキューに積む。shutdown 済みなら黙って無視する"""
        if not self._running:
            return
        self._queue.put((job, on_done, on_error, self.current_generation))

    # ── 内部 ──

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            job, on_done, on_error, generation = item
            error: Optional[Exception] = None
            result = None
            with self._busy_lock:
                self._active = True
            try:
                result = job(generation)
            except Exception as e:
                error = e
                logger.warning(f"ページ編集ジョブが失敗しました: {e}")
            finally:
                # UIへ通知する前に busy を解除する。そうしないと on_done の中で
                # is_busy を見たときに、まだ実行中に見えてしまう
                with self._busy_lock:
                    self._active = False
                self._queue.task_done()

            if error is not None:
                if on_error is not None:
                    self._post_to_ui(lambda e=error: on_error(e))
                else:
                    self._post_to_ui(lambda: None)
            else:
                if on_done is not None:
                    self._post_to_ui(lambda r=result: on_done(r))
                else:
                    self._post_to_ui(lambda: None)

    def shutdown(self, timeout: float = 5.0) -> None:
        """ワーカーを停止する。二重呼び出しは安全"""
        if not self._running:
            return
        self._running = False
        self.bump_generation()  # 実行中ジョブに中断を促す
        self._queue.put(None)
        self._thread.join(timeout=timeout)
