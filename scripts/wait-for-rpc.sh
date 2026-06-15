#!/bin/sh
set -e

RPC_URL="${1:-http://usst-node:8545}"
MAX_ATTEMPTS="${2:-60}"

attempt=0
while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  if curl -sf -X POST "$RPC_URL" \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' >/dev/null; then
    echo "RPC ready: $RPC_URL"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 2
done

echo "RPC not ready after ${MAX_ATTEMPTS} attempts: $RPC_URL" >&2
exit 1
