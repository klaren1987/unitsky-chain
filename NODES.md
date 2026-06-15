# Running a Node or Validator on UST Network

## Overview

The UST network uses **Clique Proof-of-Authority** (EIP-225) for block production and supports multiple authorized signer nodes. This document covers:

1. Running a **full node** (syncs the chain, participates in the network, can submit transactions)
2. Becoming an **authorized signer** (produces blocks, must be voted in by existing signers)

---

## Network Parameters

| Parameter | Value |
|---|---|
| Chain ID | `778889` |
| Block time | ~5 seconds |
| Gas limit | 30,000,000 |
| Genesis | [`chain/genesis.json`](chain/genesis.json) |
| Public RPC | `https://147-45-143-23.sslip.io/rpc` |
| Consensus | Clique PoA (EIP-225) |

---

## 1. Running a Full Node

A full node syncs all blocks and exposes a local RPC. It does not produce blocks unless it is an authorized signer.

### Requirements

- Linux VPS or bare metal (1 CPU, 2 GB RAM minimum; 4 GB recommended)
- 20 GB SSD storage
- Docker and Docker Compose installed
- Static IP address (recommended for peering)

### Setup

```bash
git clone https://github.com/klaren1987/UST-chain.git
cd?? UST-chain
cp .env.windows-node.example .env  # or create a minimal .env
```

Edit `.env`:
```env
USST_RPC=http://127.0.0.1:8545
USST_CHAIN_ID=778889
```

Start the node:
```bash
docker compose -f docker-compose.node.yml up -d
```

Verify sync:
```bash
docker compose -f docker-compose.node.yml logs -f usst-node
# Look for: "Imported new chain segment" — your node is syncing
```

Check block number:
```bash
curl -s -X POST http://127.0.0.1:8545 \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Connecting to Peers

Add the public bootnode to your node's static peers. The public node's enode URI is:

```
enode://[ENODE_PUBKEY]@147.45.143.23:30303
```

To get the current bootnode enode:
```bash
curl -s https://147-45-143-23.sslip.io/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"admin_nodeInfo","params":[],"id":1}' | jq .result.enode
```

Add to your `static-nodes.json` (inside the data directory) or pass via `--bootnodes` flag.

---

## 2. Becoming an Authorized Signer

Authorized signers produce blocks. The Clique protocol governs admission via on-chain voting:
- Any existing signer can propose a new signer (or remove an existing one)
- A candidate is admitted when `floor(N/2) + 1` existing signers vote in favor
- Currently the network has **1 authorized signer** — a second signer requires 1 vote (the existing signer)

### Requirements for Signers

- A dedicated server with high availability (target: 99.9% uptime)
- Static IP address reachable by other signers
- Ethereum address generated offline (hardware wallet recommended)
- Technical ability to manage a Geth node

### Signer Key Setup

Generate a new Ethereum account for signing:
```bash
docker run --rm -v $(pwd)/keystore:/keystore ethereum/client-go account new --keystore /keystore
```

Or use `eth_account` in Python:
```python
from eth_account import Account
acct = Account.create()
print("Address:", acct.address)
print("Key:    ", acct.key.hex())
```

**Important:** Never use a key that holds real funds on Ethereum mainnet as a signer key.

### Proposing Yourself as a Signer

1. Contact the network operator via [GitHub Issues](https://github.com/klaren1987/UST-chain/issues) with:
   - Your Ethereum address
   - Your node's enode URI
   - Your server's location and uptime commitment

2. The existing signer will vote your address in via `clique_propose`:
   ```bash
   # On the existing signer node:
   geth attach --exec 'clique.propose("0xYOUR_ADDRESS", true)' /path/to/geth.ipc
   ```

3. Once your address appears in `clique_getSigners`, configure your node with the signer key:
   ```bash
   geth --unlock 0xYOUR_ADDRESS --mine --miner.etherbase 0xYOUR_ADDRESS ...
   ```

### Verifying the Signer Set

Query at any time:
```bash
curl -s -X POST https://147-45-143-23.sslip.io/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"clique_getSigners","params":["latest"],"id":1}'
```

---

## 3. WireGuard VPN (Optional)

For low-latency peer connections between nodes, the network uses optional **WireGuard VPN** tunnels. Example configs are in [`config/wireguard/`](config/wireguard/).

VPN is not required to run a full node or mine — it is an optional optimization for validator-to-validator connectivity.

---

## 4. Mining from Your Node

Once your full node is synced, you can point the miner at your local RPC instead of the public endpoint:

```env
USST_RPC=http://127.0.0.1:8545
USST_MINER_KEY=0xYOUR_MINER_KEY
USST_CONTRACT_ADDRESS=0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0
```

```bash
docker compose up -d miner
```

Mining from a local node reduces latency and improves your chances of getting proofs included before the 10-block work window expires.

---

## 5. Node Monitoring

Check node health:
```bash
# Block number
curl -s -X POST http://127.0.0.1:8545 -H 'Content-Type: application/json' \
  -d '{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}'

# Peer count
curl -s -X POST http://127.0.0.1:8545 -H 'Content-Type: application/json' \
  -d '{"method":"net_peerCount","params":[],"id":1,"jsonrpc":"2.0"}'

# Clique status
curl -s -X POST http://127.0.0.1:8545 -H 'Content-Type: application/json' \
  -d '{"method":"clique_status","params":[],"id":1,"jsonrpc":"2.0"}'
```

---

## Support

Open an issue at [github.com/klaren1987/UST-chain/issues](https://github.com/klaren1987/UST-chain/issues) with the label `node-setup`.
