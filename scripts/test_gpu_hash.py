#!/usr/bin/env python3
"""Verify GPU Keccak matches CPU hash_work."""

from eth_abi.packed import encode_packed
from eth_hash.auto import keccak

from miner.gpu_engine import GPUSearcher, hash_work


def main() -> int:
    miner = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    work_block = 42
    difficulty = 500_000
    target = (2**256 - 1) // difficulty

    cpu_nonce = None
    for nonce in range(5_000_000):
        if hash_work(miner, nonce, work_block) < target:
            cpu_nonce = nonce
            break

    if cpu_nonce is None:
        print("CPU: no nonce found in range (unexpected)")
        return 1

    print(f"CPU found nonce={cpu_nonce}")

    gpu = GPUSearcher()
    print(f"GPU device: {gpu.device_name}")

    found, tried = gpu.search(miner, work_block, target, 0)
    print(f"GPU batch tried={tried:,}, found={found}")

    if found is None:
        print("GPU: no nonce in first batch")
        return 1

    if keccak(encode_packed(["address", "uint256", "uint256"], [miner, found, work_block])) != keccak(
        encode_packed(["address", "uint256", "uint256"], [miner, cpu_nonce, work_block])
    ):
        if hash_work(miner, found, work_block) >= target:
            print("GPU nonce FAILED verification")
            return 1

    print(f"GPU nonce={found} verified OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
