# Announcement Templates — UST Network

Ready-to-post templates for promoting the UST network.
Replace `[YOUR_WALLET]` with your actual wallet address before posting.

---

## Reddit — r/ethdev / r/CryptoCurrency / r/altcoin

**Title:** `[ANN] UST Network — EVM chain, Chain ID 778889, PoW mining smart contract, free UST tokens`

**Post:**

```
I launched an independent EVM-compatible blockchain called **UST Network** (UST).

**What makes it interesting:**
- Fully EVM-compatible (Geth, Clique PoA)
- UST tokens are distributed *only* through a Proof-of-Work smart contract — no pre-mine, no ICO
- Bitcoin-style halving every 50,000 proofs + 2% burn per reward
- Public HTTPS RPC + custom block explorer + Uniswap V2 DEX (UST/USDT pair live)
- GPU mining supported (NVIDIA CUDA, ~590 MH/s on RTX 4060)
- Free faucet — get 0.01 UST to start mining instantly
- Open-source

**Network Details:**
- Chain ID: `778889`
- RPC: `https://147-45-143-23.sslip.io/rpc`
- Explorer: `https://147-45-143-23.sslip.io`
- DEX: `https://147-45-143-23.sslip.io/dex`
- Faucet: `https://147-45-143-23.sslip.io/faucet`

**Mining reward:** 0.1 UST per proof (era 0), halving every 50,000 proofs
**Algorithm:** keccak256(miner_address, nonce, work_block)

**Add to MetaMask:**
- Network Name: UST Network
- RPC URL: https://147-45-143-23.sslip.io/rpc
- Chain ID: 778889
- Symbol: UST
- Explorer: https://147-45-143-23.sslip.io

**Mining (free UST):**
```bash
git clone https://github.com/klaren1987/UST-chain.git
cd?? UST-chain
pip install -r requirements.txt
cp .env.miner.example .env.miner
# Set USST_MINER_KEY in .env.miner
python miner/usst_miner.py
```

**Registry status:**
- ✅ ethereum-lists/chains — Merged PR #8418
- ✅ DefiLlama Chainlist — Merged PR #2830
- ⏳ wevm/viem — PR #4721 pending

GitHub: https://github.com/klaren1987/UST-chain
Whitepaper: https://github.com/klaren1987/UST-chain/blob/main/docs/whitepaper.md

Happy to answer questions!
```

---

## BitcoinTalk — Announcements (Altcoins)

**Subject:** `[ANN] UST Network (UST) — EVM Chain 778889 | PoW Smart Contract Mining | Halving + Burn | HTTPS RPC | Open Source`

**Post:**

```
████████████████████████████████████████████
███  UST Network (UST)  ███
████████████████████████████████████████████

An independent EVM-compatible blockchain with Proof-of-Work token distribution.

══════════════════════════════════════════
NETWORK SPECIFICATIONS
══════════════════════════════════════════
Chain ID    : 778889 (0xBE289)
Symbol      : UST
Decimals    : 18
Consensus   : Clique PoA (Geth)
Block time  : ~5 seconds
Mining      : PoW smart contract (keccak256)

══════════════════════════════════════════
PUBLIC ENDPOINTS
══════════════════════════════════════════
HTTPS RPC   : https://147-45-143-23.sslip.io/rpc
WebSocket   : wss://147-45-143-23.sslip.io/ws
Explorer    : https://147-45-143-23.sslip.io
DEX         : https://147-45-143-23.sslip.io/dex
Faucet      : https://147-45-143-23.sslip.io/faucet

══════════════════════════════════════════
TOKEN ECONOMICS
══════════════════════════════════════════
- No pre-mine, no ICO, no team allocation
- 100% of UST is earned through mining
- Era-0 reward: 0.1 UST per proof (net 0.098 after 2% burn)
- Halving: every 50,000 proofs (Bitcoin-style)
- Burn: 2% per reward → 0x000...dEaD (permanent)
- Max supply eras 0-6: ~9,922 UST gross / ~9,722 net
- Algorithm: keccak256(miner_address, nonce, work_block)
- GPU support: NVIDIA CUDA (~590 MH/s RTX 4060)
- CPU mining: available for any machine

══════════════════════════════════════════
HOW TO MINE
══════════════════════════════════════════
git clone https://github.com/klaren1987/UST-chain.git
cd?? UST-chain
pip install -r requirements.txt
cp .env.miner.example .env.miner
# Edit .env.miner: set USST_MINER_KEY to your private key
python miner/usst_miner.py

First time? Get free gas at: https://147-45-143-23.sslip.io/faucet

══════════════════════════════════════════
ADD TO METAMASK
══════════════════════════════════════════
Network Name : UST Network
RPC URL      : https://147-45-143-23.sslip.io/rpc
Chain ID     : 778889
Symbol       : UST
Explorer     : https://147-45-143-23.sslip.io

One-click add: https://chainlist.org/chain/778889

══════════════════════════════════════════
LINKS
══════════════════════════════════════════
GitHub     : https://github.com/klaren1987/UST-chain
Whitepaper : https://github.com/klaren1987/UST-chain/blob/main/docs/whitepaper.md
Explorer   : https://147-45-143-23.sslip.io

Registry status:
• ✅ ethereum-lists/chains — Merged PR #8418
• ✅ DefiLlama Chainlist — Merged PR #2830
• ⏳ wevm/viem — PR #4721 pending

══════════════════════════════════════════
ROADMAP
══════════════════════════════════════════
[✓] Mainnet launch
[✓] Public HTTPS RPC + explorer
[✓] GPU miner (CUDA)
[✓] Open-source repository
[✓] Chain registry submissions (ethereum-lists, DefiLlama)
[✓] Uniswap V2 DEX live (UST/USDT pair)
[✓] USDT bridge deployed
[ ] GeckoTerminal / CoinGecko listing (submitted)
[ ] Additional liquidity

Questions welcome!
```

---

## Twitter / X Thread

**Tweet 1 (main):**
```
🚀 UST Network (UST) — independent EVM chain, live mainnet.

⛓️ Chain ID: 778889
💎 Native token: UST
⛏️ Mining: PoW smart contract (no pre-mine, no ICO!)
🔗 RPC: https://147-45-143-23.sslip.io/rpc

Thread 👇
```

**Tweet 2:**
```
UST tokens can only be earned by mining.

No ICO. No pre-mine. No team allocation.
100% fair distribution through keccak256 PoW.

Era-0 reward: 0.1 UST per proof
Halving every 50,000 proofs (Bitcoin-style)
2% burn per reward → permanent deflation 🔥

GPU: ~590 MH/s on RTX 4060 🖥️
CPU: works on any machine 💻

github.com/klaren1987/UST-chain
```

**Tweet 3:**
```
Add UST to MetaMask in 30 seconds:

Network: UST Network
RPC: https://147-45-143-23.sslip.io/rpc
Chain ID: 778889
Symbol: UST

Or one-click: chainlist.org/chain/778889 🦊

Explorer: https://147-45-143-23.sslip.io 🔍
DEX (swap UST↔USDT): https://147-45-143-23.sslip.io/dex
```

**Tweet 4:**
```
Registry status for UST (Chain 778889):

✅ ethereum-lists/chains — Merged
✅ DefiLlama Chainlist — Merged
⏳ wevm/viem — PR pending

Once viem merges → auto-discoverable in MetaMask, WalletConnect, Rainbow, wagmi 🌈
```

**Tweet 5:**
```
Want to mine UST? 5 commands:

git clone github.com/klaren1987/UST-chain
pip install -r requirements.txt
cp .env.miner.example .env.miner
# set USST_MINER_KEY
python miner/usst_miner.py

New? Get free gas first: 147-45-143-23.sslip.io/faucet 💧
```

---

## Telegram Message (groups/channels)

```
🔗 *UST Network (UST)* — independent EVM blockchain, live mainnet!

⛓ Chain ID: 778889
💎 Token: UST (18 decimals)
⛏ Mining: PoW smart contract — 0.1 UST/proof, halving every 50k proofs, 2% burn
🌐 RPC: https://147-45-143-23.sslip.io/rpc
🔍 Explorer: https://147-45-143-23.sslip.io
⇄ DEX (UST/USDT): https://147-45-143-23.sslip.io/dex
💧 Faucet (free gas): https://147-45-143-23.sslip.io/faucet

Add to MetaMask (one click): https://chainlist.org/chain/778889

Mining (free UST):
`git clone https://github.com/klaren1987/UST-chain && pip install -r requirements.txt && python miner/usst_miner.py`

GitHub: https://github.com/klaren1987/UST-chain
Whitepaper: https://github.com/klaren1987/UST-chain/blob/main/docs/whitepaper.md
```

---

## Discord Message

```
**🚀 UST Network (UST) — Chain Launch**

An independent EVM-compatible mainnet is live!

**Network**
• Chain ID: `778889`
• RPC: `https://147-45-143-23.sslip.io/rpc`
• Explorer: `https://147-45-143-23.sslip.io`
• DEX: `https://147-45-143-23.sslip.io/dex`
• Faucet: `https://147-45-143-23.sslip.io/faucet`
• Token: `UST`

**Fair Launch**
No ICO, no pre-mine. UST tokens are earned exclusively through PoW mining.
Era-0 reward: 0.1 UST/proof · Halving every 50,000 proofs · 2% burn per reward

**Mining**
```bash
git clone https://github.com/klaren1987/UST-chain
pip install -r requirements.txt
cp .env.miner.example .env.miner
python miner/usst_miner.py
```
GPU: ~590 MH/s on RTX 4060  |  CPU: any machine

**Registry**
✅ ethereum-lists/chains — Merged  |  ✅ DefiLlama Chainlist — Merged  |  ⏳ wevm/viem pending

**Links**
• GitHub: <https://github.com/klaren1987/UST-chain>
• Whitepaper: <https://github.com/klaren1987/UST-chain/blob/main/docs/whitepaper.md>
• Chainlist: <https://chainlist.org/chain/778889>
```

---

## Suggested Communities to Post In

### Reddit
- r/ethdev — for developers/technical audience
- r/CryptoCurrency — general crypto audience
- r/altcoin — altcoin announcements
- r/gpumining — for miners
- r/EtherMining — Ethereum/EVM miners

### BitcoinTalk
- https://bitcointalk.org/index.php?board=67.0 — Altcoin Announcements

### Discord Servers
- Ethereum Community Discord
- DeFi communities
- GPU mining Discord servers
- EVM developers Discord

### Telegram Groups
- Ethereum discussions groups
- Crypto ANN groups
- GPU mining groups

### Other
- DEV.to — write a technical article
- Medium — publish the whitepaper
- Hackernews (news.ycombinator.com) — "Show HN:" post
