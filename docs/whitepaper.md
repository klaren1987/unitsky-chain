# Unitsky String Technologies — Network Whitepaper

**Version 1.0 — June 2026**

---

## Abstract

Unitsky String Technologies (UST) is an independent EVM-compatible blockchain network built on Geth with Clique Proof-of-Authority consensus for block production and a Proof-of-Work smart contract for fair, permissionless token distribution. The network is designed for low-cost, high-speed transactions with transparent on-chain mining rewards.

---

## 1. Network Overview

| Parameter | Value |
|-----------|-------|
| Chain ID | **778889** (0xBE289) |
| Consensus | Clique PoA (5-second blocks) |
| Native Token | **UST** |
| Mining | PoW smart contract (keccak256) |
| RPC | https://147-45-143-23.sslip.io/rpc |
| Explorer | https://147-45-143-23.sslip.io |
| Block time | ~5 seconds |
| Gas limit | 30,000,000 |

---

## 2. Token Economics

| Parameter | Value |
|-----------|-------|
| Token symbol | **UST** |
| Decimals | 18 |
| Initial supply | 10,000 UST (mining pool) |
| Block reward | **1 UST** per valid proof-of-work |
| Mining difficulty | 500,000 (adjustable by governance) |
| Maximum supply | Controlled by pool funding |

UST is the **native currency** of the Unitsky network — used for gas fees, staking, and as a medium of exchange within the ecosystem.

---

## 3. Consensus Mechanism

### Block Production (Clique PoA)
Blocks are produced every **5 seconds** by a designated signer node using the Clique Proof-of-Authority algorithm. This ensures:
- Deterministic, fast finality
- No energy-intensive Proof-of-Work for block creation
- Resistance to 51% attacks

### Token Distribution (PoW Contract)
UST tokens are distributed through the **USSTMine** smart contract deployed at:
```
0x5FbDB2315678afecb367f032d93F642f64180aa3
```

Miners submit a valid proof-of-work:
```
keccak256(miner_address, nonce, work_block) < target
```

Where `target = 2^256 / difficulty`.

A valid proof earns the miner **1 UST** from the mining pool. The 10-block work window prevents stale submissions.

---

## 4. Technology Stack

| Component | Technology |
|-----------|-----------|
| Node | Geth 1.13+ |
| Smart Contracts | Solidity 0.8.20 |
| Miner | Python + CUDA (GPU) / CPU fallback |
| RPC/HTTPS | Caddy 2 (Let's Encrypt) |
| Explorer | Custom SPA (Geth JSON-RPC) |
| Network | WireGuard VPN + VPS |

### GPU Mining Performance
The reference miner achieves approximately **686 MH/s** on an NVIDIA RTX 4060, using:
- Batch size: 128M hashes/batch
- Dual CUDA streams
- Synchronous transaction submission to prevent reverts

---

## 5. Smart Contract

The `USSTMine.sol` contract features:
- **Anti-double-spend**: each `(miner, nonce, workBlock)` triplet is single-use
- **Pool transparency**: `poolBalance()` is publicly readable
- **Adjustable parameters**: owner can update `difficulty` and `reward`
- **Emergency withdrawal**: owner can recover pool funds

```solidity
function mine(uint256 nonce, uint256 workBlock) external {
    // Validates PoW proof, prevents double-claiming
    // Sends 1 UST reward to caller
}
```

---

## 6. Public Infrastructure

| Service | URL |
|---------|-----|
| HTTPS RPC | https://147-45-143-23.sslip.io/rpc |
| WebSocket | wss://147-45-143-23.sslip.io/ws |
| Block Explorer | https://147-45-143-23.sslip.io |
| Chain Icon | https://147-45-143-23.sslip.io/icon.svg |
| Chainlist PR | https://github.com/DefiLlama/chainlist/pull/2830 |

The public RPC is secured with a **Let's Encrypt TLS certificate**, making it compatible with MetaMask and other browser-based wallets without warnings.

---

## 7. MetaMask Integration

Add the Unitsky network to MetaMask:

| Field | Value |
|-------|-------|
| Network Name | Unitsky String Technologies |
| RPC URL | https://147-45-143-23.sslip.io/rpc |
| Chain ID | 778889 |
| Currency Symbol | UST |
| Block Explorer | https://147-45-143-23.sslip.io |

---

## 8. Mining Guide

### Docker (recommended)

```bash
git clone https://github.com/klaren1987/unitsky-chain
cp .env.miner.example .env.miner
# Edit .env.miner: add your USST_MINER_KEY
docker compose -f docker-compose.miner.yml up -d
```

### Python (local)

```bash
pip install -r requirements.txt
USST_RPC=https://147-45-143-23.sslip.io/rpc \
USST_MINER_KEY=0xYOUR_KEY \
python -m miner.usst_miner
```

GPU mining (NVIDIA required):
```bash
USST_GPU=1 python -m miner.usst_miner
```

---

## 9. Network Statistics (June 2026)

| Metric | Value |
|--------|-------|
| Blocks produced | ~1,947 |
| Total UST mined | ~1,691 UST |
| Mining pool remaining | ~8,309 UST |
| Block time | 5 seconds |
| RPC uptime | 99%+ |

---

## 10. Roadmap

| Phase | Target | Status |
|-------|--------|--------|
| Network launch | Q1 2026 | ✅ Done |
| Public RPC + Explorer | Q2 2026 | ✅ Done |
| Chainlist listing | Q2 2026 | 🔄 Pending review |
| CoinGecko listing | Q3 2026 | 📋 Submitted |
| DEX (UST/USDT pair) | Q3 2026 | 🔜 Planned |
| Bridge to Ethereum/BSC | Q4 2026 | 🔜 Planned |
| CoinMarketCap listing | Q4 2026 | 📋 Submitted |

---

## 11. Contact & Links

| Resource | Link |
|----------|------|
| Explorer | https://147-45-143-23.sslip.io |
| RPC | https://147-45-143-23.sslip.io/rpc |
| Chainlist | https://github.com/DefiLlama/chainlist/pull/2830 |
| GitHub | https://github.com/klaren1987/unitsky-chain |

---

*This document is provided for informational purposes. Unitsky String Technologies is an experimental blockchain network. Use at your own risk.*
