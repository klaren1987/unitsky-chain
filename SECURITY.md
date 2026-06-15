# Security Policy

## Scope

This document covers the security posture of the UST Network network, including the mining contract, bridge relayer, RPC infrastructure, and supporting code.

---

## Smart Contract Audit — USSTMine v4

**Audit performed:** June 2026  
**Contract:** [`contracts/USSTMine.sol`](contracts/USSTMine.sol)  
**Deployed at:** `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0` (Chain 778889)

### Findings and Resolutions

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| CRIT-1 | Critical | Reentrancy in `mine()` — pool drain via reentrant contract | **Fixed in v4** |
| CRIT-2 | Critical | `withdrawOwner()` without timelock — instant rug vector | **Fixed in v4** |
| HIGH-1 | High | `difficulty` settable to 1 — trivial proof grinding | **Fixed in v4** |
| HIGH-2 | High | `executeOp(callData)` — arbitrary call from contract | **Fixed in v4** |
| MED-1  | Medium | Front-running between miners (PoA block ordering) | Accepted — by design on PoA |
| MED-2  | Medium | Pool exhaustion reverts miner tx (gas loss) | Mitigated — pool watchdog + pool monitor |
| MED-3  | Medium | `queueOp` re-queue resets timelock | **Fixed in v4** — typed cancel functions |
| LOW-1  | Info | `abi.encodePacked` collision | Not an issue — fixed-size types, no collision |
| LOW-2  | Info | `workBlock` stale window (10 blocks) | Accepted — miner uses 8-block max age |

### v4 Implementation Details

**CRIT-1 — Reentrancy guard:**
```solidity
uint256 private _status;
modifier nonReentrant() {
    if (_status == _ENTERED) revert Reentrancy();
    _status = _ENTERED;
    _;
    _status = _NOT_ENTERED;
}
function mine(uint256 nonce, uint256 workBlock) external nonReentrant { ... }
```
Any reentrant call to `mine()` inside a `receive()` hook reverts immediately.

**CRIT-2 — Withdrawal timelock:**  
`withdrawOwner()` is removed. Replaced by `queueWithdraw(amount)` + `executeWithdraw()` with a **7-day** enforced delay. Every withdrawal is visible on-chain 7 days in advance — miners can verify the queue at any time.

**HIGH-1 — Minimum difficulty:**
```solidity
uint256 public constant MIN_DIFFICULTY = 100_000;
function queueDifficulty(uint256 newDifficulty) external onlyOwner {
    if (newDifficulty < MIN_DIFFICULTY) revert DifficultyTooLow();
    ...
}
```

**HIGH-2 — Typed operations:**  
`executeOp(bytes calldata)` is removed entirely. Admin actions are now explicit typed functions (`queueDifficulty`, `executeDifficulty`, `queueOwnershipTransfer`, `queueWithdraw`) — no raw calldata execution is possible.

---

## What v4 Guarantees

| Property | Guarantee |
|---|---|
| Mine once per proof | `_usedWork[keccak256(miner, nonce, block)]` mapping |
| Proof bound to sender | `keccak256(abi.encodePacked(msg.sender, nonce, workBlock))` |
| No reentrancy | `nonReentrant` on `mine()` |
| No instant withdrawal | 7-day timelock queue for all pool withdrawals |
| Difficulty floor | `MIN_DIFFICULTY = 100,000` — can never be trivially low |
| All admin changes announced | 48h timelock for difficulty/ownership |
| Transparent math | Halving + burn computed deterministically in Solidity 0.8 (overflow-safe) |

---

## Infrastructure Security

### RPC Filter

The public RPC endpoint (`/rpc`) is protected by [`scripts/rpc-filter.py`](scripts/rpc-filter.py):

- `eth_sendTransaction` — **blocked** (users sign locally)
- `eth_sign`, `eth_signTypedData` — **blocked**
- `personal_*`, `admin_*`, `miner_*`, `debug_*`, `txpool_*` — **blocked**
- All read methods (`eth_call`, `eth_getLogs`, `eth_getBalance`, etc.) — **allowed**

### HTTPS / TLS

All public endpoints are served over HTTPS via [Caddy](https://caddyserver.com/) with automatic Let's Encrypt certificates.

Security headers enforced on all responses:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Content-Security-Policy: default-src 'self' https: data:; script-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Bridge Relayer

The cross-chain USDT bridge operates with the following safeguards:
- Every processed Ethereum transaction hash is recorded on-chain (`bridgeMint` stores `ethTxHash`)
- The relayer maintains a local processed-tx cache to prevent duplicate processing
- Minimum deposit: 1.0 USDT; Maximum single deposit: 10,000 USDT
- Per-address rate limit: 5 deposits per hour
- All bridge operations are logged with timestamps and transaction hashes

---

## Network Consensus Security

The network uses **Clique Proof-of-Authority** consensus (EIP-225). Key properties:

- Block signers are pre-approved Ethereum addresses
- Each signer may sign at most 1 block per `(N/2 + 1)` turn period, where N = signer count
- Adding/removing signers requires approval from `(N/2 + 1)` existing signers — no unilateral changes
- The current signer set is transparent and queryable via `clique_getSigners` on the RPC

Signer transparency: run `curl -s -X POST https://147-45-143-23.sslip.io/rpc -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"clique_getSigners","params":["latest"],"id":1}'`

---

## Responsible Disclosure

If you discover a vulnerability in the smart contract, bridge, or infrastructure:

1. **Do not** open a public GitHub issue for security-sensitive findings
2. Email a description to the repository owner via GitHub private message
3. Include: affected component, severity estimate, reproduction steps, suggested fix
4. We commit to acknowledging reports within 48 hours and resolving critical issues within 7 days

We do not operate a formal bug bounty program, but significant findings will be credited in this document.

---

## Known Limitations

| Limitation | Notes |
|---|---|
| Clique PoA single signer | Current deployment uses one authorized signer. Adding more signers follows the Clique protocol (existing signers vote). |
| Centralized bridge | The USDT bridge is operated by the deployer address. Users must trust the operator. A trustless bridge requires a separate audited escrow contract on Ethereum mainnet. |
| Pool funding | The mining pool is funded by the network operator. An empty pool means `mine()` reverts (miners lose gas). The pool watchdog monitors and refills automatically. |
| No formal audit | The v4 security review was conducted internally. A third-party audit is on the roadmap. |

---

*Last updated: June 2026*
