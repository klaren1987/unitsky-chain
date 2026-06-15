"""CUDA GPU nonce search (NVIDIA) for USST PoW."""

from __future__ import annotations

import os
import time
from typing import Optional

import numpy as np
from eth_abi.packed import encode_packed
from eth_hash.auto import keccak
from numba import cuda

RC = np.array(
    [
        0x0000000000000001,
        0x0000000000008082,
        0x800000000000808A,
        0x8000000080008000,
        0x000000000000808B,
        0x0000000080000001,
        0x8000000080008081,
        0x8000000000008009,
        0x000000000000008A,
        0x0000000000000088,
        0x0000000080008009,
        0x000000008000000A,
        0x000000008000808B,
        0x800000000000008B,
        0x8000000000008089,
        0x8000000000008003,
        0x8000000000008002,
        0x8000000000000080,
        0x000000000000800A,
        0x800000008000000A,
        0x8000000080008081,
        0x8000000000008080,
        0x0000000080000001,
        0x8000000080008008,
    ],
    dtype=np.uint64,
)

RHO = np.array(
    [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44],
    dtype=np.int32,
)

PI = np.array(
    [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1],
    dtype=np.int32,
)


@cuda.jit(device=True)
def rotl64(value, shift):
    shift &= 63
    return ((value << shift) | (value >> np.uint64(64 - shift))) & np.uint64(0xFFFFFFFFFFFFFFFF)


@cuda.jit(device=True)
def keccak_f1600(state):
    bc = cuda.local.array(5, dtype=np.uint64)
    for round_idx in range(24):
        for i in range(5):
            bc[i] = state[i] ^ state[i + 5] ^ state[i + 10] ^ state[i + 15] ^ state[i + 20]

        for i in range(5):
            t = bc[(i + 4) % 5] ^ rotl64(bc[(i + 1) % 5], np.int32(1))
            for j in range(0, 25, 5):
                state[j + i] ^= t

        t = state[1]
        for i in range(24):
            j = PI[i]
            tmp = state[j]
            state[j] = rotl64(t, RHO[i])
            t = tmp

        for j in range(0, 25, 5):
            for i in range(5):
                bc[i] = state[j + i]
            for i in range(5):
                state[j + i] ^= (~bc[(i + 1) % 5]) & bc[(i + 2) % 5]

        state[0] ^= RC[round_idx]


@cuda.jit(device=True)
def hash_below_target(hash_out, t0, t1, t2, t3):
    h0 = (
        (np.uint64(hash_out[0]) << np.uint64(56))
        | (np.uint64(hash_out[1]) << np.uint64(48))
        | (np.uint64(hash_out[2]) << np.uint64(40))
        | (np.uint64(hash_out[3]) << np.uint64(32))
        | (np.uint64(hash_out[4]) << np.uint64(24))
        | (np.uint64(hash_out[5]) << np.uint64(16))
        | (np.uint64(hash_out[6]) << np.uint64(8))
        | np.uint64(hash_out[7])
    )
    if h0 < t0:
        return True
    if h0 > t0:
        return False

    h1 = (
        (np.uint64(hash_out[8]) << np.uint64(56))
        | (np.uint64(hash_out[9]) << np.uint64(48))
        | (np.uint64(hash_out[10]) << np.uint64(40))
        | (np.uint64(hash_out[11]) << np.uint64(32))
        | (np.uint64(hash_out[12]) << np.uint64(24))
        | (np.uint64(hash_out[13]) << np.uint64(16))
        | (np.uint64(hash_out[14]) << np.uint64(8))
        | np.uint64(hash_out[15])
    )
    if h1 < t1:
        return True
    if h1 > t1:
        return False

    h2 = (
        (np.uint64(hash_out[16]) << np.uint64(56))
        | (np.uint64(hash_out[17]) << np.uint64(48))
        | (np.uint64(hash_out[18]) << np.uint64(40))
        | (np.uint64(hash_out[19]) << np.uint64(32))
        | (np.uint64(hash_out[20]) << np.uint64(24))
        | (np.uint64(hash_out[21]) << np.uint64(16))
        | (np.uint64(hash_out[22]) << np.uint64(8))
        | np.uint64(hash_out[23])
    )
    if h2 < t2:
        return True
    if h2 > t2:
        return False

    h3 = (
        (np.uint64(hash_out[24]) << np.uint64(56))
        | (np.uint64(hash_out[25]) << np.uint64(48))
        | (np.uint64(hash_out[26]) << np.uint64(40))
        | (np.uint64(hash_out[27]) << np.uint64(32))
        | (np.uint64(hash_out[28]) << np.uint64(24))
        | (np.uint64(hash_out[29]) << np.uint64(16))
        | (np.uint64(hash_out[30]) << np.uint64(8))
        | np.uint64(hash_out[31])
    )
    return h3 < t3


@cuda.jit(device=True)
def keccak256_84(miner, nonce, work_block, hash_out):
    state = cuda.local.array(25, dtype=np.uint64)
    for i in range(25):
        state[i] = np.uint64(0)

    input_buf = cuda.local.array(84, dtype=np.uint8)
    for i in range(20):
        input_buf[i] = miner[i]
    for i in range(32):
        shift = np.uint64(8 * (31 - i))
        input_buf[20 + i] = np.uint8((nonce >> shift) & np.uint64(0xFF))
    for i in range(32):
        input_buf[52 + i] = work_block[i]

    for i in range(84):
        state[i >> 3] ^= np.uint64(input_buf[i]) << np.uint64(8 * (i & 7))

    state[10] ^= np.uint64(0x01) << np.uint64(32)
    state[16] ^= np.uint64(0x8000000000000000)

    keccak_f1600(state)

    for i in range(32):
        hash_out[i] = np.uint8((state[i >> 3] >> np.uint64(8 * (i & 7))) & np.uint64(0xFF))


@cuda.jit
def usst_mine_kernel(miner, work_block, start_nonce, batch_size, t0, t1, t2, t3, result_nonce):
    idx = cuda.grid(1)
    if idx >= batch_size:
        return

    nonce = start_nonce + np.uint64(idx)
    hash_out = cuda.local.array(32, dtype=np.uint8)
    keccak256_84(miner, nonce, work_block, hash_out)

    if hash_below_target(hash_out, t0, t1, t2, t3):
        cuda.atomic.min(result_nonce, 0, np.int64(nonce))


def hash_work(miner: str, nonce: int, work_block: int) -> int:
    payload = encode_packed(["address", "uint256", "uint256"], [miner, nonce, work_block])
    return int.from_bytes(keccak(payload), "big")


def target_to_limbs(target: int) -> tuple[int, int, int, int]:
    b = target.to_bytes(32, "big")
    return (
        int.from_bytes(b[0:8], "big"),
        int.from_bytes(b[8:16], "big"),
        int.from_bytes(b[16:24], "big"),
        int.from_bytes(b[24:32], "big"),
    )


def miner_address_bytes(miner: str) -> np.ndarray:
    raw = miner.lower().removeprefix("0x")
    return np.frombuffer(bytes.fromhex(raw), dtype=np.uint8)


def work_block_bytes(work_block: int) -> np.ndarray:
    return np.frombuffer(work_block.to_bytes(32, "big"), dtype=np.uint8)


def _auto_batch_size() -> int:
    """Pick a batch large enough to keep the GPU clocked at full boost.

    Larger batches = longer kernel runs = driver keeps GPU in P0 state.
    For RTX 4060 (8 GB) 512 M hashes takes ~0.75 s at full speed — enough
    to prevent the driver from clocking down between launches.
    """
    env = os.getenv("USST_GPU_BATCH_SIZE", "").strip()
    if env:
        return max(1 << 20, int(env))
    try:
        _, _, total = cuda.current_context().get_memory_info()
        gb = total / (1024**3)
        if gb >= 16:
            return 1 << 30   # 1 B
        if gb >= 8:
            return 1 << 29   # 512 M  (was 128 M)
        if gb >= 6:
            return 1 << 28   # 256 M  (was 64 M)
        return 1 << 27       # 128 M
    except Exception:
        return 1 << 29


def _threads_per_block() -> int:
    env = os.getenv("USST_GPU_THREADS", "").strip()
    return int(env) if env else 256


# Optional sleep between GPU kernel launches (seconds).
# 0 = full speed; 0.1–0.5 = moderate; 1.0 = light mining.
_GPU_BATCH_SLEEP: float = float(os.getenv("USST_GPU_BATCH_SLEEP", "0"))


_THREADS_PER_BLOCK = _threads_per_block()


def _cuda_works() -> bool:
    try:
        if cuda.is_available():
            return True
        # Docker Desktop + WSL2: device is usable even when is_available() is False.
        cuda.get_current_device()
        return True
    except Exception:
        return False


class GPUSearcher:
    """CUDA-based nonce searcher with true double-buffer pipelining.

    Two CUDA streams alternate so the GPU is always computing while the CPU
    processes the previous batch's result.  The sequence is:

        Stream A: [==K0==]       [==K2==]       [==K4==]
        Stream B:       [==K1==]       [==K3==]
        CPU:      launch  sync-A  launch  sync-B  launch  sync-A ...

    The GPU is never idle between batch submissions.
    """

    def __init__(self) -> None:
        if not _cuda_works():
            raise RuntimeError("CUDA GPU not available. Install NVIDIA drivers or use --cpu.")
        dev = cuda.get_current_device()
        self.device_name = dev.name.decode()
        self.batch_size = _auto_batch_size()
        # Double-buffer always uses exactly 2 streams regardless of env var.
        self.stream_count = 2
        self._tpb = _threads_per_block()
        self._blocks = (self.batch_size + self._tpb - 1) // self._tpb

        # Pre-allocate device buffers once.
        self._miner_dev = cuda.device_array(20, dtype=np.uint8)
        self._work_dev = cuda.device_array(32, dtype=np.uint8)
        self._result_devs = [cuda.device_array(1, dtype=np.int64) for _ in range(2)]
        self._cuda_streams = [cuda.stream() for _ in range(2)]
        self._sentinel = np.array([np.iinfo(np.int64).max], dtype=np.int64)

        self._last_miner: Optional[str] = None
        self._last_work_block: Optional[int] = None

        # Double-buffer state: which slot is the "hot" (already-launched) one.
        self._hot: int = -1          # -1 = no prefetch in flight
        self._hot_nonce: int = 0
        self._hot_t: tuple = (0, 0, 0, 0)

    def _launch(self, slot: int, nonce: int, t0: int, t1: int, t2: int, t3: int) -> None:
        stream = self._cuda_streams[slot]
        result_dev = self._result_devs[slot]
        result_dev.copy_to_device(self._sentinel, stream=stream)
        usst_mine_kernel[self._blocks, self._tpb, stream](
            self._miner_dev,
            self._work_dev,
            np.uint64(nonce),
            np.uint64(self.batch_size),
            np.uint64(t0),
            np.uint64(t1),
            np.uint64(t2),
            np.uint64(t3),
            result_dev,
        )

    def _collect(self, slot: int, miner: str, work_block: int, target: int) -> Optional[int]:
        self._cuda_streams[slot].synchronize()
        val = int(self._result_devs[slot].copy_to_host()[0])
        if val == np.iinfo(np.int64).max:
            return None
        if hash_work(miner, val, work_block) < target:
            return val
        return None

    def search(
        self,
        miner: str,
        work_block: int,
        target: int,
        start_nonce: int,
    ) -> tuple[Optional[int], int]:
        t0, t1, t2, t3 = target_to_limbs(target)

        ctx_changed = False
        if miner != self._last_miner:
            cuda.to_device(miner_address_bytes(miner), to=self._miner_dev)
            self._last_miner = miner
            ctx_changed = True
        if work_block != self._last_work_block:
            cuda.to_device(work_block_bytes(work_block), to=self._work_dev)
            self._last_work_block = work_block
            ctx_changed = True

        if ctx_changed:
            # Discard any in-flight prefetch — its nonce/context is stale.
            self._hot = -1

        if self._hot == -1:
            # Cold start: launch slot 0, prefetch slot 1, collect slot 0.
            self._launch(0, start_nonce, t0, t1, t2, t3)
            prefetch_nonce = start_nonce + self.batch_size
            self._launch(1, prefetch_nonce, t0, t1, t2, t3)
            self._hot = 1
            self._hot_nonce = prefetch_nonce
            self._hot_t = (t0, t1, t2, t3)

            result = self._collect(0, miner, work_block, target)
            return result, self.batch_size

        # Hot path: slot self._hot already running from the previous call.
        # Immediately launch the NEXT prefetch on the OTHER slot so the GPU
        # keeps running while we sync and copy.
        prev_hot = self._hot
        next_slot = 1 - prev_hot
        next_nonce = self._hot_nonce + self.batch_size
        self._launch(next_slot, next_nonce, t0, t1, t2, t3)

        # Now collect the previously hot slot.
        result = self._collect(prev_hot, miner, work_block, target)

        self._hot = next_slot
        self._hot_nonce = next_nonce
        self._hot_t = (t0, t1, t2, t3)

        if _GPU_BATCH_SLEEP > 0:
            time.sleep(_GPU_BATCH_SLEEP)

        return result, self.batch_size


def gpu_available() -> bool:
    try:
        GPUSearcher()
        return True
    except Exception:
        return False


def create_gpu_searcher() -> GPUSearcher:
    return GPUSearcher()
