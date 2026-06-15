<div align="center">
  <img src="config/caddy/static/icon.svg" width="88" alt="UST" /><br/><br/>

  # UST Network

  **An EVM blockchain where every UST is earned through Proof-of-Work.**  
  No pre-mine · No ICO · No team allocation · Fair launch.

  [![Version](https://img.shields.io/badge/version-4.0.0-00d4aa)](CHANGELOG.md)
  [![Chain ID](https://img.shields.io/badge/Chain_ID-778889-5c6de2?logo=ethereum&logoColor=white)](https://chainlist.org/chain/778889)
  [![RPC Health](https://github.com/klaren1987/UST-chain/actions/workflows/rpc-health.yml/badge.svg)](https://github.com/klaren1987/UST-chain/actions/workflows/rpc-health.yml)
  [![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636?logo=solidity)](contracts/USSTMine.sol)
  [![Security Audit](https://img.shields.io/badge/Security-Audited_v4-3fb950?logo=shieldsdotio)](SECURITY.md)
  [![License: MIT](https://img.shields.io/badge/License-MIT-d4a017)](LICENSE)
  [![ethereum-lists](https://img.shields.io/badge/ethereum--lists-merged-3fb950)](https://github.com/ethereum-lists/chains/pull/8418)
  [![Explorer](https://img.shields.io/badge/Explorer-Blockscout-5c6de2?logo=ethereum)](https://blockscout.byteboost.ru)

  [Blockscout Explorer](https://blockscout.byteboost.ru) · [DEX](https://147-45-143-23.sslip.io/dex) · [Faucet](https://147-45-143-23.sslip.io/faucet) · [Add to MetaMask](https://chainlist.org/chain/778889) · [Whitepaper](docs/whitepaper.md) · [Security](SECURITY.md)

</div>

---

## Overview

UST is the native gas token of Chain ID 778889, distributed **exclusively through on-chain Proof-of-Work mining**. A smart contract accepts keccak256 solutions from any GPU or CPU miner and instantly transfers UST rewards from the pool. The supply schedule mirrors Bitcoin's halving model, with an additional EIP-1559-style burn that permanently removes 2% of every reward.

**Architecture:** Clique PoA for block production (fast, 5s, multi-signer) + PoW smart contract for token distribution (permissionless, audited). This intentional hybrid gives deterministic finality without sacrificing fair token launch. See [Whitepaper Section A](docs/whitepaper.md#a-architecture-why-hybrid-poa--pow) for the full design rationale.

**What makes UST scarce:**

- **~9,922 UST** total across the first 7 eras (see Supply Schedule below)
- Every reward has **2% burned** to the dead address, permanently reducing supply
- Liquidity is **locked forever** — 100% of LP tokens burned at genesis

---

## Network

| Parameter | Value |
|-----------|-------|
| Chain ID | `778889` (0xBE289) |
| Native Token | UST |
| Block Time | ~5 seconds |
| Consensus | Clique PoA (EIP-225) |
| Gas Limit | 30,000,000 |
| RPC | `https://147-45-143-23.sslip.io/rpc` |
| WebSocket | `wss://147-45-143-23.sslip.io/ws` |
| Explorer | https://blockscout.byteboost.ru |

---

## Tokenomics

| Parameter | Value | Analogue |
|-----------|-------|----------|
| Initial reward | **0.1 UST** per proof | Bitcoin: 50 BTC per block |
| Halving interval | **Every 50,000 proofs** | Bitcoin: every 210,000 blocks |
| Minimum reward | **0.001 UST** (floor after era 6) | — |
| Burn per reward | **2%** → `0x000…dEaD` forever | Ethereum EIP-1559 |
| Miner net | **0.098 UST** (98% after burn) | — |
| Admin timelock | **48 hours** (difficulty/ownership) · **7 days** (pool withdrawal) | OpenZeppelin standard |
| LP tokens | **100% burned** permanently | Uniswap LP burn |

### Supply Schedule

| Era | Proof Range | Reward/Proof | Era Total | Cumulative |
|-----|-------------|--------------|-----------|------------|
| **0** ← current | 0 – 49,999 | 0.1 UST | 5,000 UST | 5,000 UST |
| 1 | 50k – 99,999 | 0.05 UST | 2,500 UST | 7,500 UST |
| 2 | 100k – 149,999 | 0.025 UST | 1,250 UST | 8,750 UST |
| 3 | 150k – 199,999 | 0.0125 UST | 625 UST | 9,375 UST |
| 4 | 200k – 249,999 | 0.00625 UST | 312.5 UST | 9,687.5 UST |
| 5 | 250k – 299,999 | 0.003125 UST | 156.25 UST | 9,843.75 UST |
| 6 | 300k – 349,999 | 0.0015625 UST | 78.125 UST | **9,921.875 UST** |
| 7+ | 350,000+ | 0.001 UST | tail emission | — |

After era 6 the reward floors at **0.001 UST** (tail emission for ongoing gas security).  
With 2% burn applied, net circulating supply from eras 0–6 is **≈ 9,722 UST**.

Mining contract (USSTMine v4): `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0`

---

## Quick Start — 8 Steps

| Step | Action |
|------|--------|
| **1** | Create an Ethereum-compatible wallet (MetaMask, or generate with `python -c "from eth_account import Account; a=Account.create(); print(a.address, a.key.hex())"`) |
| **2** | Add the UST network to MetaMask: [one click via Chainlist](https://chainlist.org/chain/778889) or manually with Chain ID `778889`, RPC `https://147-45-143-23.sslip.io/rpc` |
| **3** | Get free gas: open the [Faucet](https://147-45-143-23.sslip.io/faucet) and request **0.01 UST** (enough for ~200 transactions) |
| **4** | Clone the repository: `git clone https://github.com/klaren1987/UST-chain.git && cd?? UST-chain` |
| **5** | Install dependencies: `pip install -r requirements.txt` |
| **6** | Configure the miner: `cp .env.miner.example .env.miner` then set `USST_MINER_KEY=0xYOUR_PRIVATE_KEY` |
| **7** | Start mining: `python miner/usst_miner.py` (or `docker compose -f docker-compose.miner.yml up -d`) |
| **8** | Monitor: watch the terminal for `Mined!` events; check your balance in the [Explorer](https://blockscout.byteboost.ru) |

---

## Mining — Earn UST

Anyone with a wallet can mine. No registration, no KYC.

> **First time?** Your wallet starts with 0 UST and can't pay gas for the first transaction.  
> Use the **[Faucet](https://147-45-143-23.sslip.io/faucet)** to receive 0.01 UST instantly (enough for ~200 transactions).

The full step-by-step guide is in the [Quick Start — 8 Steps](#quick-start--8-steps) section above.

**GPU mining** (NVIDIA CUDA): ~590 MH/s on RTX 4060  
**CPU mining**: works on any machine, no GPU required

### Docker

```bash
cp .env.miner.example .env
# Edit .env — set USST_MINER_KEY
docker compose -f docker-compose.miner.yml up --build -d
```

### Mining Algorithm

```
hash = keccak256(abi.encodePacked(miner_address, nonce, work_block))
valid  if  uint256(hash) < type(uint256).max / difficulty
reward =   poolBalance >= reward()  →  transfer minerReward() to miner
           2% of reward()           →  transfer to 0x…dEaD (burn)
```

Source: [`contracts/USSTMine.sol`](contracts/USSTMine.sol)

---

## DEX — Swap UST ↔ USDT

Uniswap V2 fork deployed on chain 778889. **[Open DEX →](https://147-45-143-23.sslip.io/dex)**

| Contract | Address |
|----------|---------|
| UniswapV2Factory | `0xbFAe9F1DF838F63eBedB29f54C7c9FA25c16fe06` |
| UniswapV2Router02 | `0xaD30634417751B8088a5ca3F812d74c3c2331e85` |
| WUST (Wrapped UST) | `0x63787dE7FEb0beB1b545eB564794b5bCEEB317CF` |
| USDT (18 decimals) | `0x3deAa90462B76F9135340820cC3024602ef7D090` |
| UST/USDT Pair | `0x0Af0858e199C85E1f56f11bAb229084b6CA09338` |

Init code hash: `0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f`

LP tokens are burned to `0x000…dEaD` — the pool cannot be rug-pulled.

---

## Add to MetaMask

**One click:** [Add via Chainlist](https://chainlist.org/chain/778889)

**Manual setup:**

| Field | Value |
|-------|-------|
| Network Name | UST Network |
| RPC URL | `https://147-45-143-23.sslip.io/rpc` |
| Chain ID | `778889` |
| Currency Symbol | `UST` |
| Block Explorer | `https://blockscout.byteboost.ru` |

Auto-discoverable in **MetaMask**, **WalletConnect**, **Rainbow**, **wagmi**, **chainid.network**

---

## Security

| Feature | Implementation |
|---------|----------------|
| No pre-mine | Pool funded by deployer at launch — every UST comes from `mine()` |
| Reentrancy guard | `nonReentrant` on `mine()` — pool drain via reentrant contract is impossible |
| 48 h timelock | Difficulty and ownership changes require a 48-hour on-chain queue |
| 7-day withdrawal timelock | Pool withdrawal queued 7 days in advance — publicly visible on-chain |
| `MIN_DIFFICULTY = 100,000` | Difficulty can never be lowered to trivially easy levels |
| Typed admin operations | No raw `executeOp(callData)` — all actions are explicit named functions |
| Mutable owner | Contract ownership can be transferred to a multisig or governance contract |
| Burn address | `0x000000000000000000000000000000000000dEaD` — unrecoverable by construction |
| Locked liquidity | LP tokens burned at pair creation — pool cannot be rug-pulled |
| RPC filter | Public RPC blocks `eth_sendTransaction`, `eth_sign`, and all `admin_*` methods |
| Double-spend guard | Each `(miner, nonce, block)` solution can only be submitted once |
| Bridge rate limiting | Min 1 USDT / max 10,000 USDT per deposit; 5 deposits/address/hour |
| Pool watchdog | Auto-refills mining pool via on-chain `FundAdded` events — no silent manual top-ups |
| Trustless escrow (roadmap) | `EscrowUSDT.sol` written — replaces operator EOA with on-chain multisig escrow |

Full audit report and disclosure policy: [SECURITY.md](SECURITY.md)

---

## Registry Status

| Registry | Status | Link |
|----------|--------|------|
| ethereum-lists/chains | ✅ Merged | [PR #8418](https://github.com/ethereum-lists/chains/pull/8418) |
| DefiLlama Chainlist | ✅ Merged | [PR #2830](https://github.com/DefiLlama/chainlist/pull/2830) |
| wevm/viem | ⏳ Pending | [PR #4734](https://github.com/wevm/viem/pull/4734) |
| blockscout/chainscout | ⏳ Pending | [PR #242](https://github.com/blockscout/chainscout/pull/242) |
| GeckoTerminal / CoinGecko | ⏳ Submitted | Network + DEX listing |

---

## Repository Structure

```
.
├── contracts/
│   ├── USSTMine.sol        PoW mining contract (v4, audited)
│   └── EscrowUSDT.sol      Trustless Ethereum-side bridge escrow (roadmap)
├── miner/                  Python miner client (GPU + CPU engines)
├── config/
│   ├── explorer/           Block explorer + DEX + Faucet (static SPA)
│   └── wireguard/          WireGuard VPN config examples
├── chain/                  genesis.json and chain setup docs
├── docs/                   Whitepaper, announcements, listing docs
├── scripts/
│   ├── pool-watchdog.py    Auto-refills mining pool, emits on-chain FundAdded events
│   ├── bridge-relayer.py   Bridge operator (v2: rate limit, audit log, replay guard)
│   └── ...                 Deploy, migrate, test scripts
├── docker-compose.blockscout.yml  Self-hosted Blockscout explorer deployment
├── SECURITY.md             Security policy, audit report, disclosure
├── NODES.md                Running a validator / full node
└── .env.miner.example      Miner configuration template
```

---

## Documentation

- [Whitepaper](docs/whitepaper.md) — full technical specification, architecture decisions
- [Security Policy](SECURITY.md) — audit report, v4 fixes, disclosure
- [Node & Validator Guide](NODES.md) — run a full node or become a signer
- [Changelog](CHANGELOG.md) — version history v1.0 → v4.0
- [Contributing](CONTRIBUTING.md) — how to contribute
- [Announcements](docs/announcements.md) — community post templates

---

## License

MIT
