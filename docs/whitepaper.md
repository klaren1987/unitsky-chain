# UST Network — Network Whitepaper

**Version 4.0 — June 2026**

---

## Abstract

UST Network (UST) is an independent EVM-compatible blockchain network built on Geth with **Clique Proof-of-Authority** consensus for block production and a **Proof-of-Work smart contract** for fair, permissionless token distribution. The network is designed for low-cost, high-speed transactions with transparent, auditable on-chain mining rewards.

This architecture — PoA for block consensus, PoW for token distribution — is an **intentional hybrid design**, not a compromise. It provides:

- **Fast finality** (5-second blocks, deterministic) without the energy cost of proof-of-work mining at the chain level
- **Permissionless participation** (anyone can mine, no registration, no KYC) without sacrificing block-time predictability
- **Transparent token issuance** via an open-source, audited smart contract with immutable halving and burn rules
- **DeFi composability** on a full EVM chain with the same tooling as Ethereum (MetaMask, ethers.js, Hardhat, Foundry)


---

## A. Architecture: Why Hybrid PoA + PoW?

The combination of Proof-of-Authority block production with Proof-of-Work token distribution is a deliberate architectural decision. This section explains the rationale.

### The Problem with Pure PoW for a New Chain

A chain that uses PoW for both block production and token distribution (like early Bitcoin or Ethereum) faces a bootstrapping problem: it requires significant hash-rate from day one to prevent 51% attacks. For a new chain, this hash-rate does not exist.

The result is a chain that is either:
- Insecure (low hash-rate → trivial to attack), or
- Centralized in practice (a small group controls the hash-rate anyway)

### The Problem with Pure PoA

Clique PoA without a token distribution mechanism means the token must be pre-allocated — either to founders (ICO/pre-mine) or to the chain operator. This concentrates wealth and trust.

### The Hybrid Solution

UST separates the two roles:

| Role | Mechanism | Properties |
|---|---|---|
| **Block production** | Clique PoA | Fast (5s), deterministic, energy-efficient, multi-signer capable |
| **Token distribution** | PoW smart contract | Permissionless, transparent, auditable, no pre-mine |

This is **not** a new idea — several deployed networks use this or analogous patterns:
- **BSC / BNB Chain**: PoA (21 validators) + DPoS for block production; BNB was distributed via token sale
- **xDAI / Gnosis Chain**: PoA for blocks; xDAI minted from DAI collateral (protocol-enforced, not admin)
- **Optimism, Arbitrum**: centralized sequencer (similar trust model to PoA) + token distribution via airdrop/mining

The difference with UST: token distribution is governed by **an on-chain PoW smart contract** with no admin keys for the emission schedule. The difficulty, halving, and burn are immutable in their logic; only the `difficulty` parameter is adjustable (via 48-hour timelock, with `MIN_DIFFICULTY = 100,000` floor).

### Trust Model Summary

```
Block production:  operator-controlled (Clique signer) — transparent, can be expanded
Token emission:    contract-controlled (USSTMine v4)   — audited, timelocked governance
Pool funding:      operator-funded, open-source watchdog, on-chain events
Bridge:            operator-relayed (Phase 1), on-chain escrow (EscrowUSDT.sol, Phase 2)
DEX liquidity:     LP tokens burned at genesis — permanent, no rug possible
```

No part of this model is hidden. The trade-offs are explicitly documented.

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
| Initial pool | 10,000 UST (funded at deployment) |
| Era-0 reward | **0.1 UST** gross per proof (0.098 UST net after 2% burn) |
| Halving interval | every 50,000 proofs |
| Minimum reward | 0.001 UST (floor, era 7+) |
| Burn per reward | 2% → `0x000…dEaD` permanently |
| Mining difficulty | 500,000 (adjustable via 48 h timelock) |
| Total supply (eras 0–6) | ≈ 9,922 UST gross; ≈ 9,722 UST net after burn |

UST is the **native gas token** of the UST network — used to pay transaction fees and received as mining rewards. There is no ICO and no private investor allocation.

### 2.1 Genesis Allocation — Full Transparency

The genesis block (`chain/genesis.json`) pre-allocates UST for network bootstrapping. This is standard for PoA networks and is disclosed here in full:

| Address | Amount | Purpose |
|---|---|---|
| Signer node address | 1,000,000 UST | Network operational reserve (validator costs, infrastructure) |
| Deployer address | 1,000 UST | Initial gas for contract deployments |

**Why this is not a pre-mine:**
- Neither allocation can be sold into the DEX — the DEX pool is funded exclusively by the deployer's operational reserve, and LP tokens are 100% burned. No selling pressure from genesis.
- The mining pool (`USSTMine v4`) is funded separately from the deployer's reserve, not from the signer allocation.
- The signer address's 1M UST serves the same role as a foundation reserve in any L1: covering RPC hosting, validator infrastructure, bug bounties, and ecosystem development.

**Pool transparency:** the mining pool refill is handled by an open-source watchdog service ([`scripts/pool-watchdog.py`](../scripts/pool-watchdog.py)). Every refill transaction emits a `FundAdded` event on-chain, visible in the explorer to anyone at any time.

---

## 3. Consensus Mechanism

### Block Production (Clique PoA — EIP-225)

Blocks are produced every **5 seconds** by authorized signer nodes using the **Clique Proof-of-Authority** algorithm (Ethereum EIP-225). This is the same consensus mechanism used by many established EVM networks and Ethereum testnets.

Clique properties:
- **Fast finality**: transactions are confirmed within one block (~5 seconds)
- **Energy-efficient**: no proof-of-work for block production
- **MEV-resistant by design**: the signer schedule is deterministic; signers cannot reorder blocks beyond their designated turn
- **Multi-signer capable**: the Clique protocol supports any number of authorized signers, added or removed by majority vote — no unilateral control
- **Transparent**: the current signer set is always queryable via `clique_getSigners`

The signer set is managed on-chain via the Clique voting mechanism. To propose a new signer, an existing signer votes by including the candidate in a block's `extraData` field; the candidate is admitted when `floor(N/2) + 1` existing signers vote in favor, where N is the current signer count.

See [NODES.md](../NODES.md) for validator requirements and the process for joining the signer set.

### Token Distribution (PoW Contract)
UST tokens are distributed through the **USSTMine v4** smart contract deployed at:
```
0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0
```

Miners submit a valid proof-of-work:
```
keccak256(abi.encodePacked(miner_address, nonce, work_block)) < target
```

Where `target = 2^256 / difficulty`.

A valid proof earns the miner **`minerReward()`** UST (gross reward minus 2% burn). In era 0 this is 0.098 UST net. The 10-block work window prevents stale submissions; the 48-hour timelock prevents rapid parameter changes.

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
The reference miner achieves approximately **590 MH/s** on an NVIDIA RTX 4060, using:
- Batch size: 128M hashes/batch
- Dual CUDA streams
- Synchronous transaction submission to prevent stale-proof reverts

---

## 5. Smart Contract

`USSTMine.sol` **v4** (deployed `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0`) features:

- **Anti-double-spend**: each `(miner, nonce, workBlock)` triplet is single-use via `_usedWork` mapping
- **Reentrancy guard**: `nonReentrant` modifier on `mine()` — pool drain via malicious receiver contract is impossible
- **Pool transparency**: `poolBalance()` is publicly readable at any time
- **Halving + burn**: `reward()` returns the current era reward (halves every 50,000 proofs); 2% is automatically burned on every `mine()` call
- **48-hour timelock**: difficulty changes and ownership transfers require an on-chain queue before execution
- **7-day withdrawal timelock**: any pool withdrawal must be queued 7 days in advance and is visible to all participants — no instant removal of funds
- **Minimum difficulty floor**: `MIN_DIFFICULTY = 100,000` prevents administrative lowering to trivially easy values
- **Typed governance operations**: `queueDifficulty`, `executeDifficulty`, `queueOwnershipTransfer`, `queueWithdraw` — no raw calldata execution

```solidity
// nonReentrant prevents pool drain via reentrant receive() hook
function mine(uint256 nonce, uint256 workBlock) external nonReentrant {
    // 1. Validate proof (CEI: all state changes before external calls)
    // 2. Mark (miner, nonce, workBlock) as used
    // 3. Increment totalMined, update totalBurned
    // 4. Send 2% burn to 0x…dEaD
    // 5. Send 98% net reward to miner
}
```

Full security analysis: [SECURITY.md](../SECURITY.md)

---

## 6. Public Infrastructure

| Service | URL |
|---------|-----|
| HTTPS RPC | https://147-45-143-23.sslip.io/rpc |
| WebSocket | wss://147-45-143-23.sslip.io/ws |
| Block Explorer | https://147-45-143-23.sslip.io |
| Chain Icon | https://147-45-143-23.sslip.io/icon.svg |
| Chainlist | https://chainlist.org/chain/778889 |
| DEX | https://147-45-143-23.sslip.io/dex |
| Faucet | https://147-45-143-23.sslip.io/faucet |

The public RPC is secured with a **Let's Encrypt TLS certificate**, making it compatible with MetaMask and other browser-based wallets without warnings.

---

## 7. MetaMask Integration

Add the UST network to MetaMask:

| Field | Value |
|-------|-------|
| Network Name | UST Network |
| RPC URL | https://147-45-143-23.sslip.io/rpc |
| Chain ID | 778889 |
| Currency Symbol | UST |
| Block Explorer | https://147-45-143-23.sslip.io |

---

## 8. Mining Guide

### Docker (recommended)

```bash
git clone https://github.com/klaren1987/UST-chain
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
| Blocks produced | 50,000+ |
| Total proofs submitted | 4,800+ |
| Total UST burned | 9.5+ UST (to `0xdead`) |
| Mining pool balance | 18,300+ UST |
| Block time | 5 seconds |
| RPC uptime | 99%+ |

*Statistics are live — check the [Explorer](https://147-45-143-23.sslip.io) for real-time data.*

---

## 10. Bridge Architecture

The USDT bridge connects Ethereum mainnet to Chain 778889. It operates in two phases:

### Phase 1 — Operator Bridge (current)
The bridge relayer monitors both chains and mints/burns `BridgedUSDT` on Chain 778889 in response to USDT movements on Ethereum. The Ethereum-side USDT is held by the operator address (treasury).

Security measures active:
- Double-spend guard: every processed Ethereum tx hash is stored on-chain in the `BridgedUSDT` contract
- Rate limiting: 5 deposits/address/hour; 1–10,000 USDT per deposit
- Audit log: all bridge actions are recorded in `logs/bridge-audit.log`
- Pre-flight check: treasury balance is verified before every withdrawal

### Phase 2 — Trustless Escrow Bridge (roadmap Q3 2026)
`contracts/EscrowUSDT.sol` is written and ready to deploy on Ethereum mainnet. It replaces the operator EOA with a smart contract escrow:

- User deposits go **directly into the escrow contract** (not an operator wallet)
- Releases require an on-chain signature from the authorized signer set (m-of-n)
- The signer set is governed by a timelocked owner
- The `released[ustTxHash]` mapping prevents any replay attack at the contract level
- The escrow contract is open-source and auditable at `contracts/EscrowUSDT.sol`

Once `EscrowUSDT` is deployed on Ethereum mainnet, the bridge is fully trustless on both sides.

---

## 11. Roadmap

| Phase | Target | Status |
|-------|--------|--------|
| Network launch | Q1 2026 | ✅ Done |
| Public HTTPS RPC + Explorer | Q2 2026 | ✅ Done |
| GPU miner (CUDA) | Q2 2026 | ✅ Done |
| Uniswap V2 DEX (UST/USDT) | Q2 2026 | ✅ Done |
| USDT Bridge operator model | Q2 2026 | ✅ Done |
| ethereum-lists/chains | Q2 2026 | ✅ Merged |
| DefiLlama Chainlist | Q2 2026 | ✅ Merged |
| Smart contract security audit (v4) | Q2 2026 | ✅ Done |
| Pool watchdog service | Q2 2026 | ✅ Done |
| EscrowUSDT.sol (trustless bridge) | Q2 2026 | ✅ Written — pending mainnet deploy |
| wevm/viem | Q2 2026 | ⏳ Pending |
| GeckoTerminal / CoinGecko listing | Q3 2026 | 📋 Submitted |
| Deploy EscrowUSDT on Ethereum mainnet | Q3 2026 | ⬜ Planned |
| Additional validator nodes | Q3 2026 | ⬜ Planned |
| Additional liquidity | Q3 2026 | ⬜ Planned |
| Third-party smart contract audit | Q4 2026 | ⬜ Planned |

---

## 11. Contact & Links

| Resource | Link |
|----------|------|
| Explorer | https://147-45-143-23.sslip.io |
| DEX | https://147-45-143-23.sslip.io/dex |
| Faucet | https://147-45-143-23.sslip.io/faucet |
| Bridge | https://147-45-143-23.sslip.io/bridge |
| RPC | https://147-45-143-23.sslip.io/rpc |
| GitHub | https://github.com/klaren1987/UST-chain |
| Chainlist | https://chainlist.org/chain/778889 |

---

*This document is provided for informational purposes. UST Network is an independent EVM network in active development. Use at your own risk.*
