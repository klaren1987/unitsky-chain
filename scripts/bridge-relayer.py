#!/usr/bin/env python3
"""
UST Bridge Relayer v2
=====================
Watches Ethereum for USDT deposits to the treasury address → mints BridgedUSDT on Chain 778889.
Watches Chain 778889 for BridgeWithdraw events → sends real USDT back on Ethereum.

Security features:
  - Processed-tx cache prevents double-minting even on relayer restart
  - Minimum / maximum deposit limits (1 USDT – 10,000 USDT)
  - Per-address rate limiting (5 deposits per hour)
  - Structured audit log (bridge-audit.log) records every action
  - Pre-flight balance check ensures treasury has sufficient USDT before completing withdrawal

Environment variables:
    BRIDGE_OPERATOR_KEY      — private key of the bridge operator
    BRIDGED_USDT_ADDRESS     — BridgedUSDT contract on Chain 778889
    ETH_RPC                  — Ethereum mainnet RPC URL
    BRIDGE_TREASURY_ADDRESS  — Ethereum address that receives USDT deposits
    USST_RPC                 — Chain 778889 RPC (default: http://127.0.0.1:8545)
    BRIDGE_MIN_USDT          — Minimum deposit in USDT (default: 1.0)
    BRIDGE_MAX_USDT          — Maximum single deposit in USDT (default: 10000.0)
    BRIDGE_RATE_LIMIT        — Max deposits per address per hour (default: 5)

Real USDT on Ethereum mainnet: 0xdAC17F958D2ee523a2206206994597C13D831ec7
"""

import os, sys, json, time, logging, urllib.request, fcntl
from collections import defaultdict
from pathlib import Path
from eth_account import Account
from eth_hash.auto import keccak

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path(os.path.dirname(__file__)).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "bridge-audit.log"),
    ],
)
log = logging.getLogger("bridge")

# ── Config ────────────────────────────────────────────────────────────────────
OPERATOR_KEY    = os.getenv("BRIDGE_OPERATOR_KEY", "")
BRIDGED_USDT    = os.getenv("BRIDGED_USDT_ADDRESS", "")
ETH_RPC         = os.getenv("ETH_RPC", "")
TREASURY        = os.getenv("BRIDGE_TREASURY_ADDRESS", "")
UST_RPC         = os.getenv("USST_RPC", "http://127.0.0.1:8545")
REAL_USDT_ETH   = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
CHAIN_778889    = 778889
CHAIN_ETH       = 1
POLL_INTERVAL   = 15

MIN_USDT        = float(os.getenv("BRIDGE_MIN_USDT",   "1.0"))
MAX_USDT        = float(os.getenv("BRIDGE_MAX_USDT",   "10000.0"))
RATE_LIMIT      = int(os.getenv("BRIDGE_RATE_LIMIT",   "5"))

# Minimum ETH to keep in treasury for gas — warn loudly if below
ETH_WARN_WEI    = int(float(os.getenv("BRIDGE_ETH_WARN",  "0.005")) * 1e18)
ETH_PAUSE_WEI   = int(float(os.getenv("BRIDGE_ETH_PAUSE", "0.0005")) * 1e18)  # pause withdrawals below this

for var, val in [("BRIDGE_OPERATOR_KEY", OPERATOR_KEY), ("BRIDGED_USDT_ADDRESS", BRIDGED_USDT),
                 ("ETH_RPC", ETH_RPC), ("BRIDGE_TREASURY_ADDRESS", TREASURY)]:
    if not val:
        log.error(f"Missing required env var: {var}")
        sys.exit(1)

operator = Account.from_key(OPERATOR_KEY)
log.info(f"Bridge operator:  {operator.address}")
log.info(f"Treasury:         {TREASURY}")
log.info(f"BridgedUSDT:      {BRIDGED_USDT}")
log.info(f"Limits:           min={MIN_USDT} USDT  max={MAX_USDT} USDT  rate={RATE_LIMIT}/hr")

# ── Event topics ──────────────────────────────────────────────────────────────
TOPIC_TRANSFER    = "0x" + keccak(b"Transfer(address,address,uint256)").hex()
TOPIC_BRIDGE_WITH = "0x" + keccak(b"BridgeWithdraw(address,uint256,string)").hex()

# ── State files ───────────────────────────────────────────────────────────────
BASE_DIR    = Path(os.path.dirname(__file__)).parent
STATE_FILE  = BASE_DIR / ".bridge-state.json"
PROC_FILE   = BASE_DIR / ".bridge-processed.json"   # set of processed eth tx hashes

def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

# ── Rate limiter ──────────────────────────────────────────────────────────────
_rate_window: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(address: str) -> bool:
    now = time.time()
    window = _rate_window[address.lower()]
    window[:] = [t for t in window if now - t < 3600]
    if len(window) >= RATE_LIMIT:
        return False
    window.append(now)
    return True

# ── RPC helpers ───────────────────────────────────────────────────────────────
def _rpc(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req  = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json",
                                           "User-Agent": "UST-Bridge-Relayer/2.0"},
                                  method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if "error" in resp:
        raise RuntimeError(f"RPC {method} error: {resp['error']}")
    return resp["result"]

def get_block(url) -> int:
    return int(_rpc(url, "eth_blockNumber", []), 16)

def get_usdt_balance(url, chain_id, address) -> int:
    selector = "0x" + keccak(b"balanceOf(address)").hex()[:8]
    padded   = address[2:].lower().zfill(64)
    result   = _rpc(url, "eth_call",
                    [{"to": REAL_USDT_ETH, "data": selector + padded}, "latest"])
    return int(result, 16)

def get_eth_balance(address: str) -> int:
    """Return treasury ETH balance in wei on Ethereum mainnet."""
    try:
        result = _rpc(ETH_RPC, "eth_getBalance", [address, "latest"])
        return int(result, 16)
    except Exception:
        return -1

_last_eth_warn = 0.0

def check_treasury_eth() -> bool:
    """Check treasury ETH balance. Return False if withdrawals should pause."""
    global _last_eth_warn
    bal = get_eth_balance(TREASURY)
    if bal < 0:
        return True  # RPC error — don't block
    now = time.time()
    if bal == 0:
        if now - _last_eth_warn > 3600:
            log.critical(
                f"TREASURY_ETH_EMPTY  treasury={TREASURY}  "
                f"Withdrawals paused. Send ETH to treasury to resume."
            )
            _last_eth_warn = now
        return False
    if bal < ETH_PAUSE_WEI:
        if now - _last_eth_warn > 3600:
            log.error(
                f"TREASURY_ETH_CRITICAL  balance={bal/1e18:.6f} ETH  "
                f"threshold={ETH_PAUSE_WEI/1e18:.4f} ETH  Pausing withdrawals."
            )
            _last_eth_warn = now
        return False
    if bal < ETH_WARN_WEI:
        if now - _last_eth_warn > 3600:
            log.warning(
                f"TREASURY_ETH_LOW  balance={bal/1e18:.6f} ETH  "
                f"warn_threshold={ETH_WARN_WEI/1e18:.4f} ETH  "
                f"Please top up: {TREASURY}"
            )
            _last_eth_warn = now
    return True

def send_tx(url, chain_id, to, data, value=0):
    nonce     = int(_rpc(url, "eth_getTransactionCount", [operator.address, "pending"]), 16)
    gas_price = max(int(_rpc(url, "eth_gasPrice", []), 16), 10**9)
    gas       = int(_rpc(url, "eth_estimateGas",
                         [{"from": operator.address, "to": to,
                           "data": data, "value": hex(value)}]), 16)
    tx = {"nonce": nonce, "gasPrice": gas_price, "gas": int(gas * 1.2),
          "to": to, "value": value, "data": data, "chainId": chain_id}
    signed = operator.sign_transaction(tx)
    return _rpc(url, "eth_sendRawTransaction", [signed.raw_transaction.hex()])

# ── Bridge actions ────────────────────────────────────────────────────────────
def mint_bridged(recipient: str, amount_6dec: int, eth_tx_hash: str) -> str:
    """Call bridgeMint(address,uint256,bytes32) on BridgedUSDT contract."""
    selector = "0x" + keccak(b"bridgeMint(address,uint256,bytes32)").hex()[:8]
    data = selector + recipient[2:].lower().zfill(64) + hex(amount_6dec)[2:].zfill(64) + eth_tx_hash[2:].zfill(64)
    return send_tx(UST_RPC, CHAIN_778889, BRIDGED_USDT, data)

def send_eth_usdt(recipient_eth: str, amount_6dec: int) -> str:
    """Transfer real USDT on Ethereum to recipient."""
    selector = "0x" + keccak(b"transfer(address,uint256)").hex()[:8]
    data = selector + recipient_eth[2:].lower().zfill(64) + hex(amount_6dec)[2:].zfill(64)
    return send_tx(ETH_RPC, CHAIN_ETH, REAL_USDT_ETH, data)

# ── Event scanners ────────────────────────────────────────────────────────────
def get_eth_deposits(from_block: int, to_block: int):
    treasury_topic = "0x" + TREASURY[2:].lower().zfill(64)
    logs = _rpc(ETH_RPC, "eth_getLogs", [{
        "address":   REAL_USDT_ETH,
        "topics":    [TOPIC_TRANSFER, None, treasury_topic],
        "fromBlock": hex(from_block),
        "toBlock":   hex(to_block),
    }])
    result = []
    for lg in logs:
        tx_hash = lg["transactionHash"]
        sender  = "0x" + lg["topics"][1][26:]
        amount  = int(lg["data"], 16)
        result.append((tx_hash, sender, amount))
    return result

def get_withdrawals(from_block: int, to_block: int):
    logs = _rpc(UST_RPC, "eth_getLogs", [{
        "address":   BRIDGED_USDT,
        "topics":    [TOPIC_BRIDGE_WITH],
        "fromBlock": hex(from_block),
        "toBlock":   hex(to_block),
    }])
    result = []
    for lg in logs:
        burner = "0x" + lg["topics"][1][26:]
        amount = int(lg["data"][:66], 16)
        try:
            data_hex   = lg["data"][2:]
            str_offset = int(data_hex[64:128], 16) * 2
            str_len    = int(data_hex[str_offset:str_offset + 64], 16)
            eth_addr   = bytes.fromhex(data_hex[str_offset + 64:str_offset + 64 + str_len * 2]).decode()
        except Exception:
            eth_addr = ""
        result.append((lg["transactionHash"], burner, amount, eth_addr))
    return result

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    log.info("=== Bridge relayer v2 starting ===")

    state     = load_json(STATE_FILE, None)
    processed = set(load_json(PROC_FILE, []))   # set of processed eth tx hashes

    if state is None:
        eth_bn = get_block(ETH_RPC)
        ust_bn = get_block(UST_RPC)
        state  = {"eth_last": eth_bn, "ust_last": ust_bn}
        log.info(f"First run — starting from ETH block {eth_bn}, UST block {ust_bn}")
    else:
        log.info(f"Resuming — ETH block {state['eth_last']}, UST block {state['ust_last']}")
        log.info(f"Processed tx cache: {len(processed)} entries")

    while True:
        try:
            eth_current = get_block(ETH_RPC)
            ust_current = get_block(UST_RPC)

            # ── Ethereum deposits → mint BridgedUSDT ─────────────────────────
            if eth_current > state["eth_last"]:
                from_blk = state["eth_last"] + 1
                to_blk   = min(eth_current, from_blk + 100)
                deposits = get_eth_deposits(from_blk, to_blk)

                for tx_hash, sender, amount in deposits:
                    usdt_human = amount / 1_000_000

                    # Double-spend guard
                    if tx_hash in processed:
                        log.warning(f"SKIP duplicate tx {tx_hash}")
                        continue

                    # Amount limits
                    if usdt_human < MIN_USDT:
                        log.warning(f"SKIP {tx_hash}: {usdt_human:.2f} USDT < MIN ({MIN_USDT})")
                        continue
                    if usdt_human > MAX_USDT:
                        log.warning(f"SKIP {tx_hash}: {usdt_human:.2f} USDT > MAX ({MAX_USDT})")
                        continue

                    # Rate limit
                    if not check_rate_limit(sender):
                        log.warning(f"RATE LIMIT {sender} — deposit {tx_hash} queued for manual review")
                        continue

                    log.info(f"DEPOSIT  {usdt_human:.6f} USDT  from={sender}  eth_tx={tx_hash}")
                    try:
                        mint_tx = mint_bridged(sender, amount, tx_hash)
                        processed.add(tx_hash)
                        save_json(PROC_FILE, list(processed))
                        log.info(f"  MINTED  ust_tx={mint_tx}")
                    except Exception as e:
                        log.error(f"  MINT_FAILED  {e}  eth_tx={tx_hash}")

                state["eth_last"] = to_blk

            # ── UST withdrawals → send real USDT on Ethereum ─────────────────
            if ust_current > state["ust_last"]:
                from_blk = state["ust_last"] + 1
                to_blk   = min(ust_current, from_blk + 500)
                withdrawals = get_withdrawals(from_blk, to_blk)

                for tx_hash, burner, amount, eth_addr in withdrawals:
                    usdt_human = amount / 1_000_000
                    log.info(f"WITHDRAW  {usdt_human:.6f} USDT  burner={burner}  eth={eth_addr}  ust_tx={tx_hash}")

                    if not eth_addr or not eth_addr.startswith("0x") or len(eth_addr) != 42:
                        log.error(f"  INVALID_ETH_ADDR '{eth_addr}' — manual action required")
                        continue

                    # Pre-flight: check treasury ETH gas balance
                    if not check_treasury_eth():
                        log.error(f"  PAUSED_NO_GAS  ust_tx={tx_hash} — top up ETH at {TREASURY}")
                        continue

                    # Pre-flight: check treasury USDT balance
                    try:
                        treasury_bal = get_usdt_balance(ETH_RPC, CHAIN_ETH, TREASURY)
                        if treasury_bal < amount:
                            log.error(f"  INSUFFICIENT_TREASURY  have={treasury_bal/1e6:.2f}  need={usdt_human:.2f} — MANUAL")
                            continue
                    except Exception as e:
                        log.error(f"  BALANCE_CHECK_FAILED  {e}")
                        continue

                    try:
                        eth_tx = send_eth_usdt(eth_addr, amount)
                        log.info(f"  SENT  eth_tx={eth_tx}")
                    except Exception as e:
                        log.error(f"  SEND_FAILED  {e}  — MANUAL ACTION REQUIRED for ust_tx={tx_hash}")

                state["ust_last"] = ust_current

            save_json(STATE_FILE, state)

        except Exception as e:
            err_str = str(e)
            log.error(f"RELAYER_ERROR  {err_str}")
            # pebble: not found → Geth bloom filter missing for old blocks.
            # Skip forward to avoid infinite retry on same broken range.
            if "pebble: not found" in err_str and "ust_last" in state:
                skip_to = state["ust_last"] + 50
                log.warning(f"pebble error — skipping ust_last forward to {skip_to}")
                state["ust_last"] = skip_to
                save_json(STATE_FILE, state)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
