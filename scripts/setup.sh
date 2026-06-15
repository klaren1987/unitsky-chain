#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "==> Building and starting UST Network stack..."
docker compose up --build -d

echo ""
echo "==> Services:"
docker compose ps

echo ""
echo "==> Follow miner logs:"
echo "    docker compose logs -f miner"
echo ""
echo "==> MetaMask: add network from metamask-network.json (RPC http://127.0.0.1:8545)"
echo "==> Miner wallet import key is in .env (USST_MINER_KEY)"
