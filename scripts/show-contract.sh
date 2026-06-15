#!/usr/bin/env bash
# Print contract address and deployment info from the server.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="${1:-docker-compose.node.yml}"

# Try reading from a running deploy container first (fastest).
if docker compose -f "$COMPOSE_FILE" ps deploy 2>/dev/null | grep -q "deploy"; then
  docker compose -f "$COMPOSE_FILE" logs --no-log-prefix deploy 2>/dev/null | grep -E "(USSTMine deployed|contractAddress)" | tail -5
  exit 0
fi

# Fall back to reading deployed.json from the named volume.
# The volume name is determined by Docker Compose: <project>_usst-config.
PROJECT="$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('name','tebot'))" 2>/dev/null || echo "tebot")"
VOLUME="${PROJECT}_usst-config"

echo "Reading from volume: $VOLUME"
docker run --rm -v "${VOLUME}:/data:ro" alpine cat /data/deployed.json
