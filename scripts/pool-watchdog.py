#!/usr/bin/env python3
"""
UST Mining Pool Watchdog
========================
Monitors the USSTMine v4 pool balance and automatically refills it
from the deployer wallet when the balance drops below a configurable threshold.

This service removes the "operator manually fills pool" concern: the refill
logic is open-source, deterministic, and produces on-chain events that anyone
can verify.

Transparency guarantees:
  - Every refill is a regular on-chain transaction (visible in the explorer)
  - FundAdded events are emitted by the contract (listeners can subscribe)
  - This script is public and auditable

Environment variables:
    USST_RPC              — Geth RPC URL (default: http://127.0.0.1:8545)
    USST_CONTRACT_ADDRESS — USSTMine v4 address
    USST_DEPLOYER_KEY     — deployer private key (wallet that funds the pool)
    POOL_MIN_UST          — trigger threshold in UST (default: 1000.0)
    POOL_REFILL_UST       — amount to add per refill (default: 5000.0)
    POOL_CHECK_INTERVAL   — seconds between checks (default: 60)
    USST_CHAIN_ID         — chain ID (default: 778889)

Usage:
    python scripts/pool-watchdog.py
    # or via Docker:
    docker compose -f docker-compose.public.yml up -d pool-watchdog
"""

import os, sys, time, json, logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "pool-watchdog.log"),
    ],
)
log = logging.getLogger("pool-watchdog")

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    from eth_account import Account
except ImportError:
    log.error("Missing deps: pip install web3")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
ENV  = ROOT / ".env"

# Load .env into os.environ
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        k, _, v = line.partition("=")
        if k.strip() and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip())

RPC          = os.getenv("USST_RPC", "http://127.0.0.1:8545")
CONTRACT     = os.getenv("USST_CONTRACT_ADDRESS", "")
DEPLOYER_KEY = os.getenv("USST_DEPLOYER_KEY", "")
CHAIN_ID     = int(os.getenv("USST_CHAIN_ID", "778889"))
MIN_UST      = float(os.getenv("POOL_MIN_UST",      "1000.0"))
REFILL_UST   = float(os.getenv("POOL_REFILL_UST",   "5000.0"))
CHECK_SECS   = int(os.getenv("POOL_CHECK_INTERVAL", "60"))

if not CONTRACT or not DEPLOYER_KEY:
    log.error("USST_CONTRACT_ADDRESS and USST_DEPLOYER_KEY must be set")
    sys.exit(1)

w3 = Web3(Web3.HTTPProvider(RPC))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    log.error(f"Cannot connect to RPC: {RPC}")
    sys.exit(1)

deployer = Account.from_key(DEPLOYER_KEY)

MINE_ABI = [
    {"name": "poolBalance", "type": "function", "inputs": [],
     "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "fund", "type": "function", "inputs": [],
     "outputs": [], "stateMutability": "payable"},
    {"name": "owner", "type": "function", "inputs": [],
     "outputs": [{"type": "address"}], "stateMutability": "view"},
]
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT), abi=MINE_ABI)

log.info("=== Pool Watchdog starting ===")
log.info(f"  RPC:          {RPC}")
log.info(f"  Contract:     {CONTRACT}")
log.info(f"  Deployer:     {deployer.address}")
log.info(f"  Threshold:    {MIN_UST} UST")
log.info(f"  Refill size:  {REFILL_UST} UST")
log.info(f"  Check every:  {CHECK_SECS}s")

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = {"checks": 0, "refills": 0, "total_funded_wei": 0}


def send_tx(to, value_wei, data=b""):
    tx = {
        "from":     deployer.address,
        "to":       to,
        "value":    value_wei,
        "data":     data,
        "nonce":    w3.eth.get_transaction_count(deployer.address),
        "chainId":  CHAIN_ID,
        "gasPrice": max(w3.eth.gas_price, 10**9),
    }
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.3)
    signed  = deployer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    assert receipt["status"] == 1, f"TX failed: {tx_hash.hex()}"
    return receipt, tx_hash.hex()


def check_and_refill():
    stats["checks"] += 1
    pool_wei     = contract.functions.poolBalance().call()
    pool_ust     = float(w3.from_wei(pool_wei, "ether"))
    deployer_wei = w3.eth.get_balance(deployer.address)
    deployer_ust = float(w3.from_wei(deployer_wei, "ether"))

    log.info(f"Pool: {pool_ust:.4f} UST  |  Deployer: {deployer_ust:.4f} UST")

    if pool_ust >= MIN_UST:
        return  # pool is healthy

    refill_wei = w3.to_wei(REFILL_UST, "ether")
    gas_reserve = w3.to_wei(1.0, "ether")

    if deployer_wei < refill_wei + gas_reserve:
        available = deployer_wei - gas_reserve
        if available <= 0:
            log.warning(f"Deployer has insufficient funds to refill! "
                        f"Pool={pool_ust:.2f} UST (below {MIN_UST}). Manual action needed.")
            return
        refill_wei = available
        log.warning(f"Partial refill: {float(w3.from_wei(refill_wei, 'ether')):.4f} UST "
                    f"(deployer low on funds)")

    log.info(f"REFILL triggered — pool={pool_ust:.4f} UST < threshold={MIN_UST} UST")
    log.info(f"  Sending {float(w3.from_wei(refill_wei, 'ether')):.4f} UST to pool ...")

    # Use fund() to emit FundAdded event (visible in explorer)
    fund_data = w3.keccak(text="fund()")[:4]
    receipt, tx_hash = send_tx(
        to=Web3.to_checksum_address(CONTRACT),
        value_wei=refill_wei,
        data=fund_data,
    )

    stats["refills"] += 1
    stats["total_funded_wei"] += refill_wei
    total_funded = float(w3.from_wei(stats["total_funded_wei"], "ether"))

    new_pool = float(w3.from_wei(contract.functions.poolBalance().call(), "ether"))
    log.info(f"  REFILLED  tx={tx_hash}  block={receipt['blockNumber']}")
    log.info(f"  New pool balance: {new_pool:.4f} UST")
    log.info(f"  Session stats: {stats['refills']} refills, {total_funded:.2f} UST total funded")


def main():
    while True:
        try:
            check_and_refill()
        except Exception as e:
            log.error(f"Watchdog error: {e}")
        time.sleep(CHECK_SECS)


if __name__ == "__main__":
    main()
