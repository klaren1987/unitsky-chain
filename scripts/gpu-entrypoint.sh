#!/bin/sh
set -e

# Docker Desktop on WSL2: numba needs the host libcuda path, not CUDA compat stubs.
WSL_CUDA_LIB="$(find /usr/lib/wsl/drivers -name 'libcuda.so.1' 2>/dev/null | head -1)"
if [ -n "$WSL_CUDA_LIB" ]; then
  WSL_CUDA_DIR="$(dirname "$WSL_CUDA_LIB")"
  export LD_LIBRARY_PATH="${WSL_CUDA_DIR}:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
fi

# Performance defaults (override via .env.miner)
export USST_GPU_STREAMS="${USST_GPU_STREAMS:-2}"
export USST_GPU_THREADS="${USST_GPU_THREADS:-256}"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-/tmp/numba-cache}"

exec python -m miner.usst_miner "$@"
