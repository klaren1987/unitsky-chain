"""CPU nonce search — multi-core via thread pool (keccak C-ext releases the GIL)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from miner.gpu_engine import hash_work


def _search_chunk(
    miner: str, work_block: int, target: int, start: int, count: int
) -> Optional[int]:
    end = start + count
    nonce = start
    while nonce < end:
        if hash_work(miner, nonce, work_block) < target:
            return nonce
        nonce += 1
    return None


class CPUSearcher:
    def __init__(self) -> None:
        workers = max(1, os.cpu_count() or 1)
        self._workers = workers
        self.device_name = f"CPU ({workers} cores)"
        batch_env = os.getenv("USST_CPU_BATCH_SIZE", "").strip()
        self.batch_size = int(batch_env) if batch_env else workers * 25_000
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="usst-cpu")

    def search(
        self,
        miner: str,
        work_block: int,
        target: int,
        start_nonce: int,
    ) -> tuple[Optional[int], int]:
        chunk = (self.batch_size + self._workers - 1) // self._workers
        futures = [
            self._executor.submit(
                _search_chunk, miner, work_block, target, start_nonce + i * chunk, chunk
            )
            for i in range(self._workers)
        ]
        result: Optional[int] = None
        for fut in as_completed(futures):
            r = fut.result()
            if r is not None and result is None:
                result = r
                # Cancel still-pending futures — already-running ones finish in
                # background but we don't wait for them, saving CPU time.
                for f in futures:
                    f.cancel()
                break
        return result, self.batch_size

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
