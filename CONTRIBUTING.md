# Contributing to UST Network

Thank you for your interest in contributing. UST is an open-source project and welcomes pull requests, bug reports, and feedback.

---

## Ways to Contribute

### Run a Node
Run a full node to strengthen the network:

```bash
git clone https://github.com/klaren1987/UST-chain.git
cd?? UST-chain
docker compose -f docker-compose.node.yml up -d
```

### Mine UST
Mine UST to distribute tokens and contribute hashrate:

```bash
cp .env.miner.example .env.miner
# Edit .env.miner — set USST_MINER_KEY
python miner/usst_miner.py
```

### Fund the Mining Pool
Send UST directly to the mining contract to extend the reward pool for all miners:

```
Contract: 0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0
Network:  Chain ID 778889
```

### Report Issues
Open an issue on GitHub for bugs, security concerns, or feature requests:
- **Bug reports:** describe the error, steps to reproduce, expected vs actual behavior
- **Security issues:** report privately via GitHub Security Advisories (preferred) or by opening a regular issue

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and test them
4. Open a pull request with a clear description of what changed and why

**What we welcome:**
- Miner improvements (CPU/GPU performance, reliability)
- Explorer UI improvements
- Documentation updates and translations
- Smart contract audits (read-only — the contract is deployed and immutable)
- Scripts and tooling

**Code style:**
- Python: follow PEP 8; prefer `black` formatting
- Solidity: follow the existing contract style
- JavaScript: plain ES2020, no build step required

---

## Project Structure

```
contracts/      USSTMine.sol — PoW mining contract (v3, deployed, immutable)
miner/          Python miner client (GPU CUDA + CPU fallback)
config/
  explorer/     Block explorer + DEX + Faucet + Bridge (static HTML/JS)
  caddy/        Caddy web server config and static assets
  wireguard/    WireGuard VPN config examples
chain/          genesis.json and chain bootstrap docs
docs/           Whitepaper, announcements, listing documentation
scripts/        Deployment and maintenance scripts
```

---

## Network Information

| Parameter | Value |
|-----------|-------|
| Chain ID | `778889` |
| RPC | `https://147-45-143-23.sslip.io/rpc` |
| Explorer | `https://147-45-143-23.sslip.io` |
| Mining contract | `0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0` |

---

## Code of Conduct

- Be respectful and constructive in all interactions
- No spam, no solicitation, no irrelevant content
- Focus on improving the network for all participants

---

MIT License — contributions are accepted under the same license.
