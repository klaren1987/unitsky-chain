#!/bin/sh
set -e

/app/scripts/wait-for-rpc.sh "${USST_RPC:-http://usst-node:8545}"

DEPLOYED="${USST_DEPLOYED_PATH:-/data/deployed.json}"
if [ -f "$DEPLOYED" ]; then
  ADDR=$(python -c "import json; print(json.load(open('$DEPLOYED'))['contractAddress'])" 2>/dev/null || true)
  if [ -n "$ADDR" ]; then
    CODE=$(curl -sf -X POST "${USST_RPC:-http://usst-node:8545}" \
      -H "Content-Type: application/json" \
      -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getCode\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}" \
      | python -c "import json,sys; print(json.load(sys.stdin).get('result','0x'))" 2>/dev/null || echo "0x")
    if [ "$CODE" != "0x" ] && [ -n "$CODE" ]; then
      echo "Contract already deployed:"
      cat "$DEPLOYED"
      exit 0
    fi
    echo "deployed.json exists but no code on chain — redeploying..."
    rm -f "$DEPLOYED"
  fi
fi

exec python scripts/deploy.py
