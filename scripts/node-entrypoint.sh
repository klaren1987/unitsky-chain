#!/bin/sh
set -e

GENESIS=/genesis.json
DATADIR=/data
SIGNER_KEY="${USST_SIGNER_KEY#0x}"

if [ -z "$SIGNER_KEY" ]; then
  echo "USST_SIGNER_KEY is required" >&2
  exit 1
fi

if [ -z "$USST_SIGNER_ADDRESS" ]; then
  echo "USST_SIGNER_ADDRESS is required" >&2
  exit 1
fi

if [ ! -f "$DATADIR/geth/chaindata/CURRENT" ]; then
  geth --datadir "$DATADIR" init "$GENESIS"
fi

SIGNER_ADDRESS="$USST_SIGNER_ADDRESS"

if ! geth account list --datadir "$DATADIR" 2>/dev/null | grep -qi "${SIGNER_ADDRESS#0x}"; then
  # Write key to a tmpfs-backed path and remove immediately after import.
  PK_FILE="$(mktemp)"
  printf '%s' "$SIGNER_KEY" > "$PK_FILE"
  geth --datadir "$DATADIR" account import --password /dev/null "$PK_FILE"
  rm -f "$PK_FILE"
fi

# Security notes:
#   --http.addr 0.0.0.0   : Geth listens on all interfaces inside Docker.
#                           Access from outside the host is blocked by:
#                           (a) docker-compose port binding to 127.0.0.1 only, and
#                           (b) the RPC filter proxy (rpc-filter service) that strips
#                               dangerous methods (eth_sendTransaction, admin_*, etc.)
#                           before forwarding to Caddy / the public internet.
#   --allow-insecure-unlock: Required by Geth to unlock the Clique PoA signer over HTTP.
#                            The signer account is used exclusively for block signing
#                            (--mine), not for user transactions.
exec geth --datadir "$DATADIR" \
  --networkid "${USST_CHAIN_ID:-778889}" \
  --syncmode full \
  --gcmode archive \
  --http --http.addr 0.0.0.0 --http.port 8545 \
  --http.api eth,net,web3,txpool,debug \
  --http.corsdomain "*" \
  --http.vhosts "*" \
  --ws --ws.addr 0.0.0.0 --ws.port 8546 \
  --ws.api eth,net,web3,txpool,debug \
  --ws.origins "*" \
  --allow-insecure-unlock \
  --unlock "$SIGNER_ADDRESS" \
  --password /dev/null \
  --mine \
  --miner.etherbase "$SIGNER_ADDRESS" \
  --nodiscover
