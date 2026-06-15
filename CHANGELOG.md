# Changelog

All notable changes to the UST Network network are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

## [4.0.0] — 2026-06-15 — Security Hardening

### Breaking Changes
- `USSTMine` contract redeployed as v4 at `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0`
- Old v3 address `0xB650a7B39a447A266b927d6e0908AC6d0091FC67` is retired; pool migrated
- `executeOp(bytes calldata)` removed — callers must use typed operation functions

### Security
- **[CRITICAL]** Added `nonReentrant` guard to `mine()` — reentrancy pool drain is impossible
- **[CRITICAL]** `withdrawOwner()` replaced with `queueWithdraw()` + `executeWithdraw()` enforcing 7-day timelock
- **[HIGH]** Added `MIN_DIFFICULTY = 100,000` constant — difficulty can never be trivially low
- **[HIGH]** Removed raw `executeOp(callData)` — replaced with typed `queueDifficulty`, `queueOwnershipTransfer`, `queueWithdraw`
- **[MEDIUM]** Added explicit `cancelDifficulty()`, `cancelWithdraw()`, `cancelOwnershipTransfer()` — queue state is fully transparent

### Added
- `contracts/EscrowUSDT.sol` — Ethereum-side trustless bridge escrow (m-of-n signers, replay protection, timelocked governance)
- `scripts/pool-watchdog.py` — automated pool refill service with on-chain `FundAdded` events
- `scripts/bridge-relayer.py` v2 — rate limiting, processed-tx cache, pre-flight treasury check, audit log
- `SECURITY.md` — full audit findings table, responsible disclosure policy
- `NODES.md` — full-node and validator setup guide
- Pool watchdog added as Docker service in `docker-compose.public.yml`
- Explorer home page: live validator (signer) set via `clique_getSigners`

### Changed
- Migration: v3 pool (17,664 UST) transferred to v4 with `initialTotalMined=11,078` (era preserved)
- `WITHDRAW_TIMELOCK = 7 days` (vs no timelock in v3)
- All admin events added: `DifficultyQueued`, `WithdrawalQueued`, `Withdrawn`, `OwnershipQueued`

### Migration Guide (v3 → v4)
```
1. python scripts/migrate_to_v4.py --dry-run    # inspect state
2. python scripts/migrate_to_v4.py              # deploy + migrate pool
3. Update USST_CONTRACT_ADDRESS in .env
4. docker compose restart miner rpc-filter
```

---

## [3.0.0] — 2026-06-10 — Bridge & DEX

### Added
- Uniswap V2 fork deployed on chain 778889 (UST/USDT pair, LP tokens burned)
- `contracts/BridgedUSDT.sol` — 6-decimal ERC-20 bridged USDT on Chain 778889
- `scripts/bridge-relayer.py` — cross-chain USDT bridge relayer (ETH ↔ Chain 778889)
- `/bridge` UI page — deposit/withdraw USDT between Ethereum and Chain 778889
- `/dex` UI page — swap UST ↔ USDT via Uniswap V2
- `scripts/deploy.py` — automated deployment of all contracts
- `CONTRIBUTING.md` — contribution guidelines

### Changed
- Mining contract upgraded to v3: added halving, 2% burn, 48-hour timelock governance
- RPC filter extended: `/bridge/status`, `/faucet/status` API endpoints
- Public RPC moved to HTTPS via Caddy + Let's Encrypt

### Security
- 48-hour timelock added to `_setDifficulty` and `_transferOwnership`
- RPC filter blocks all `admin_*`, `personal_*`, `debug_*`, `miner_*`, `txpool_*` methods
- CORS headers added for GeckoTerminal compatibility

---

## [2.0.0] — 2026-06-08 — Public Launch

### Added
- Public HTTPS RPC: `https://147-45-143-23.sslip.io/rpc`
- Block explorer SPA (`config/explorer/index.html`)
- Faucet: 0.01 UST per address per 24 hours
- GPU miner (NVIDIA CUDA) via Numba — ~590 MH/s on RTX 4060
- `docker-compose.public.yml` — public infrastructure (Caddy + rpc-filter)
- `docker-compose.miner.yml` — containerized miner
- `docker-compose.windows-node.yml` — Windows node setup
- WireGuard VPN config examples for multi-node peering
- GitHub Actions RPC health check workflow
- Chain registered in `ethereum-lists/chains` (PR #8418, merged)
- Chain registered in `DefiLlama/chainlist` (PR #2830, merged)
- MetaMask one-click add via Chainlist

### Changed
- Mining contract v2: anti-double-spend via `_usedWork[keccak256(miner, nonce, block)]`
- Miner improved: stale-proof protection, Rich terminal UI, automatic retry

---

## [1.0.0] — 2026-06-01 — Genesis

### Added
- Chain 778889 genesis block (Clique PoA, 5-second blocks, 30M gas limit)
- `USSTMine.sol` v1 — proof-of-work mining contract
  - keccak256 PoW: `hash(miner, nonce, workBlock) < 2^256 / difficulty`
  - 0.1 UST reward per valid proof (era 0)
  - Pool funded by deployer at deployment
- `miner/usst_miner.py` — Python CPU/GPU miner client
- `docker-compose.yml` + `docker-compose.node.yml` — local node stack
- `chain/genesis.json` — genesis configuration
- `docs/whitepaper.md` — v1.0 technical specification
- `README.md` — project overview and quick start

---

## Versioning Policy

| Component | Versioning |
|---|---|
| Network protocol | Major version bump for consensus changes |
| Mining contract | Redeployment = major version bump; migration guide provided |
| Miner client | Semver on `miner/` directory |
| Infrastructure | Docker image rebuild on config changes |

Contract addresses by version:

| Version | Address | Status |
|---|---|---|
| USSTMine v4 | `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0` | **Active** |
| USSTMine v3 | `0xB650a7B39a447A266b927d6e0908AC6d0091FC67` | Retired — pool drained |
