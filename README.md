# Unitsky String Technologies

**EVM-compatible blockchain · Chain ID 778889 · Native token UST**

[![Chain ID](https://img.shields.io/badge/Chain%20ID-778889-blue)](https://chainlist.org)
[![RPC](https://img.shields.io/badge/RPC-HTTPS-green)](https://147-45-143-23.sslip.io/rpc)
[![Explorer](https://img.shields.io/badge/Explorer-online-brightgreen)](https://147-45-143-23.sslip.io)
[![CI](https://github.com/klaren1987/unitsky-chain/actions/workflows/rpc-health.yml/badge.svg)](https://github.com/klaren1987/unitsky-chain/actions/workflows/rpc-health.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Network

| Parameter | Value |
|-----------|-------|
| **Chain ID** | `778889` (`0xBE289`) |
| **Native Token** | **UST** |
| **Block Time** | ~5 seconds |
| **Consensus** | Clique PoA |
| **Mining** | PoW smart contract |
| **HTTPS RPC** | https://147-45-143-23.sslip.io/rpc |
| **WebSocket** | wss://147-45-143-23.sslip.io/ws |
| **Explorer** | https://147-45-143-23.sslip.io |

---

## Add to MetaMask

**One click:** [Add via Chainlist](https://chainlist.org/?search=778889) *(after PR #2830 merges)*

**Manual:**

| Field | Value |
|-------|-------|
| Network Name | `Unitsky String Technologies` |
| RPC URL | `https://147-45-143-23.sslip.io/rpc` |
| Chain ID | `778889` |
| Currency Symbol | `UST` |
| Block Explorer | `https://147-45-143-23.sslip.io` |

---

## Mining (earn free UST)

UST tokens are distributed **only** through mining — no pre-mine, no ICO, no team allocation.

```bash
git clone https://github.com/klaren1987/unitsky-chain.git
cd unitsky-chain
pip install -r requirements.txt
cp .env.miner.example .env.miner
# Edit .env.miner: set MINER_ADDRESS to your wallet
python miner/usst_miner.py
```

**GPU mining** (NVIDIA CUDA): ~686 MH/s on RTX 4060  
**CPU mining**: works on any machine

Mining algorithm: `keccak256(miner_address, nonce, work_block)`  
Contract: [`contracts/USSTMine.sol`](contracts/USSTMine.sol)

---

## Registry Status

| Registry | Status | Link |
|----------|--------|------|
| ethereum-lists/chains | ⏳ Pending merge | [PR #8418](https://github.com/ethereum-lists/chains/pull/8418) |
| DefiLlama Chainlist | ⏳ Pending merge | [PR #2830](https://github.com/DefiLlama/chainlist/pull/2830) |
| wevm/viem | ⏳ Pending merge | [PR #4721](https://github.com/wevm/viem/pull/4721) |

Once merged: auto-discoverable in **MetaMask**, **WalletConnect**, **Rainbow**, **wagmi**, **chainid.network**

---

## Repository Structure

```
.
├── chain/              Genesis block configuration
├── config/
│   ├── caddy/          Caddyfile (HTTPS reverse proxy)
│   ├── explorer/       Custom block explorer (static SPA)
│   └── wireguard/      WireGuard VPN config examples
├── contracts/          USSTMine.sol — PoW mining contract
├── docs/
│   ├── whitepaper.md   Full technical documentation
│   └── announcements.md  Community post templates
├── miner/              Python miner (GPU + CPU)
├── scripts/            Setup and maintenance scripts
├── docker-compose*.yml Container orchestration
└── .env.miner.example  Miner configuration template
```

---

## Infrastructure

The network runs on a self-hosted Windows machine behind a VPS gateway:

```
Internet → VPS (147.45.143.23)
         → WireGuard tunnel
         → Windows Docker host
         → Geth node + Caddy HTTPS proxy
```

**VPS repair:** If the WireGuard tunnel goes down, run [`scripts/fix-vps-wireguard.sh`](scripts/fix-vps-wireguard.sh) on the VPS.

---

## Documentation

- [Whitepaper](docs/whitepaper.md) — full technical docs
- [Announcements](docs/announcements.md) — ready-to-post community templates
- [Contributing](CONTRIBUTING.md) — how to contribute

---

## Roadmap

- [x] Mainnet launch
- [x] Public HTTPS RPC + block explorer
- [x] GPU miner (NVIDIA CUDA ~686 MH/s)
- [x] Open-source repository
- [x] Chain registry submissions (ethereum-lists, Chainlist, viem)
- [x] GitHub CI health checks
- [ ] DEX listing (Uniswap v2 fork on-chain)
- [ ] Bridge to Ethereum mainnet
- [ ] CoinGecko / CoinMarketCap listing

---

## License

[MIT](LICENSE)
