# UST Listing — GeckoTerminal / CoinGecko

## Strategy

1. **GeckoTerminal** — submit an EVM DEX/Chain listing request (free).  
   Once approved, GeckoTerminal automatically triggers a CoinGecko listing.
2. **CoinGecko Preview Listing** — can be submitted in parallel, but requires active trading.

---

## Submission Steps

### 1. GeckoTerminal — EVM DEX/Chain Listing

**Form:** https://about.geckoterminal.com/dex-chain-listing  
*(Click "Fill Out Form" → DEX Addition)*

#### Form data:

| Field | Value |
|-------|-------|
| Your name / contact | (your name / email) |
| Chain name | UST Network |
| Chain ID | 778889 |
| RPC URL (public) | `https://147-45-143-23.sslip.io/rpc` |
| Block explorer | `https://147-45-143-23.sslip.io` |
| Native currency symbol | UST |
| Native currency decimals | 18 |
| DEX name | UST DEX |
| DEX type / fork | **Uniswap V2** |
| Factory contract | `0xbFAe9F1DF838F63eBedB29f54C7c9FA25c16fe06` |
| Router contract | `0xaD30634417751B8088a5ca3F812d74c3c2331e85` |
| Init code hash | `0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f` |
| Website | `https://klaren1987.github.io/UST-chain/` |
| Telegram / Twitter | (your social links, if available) |
| Listing type | Regular (free) or Express ($500, within 7 days) |

#### Project description (for the form):

```
UST Network (UST) is an EVM-compatible Proof-of-Work blockchain
(Chain ID 778889) running the native token UST. The chain features a
smart-contract-based mining system (USSTMine v3) with Bitcoin-style halving
every 50,000 proofs, Ethereum-style 2% burn per reward, and a 48-hour timelock
on admin functions. DEX: Uniswap V2 fork with permanently locked liquidity
(LP tokens burned to 0xdead). Fully open-source.

GitHub: https://github.com/klaren1987/UST-chain
DEX: https://147-45-143-23.sslip.io/dex
RPC: https://147-45-143-23.sslip.io/rpc
Explorer: https://147-45-143-23.sslip.io
```

---

### 2. CoinGecko — New Coin Listing (after GeckoTerminal approval)

**Form:** https://partner.coingecko.com/request-form/new

| Field | Value |
|-------|-------|
| Request type | New Coin/Token Listing → Active Listing |
| Coin name | UST |
| Ticker symbol | UST |
| Coin type | Native coin (layer-1) |
| Chain | UST Network (778889) |
| Website | `https://klaren1987.github.io/UST-chain/` |
| Block explorer | `https://147-45-143-23.sslip.io` |
| GitHub | `https://github.com/klaren1987/UST-chain` |
| Logo | `/config/caddy/static/icon.svg` (convert to 200×200 PNG) |
| Description | Open-source EVM PoW chain with halving, burn mechanism and locked DEX liquidity |
| Markets | UST DEX (GeckoTerminal listing URL after approval) |

**After submitting:** publish a tweet/post confirming submission and reply to it with the Request ID.

---

## Current DEX Contracts

| Contract | Address |
|----------|---------|
| WUST (Wrapped UST) | `0x63787dE7FEb0beB1b545eB564794b5bCEEB317CF` |
| FixedUSDT (18 decimals) | `0x3deAa90462B76F9135340820cC3024602ef7D090` |
| UniswapV2Factory | `0xbFAe9F1DF838F63eBedB29f54C7c9FA25c16fe06` |
| UniswapV2Router02 | `0xaD30634417751B8088a5ca3F812d74c3c2331e85` |
| UST/USDT Pair (current) | `0x0Af0858e199C85E1f56f11bAb229084b6CA09338` |
| USSTMine v3 | `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0` |

Current liquidity: **3,500 WUST + 350 USDT** (~$35 TVL at 1 UST = $0.10)  
LP tokens: **burned** → `0x000000000000000000000000000000000000dEaD` ✅

---

## Init Code Hash (verified)

Required by GeckoTerminal to compute pair addresses. This is the standard Uniswap V2 hash:

```
0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f
```

**Verification:**
```
factory = 0xbFAe9F1DF838F63eBedB29f54C7c9FA25c16fe06
token0  = 0x3deAa90462B76F9135340820cC3024602ef7D090  (FixedUSDT18 — sorted lower)
token1  = 0x63787dE7FEb0beB1b545eB564794b5bCEEB317CF  (WUST)
salt    = keccak256(abi.encodePacked(token0, token1))
pair    = CREATE2(factory, salt, initHash) = 0x0Af0858e...  ✅ match
```

> **Note:** `abi.encodePacked(address, address)` = 40 bytes (20+20),  
> NOT 64 bytes (with 32-byte padding).
