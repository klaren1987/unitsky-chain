#!/usr/bin/env python3
"""
Emergency Key Rotation & Fund Rescue
=====================================
1. Generates 4 new secure private keys (signer, deployer, miner, faucet)
2. Rescues LP tokens from old compromised deployer → new deployer
3. Rescues UST from old deployer + old signer → new deployer
4. Outputs new .env values ready to paste

Run inside bridge-relayer container:
  docker exec unitsky-string-bridge-relayer python3 /app/scripts/emergency-rotate-keys.py
"""

import os, json, time, secrets, urllib.request
from eth_account import Account
from eth_utils import to_checksum_address
from eth_hash.auto import keccak

RPC         = os.getenv("USST_RPC", "http://unitsky-string-node:8545")
CHAIN_ID    = 778889

# ── Old compromised keys ───────────────────────────────────────────────────────
OLD_DEPLOYER_KEY = "0x3014dac8e7e8082dd791032d9b451bcaf5f5b3b59f1bcc748516e78ba35555bc"
OLD_SIGNER_KEY   = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # Hardhat #0!
OLD_MINER_KEY    = "0x1d00410783c9ed86ee2a45be96f3b47907159d1672fb169741b88a0b6b4e0a5b"
OLD_FAUCET_KEY   = "0x5bfe192b3fbddcc24a3ac097e864c90df3c60cb5e87133215f212dcda90d5943"

old_deployer = Account.from_key(OLD_DEPLOYER_KEY)
old_signer   = Account.from_key(OLD_SIGNER_KEY)
old_miner    = Account.from_key(OLD_MINER_KEY)
old_faucet   = Account.from_key(OLD_FAUCET_KEY)

# ── Contract addresses ─────────────────────────────────────────────────────────
PAIR_ADDR  = "0x0f53baf46172bddf8004909d05e9ab8592ca08e7"   # WUST/bUSDT LP token
WUST_ADDR  = "0x372cf3bc672639f4089d493c3863933affd88014"
BUSDT_ADDR = "0xcd7cb25f025B20D5f90C0FDA3463D91AF76A8EF1"

# ── Generate new keys (or resume from previous run) ───────────────────────────
RESUME_FILE = "/tmp/new-keys.json"

def new_key():
    pk = "0x" + secrets.token_hex(32)
    acct = Account.from_key(pk)
    return pk, acct.address

if os.path.exists(RESUME_FILE):
    saved = json.load(open(RESUME_FILE))
    NEW_SIGNER_KEY   = saved["USST_SIGNER_KEY"]
    NEW_SIGNER_ADDR  = saved["USST_SIGNER_ADDRESS"]
    NEW_DEPLOYER_KEY = saved["USST_DEPLOYER_KEY"]
    NEW_DEPLOYER_ADDR = Account.from_key(NEW_DEPLOYER_KEY).address
    NEW_MINER_KEY    = saved["USST_MINER_KEY"]
    NEW_MINER_ADDR   = Account.from_key(NEW_MINER_KEY).address
    NEW_FAUCET_KEY   = saved["USST_FAUCET_KEY"]
    NEW_FAUCET_ADDR  = Account.from_key(NEW_FAUCET_KEY).address
    print("Resuming from saved keys.")
else:
    NEW_DEPLOYER_KEY, NEW_DEPLOYER_ADDR = new_key()
    NEW_SIGNER_KEY,   NEW_SIGNER_ADDR   = new_key()
    NEW_MINER_KEY,    NEW_MINER_ADDR    = new_key()
    NEW_FAUCET_KEY,   NEW_FAUCET_ADDR   = new_key()
    # Save immediately before doing anything
    json.dump({
        "USST_SIGNER_KEY":    NEW_SIGNER_KEY,
        "USST_SIGNER_ADDRESS": NEW_SIGNER_ADDR,
        "USST_DEPLOYER_KEY":  NEW_DEPLOYER_KEY,
        "USST_MINER_KEY":     NEW_MINER_KEY,
        "USST_FAUCET_KEY":    NEW_FAUCET_KEY,
        "OLD_SIGNER":         old_signer.address,
    }, open(RESUME_FILE, "w"), indent=2)
    print(f"New keys saved to {RESUME_FILE}")

print("=" * 65)
print("NEW KEYS GENERATED")
print("=" * 65)
print(f"  NEW_SIGNER:   {NEW_SIGNER_ADDR}  (keep secret)")
print(f"  NEW_DEPLOYER: {NEW_DEPLOYER_ADDR}  (keep secret)")
print(f"  NEW_MINER:    {NEW_MINER_ADDR}  (keep secret)")
print(f"  NEW_FAUCET:   {NEW_FAUCET_ADDR}  (keep secret)")
print()

# ── RPC helpers ───────────────────────────────────────────────────────────────
def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    req  = urllib.request.Request(RPC, data=body,
                                  headers={"Content-Type":"application/json"},
                                  method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if "error" in resp:
        raise RuntimeError(f"RPC {method}: {resp['error']}")
    return resp["result"]

def get_balance(addr):
    return int(_rpc("eth_getBalance", [addr, "latest"]), 16)

def get_token_balance(token, addr):
    sel = keccak(b"balanceOf(address)").hex()[:8]
    pad = addr[2:].lower().zfill(64)
    r = _rpc("eth_call", [{"to": token, "data": "0x" + sel + pad}, "latest"])
    return int(r, 16)

def get_nonce(addr):
    return int(_rpc("eth_getTransactionCount", [addr, "pending"]), 16)

def sign_and_send(key, to, data="0x", value=0, gas=None):
    acct = Account.from_key(key)
    nonce = get_nonce(acct.address)
    gas_price = max(int(_rpc("eth_gasPrice", []), 16), 10**9)
    if gas is None:
        try:
            gas = int(_rpc("eth_estimateGas", [{
                "from": acct.address, "to": to,
                "data": data, "value": hex(value)
            }]), 16) + 20000
        except Exception:
            gas = 200000
    tx = {
        "nonce": nonce, "gasPrice": gas_price, "gas": gas,
        "to": to_checksum_address(to), "value": value, "data": data, "chainId": CHAIN_ID,
    }
    signed = acct.sign_transaction(tx)
    raw = "0x" + signed.raw_transaction.hex()
    return _rpc("eth_sendRawTransaction", [raw])

def wait(tx_hash, label=""):
    print(f"  ⏳ {label} tx {tx_hash[:18]}… ", end="", flush=True)
    for _ in range(60):
        time.sleep(2)
        try:
            r = _rpc("eth_getTransactionReceipt", [tx_hash])
            if r:
                status = int(r.get("status","0x0"),16)
                print("✅ ok" if status == 1 else "❌ REVERTED")
                return status == 1
        except Exception:
            pass
    print("⏰ timeout")
    return False

def erc20_transfer(key, token, to, amount):
    sel = keccak(b"transfer(address,uint256)").hex()[:8]
    data = "0x" + sel + to[2:].lower().zfill(64) + hex(amount)[2:].zfill(64)
    return sign_and_send(key, token, data)

# ── Print current state ────────────────────────────────────────────────────────
print("CURRENT STATE (before rescue)")
print("-" * 50)

deployer_ust = get_balance(old_deployer.address)
deployer_lp  = get_token_balance(PAIR_ADDR, old_deployer.address)
signer_ust   = get_balance(old_signer.address)
miner_ust    = get_balance(old_miner.address)
faucet_ust   = get_balance(old_faucet.address)

print(f"  Old deployer {old_deployer.address}:")
print(f"    UST: {deployer_ust/1e18:.4f}   LP: {deployer_lp/1e18:.4f}")
print(f"  Old signer   {old_signer.address}:")
print(f"    UST: {signer_ust/1e18:.4f}")
print(f"  Old miner    {old_miner.address}:")
print(f"    UST: {miner_ust/1e18:.4f}")
print(f"  Old faucet   {old_faucet.address}:")
print(f"    UST: {faucet_ust/1e18:.4f}")
print()

# ── Step 1: Rescue LP tokens from old deployer ────────────────────────────────
if deployer_lp > 0:
    print(f"STEP 1: Rescue {deployer_lp/1e18:.4f} LP tokens → {NEW_DEPLOYER_ADDR}")
    tx = erc20_transfer(OLD_DEPLOYER_KEY, PAIR_ADDR, NEW_DEPLOYER_ADDR, deployer_lp)
    wait(tx, "LP transfer")
else:
    print("STEP 1: No LP tokens to rescue")

# ── Step 2: Rescue UST from old deployer ─────────────────────────────────────
deployer_ust = get_balance(old_deployer.address)  # refresh after LP tx
if deployer_ust > int(0.05 * 1e18):
    gas_price = max(int(_rpc("eth_gasPrice", []), 16), 10**9)
    gas_cost = 21000 * gas_price
    amount = deployer_ust - gas_cost  # exact: leave exactly enough for this 1 tx
    print(f"STEP 2: Rescue {amount/1e18:.4f} UST from old deployer → {NEW_DEPLOYER_ADDR}")
    if amount > 0:
        tx = sign_and_send(OLD_DEPLOYER_KEY, NEW_DEPLOYER_ADDR, "0x", value=amount, gas=21000)
        wait(tx, "UST rescue from deployer")
    else:
        print("  Not enough UST to rescue after gas")
else:
    print("STEP 2: Old deployer UST balance too low to rescue")

# ── Step 3: Rescue UST from old signer (Hardhat #0) ──────────────────────────
signer_ust = get_balance(old_signer.address)
if signer_ust > int(0.05 * 1e18):
    gas_price = max(int(_rpc("eth_gasPrice", []), 16), 10**9)
    gas_cost = 21000 * gas_price
    amount = signer_ust - gas_cost
    if amount > 0:
        print(f"STEP 3: Rescue {amount/1e18:.4f} UST from old signer → {NEW_DEPLOYER_ADDR}")
        tx = sign_and_send(OLD_SIGNER_KEY, NEW_DEPLOYER_ADDR, "0x", value=amount, gas=21000)
        wait(tx, "UST rescue from signer")
    else:
        print("STEP 3: Old signer UST insufficient after gas")
else:
    print("STEP 3: Old signer UST balance negligible")

# ── Step 4: Rescue UST from old miner (~9866 UST) ────────────────────────────
miner_ust = get_balance(old_miner.address)
if miner_ust > int(0.05 * 1e18):
    gas_price = max(int(_rpc("eth_gasPrice", []), 16), 10**9)
    gas_cost = 21000 * gas_price
    amount = miner_ust - gas_cost
    if amount > 0:
        print(f"STEP 4: Rescue {amount/1e18:.4f} UST from old miner → {NEW_DEPLOYER_ADDR}")
        tx = sign_and_send(OLD_MINER_KEY, NEW_DEPLOYER_ADDR, "0x", value=amount, gas=21000)
        wait(tx, "UST rescue from miner")
else:
    print("STEP 4: Old miner UST balance negligible")

# ── Step 5: Fund new faucet ────────────────────────────────────────────────────
FAUCET_FUNDING = int(100 * 1e18)
new_deployer_bal = get_balance(NEW_DEPLOYER_ADDR)
print(f"STEP 5: Fund new faucet ({NEW_FAUCET_ADDR}) with 100 UST")
if new_deployer_bal >= FAUCET_FUNDING + int(0.1 * 1e18):
    tx = sign_and_send(NEW_DEPLOYER_KEY, NEW_FAUCET_ADDR, "0x", value=FAUCET_FUNDING, gas=21000)
    wait(tx, "Fund new faucet")
else:
    print(f"  New deployer has only {new_deployer_bal/1e18:.2f} UST — skipping faucet funding")

# ── Final verification ─────────────────────────────────────────────────────────
print()
print("=" * 65)
print("POST-RESCUE STATE")
print("=" * 65)
print(f"  New deployer {NEW_DEPLOYER_ADDR}:")
print(f"    UST: {get_balance(NEW_DEPLOYER_ADDR)/1e18:.4f}")
print(f"    LP:  {get_token_balance(PAIR_ADDR, NEW_DEPLOYER_ADDR)/1e18:.4f}")
print(f"  New faucet   {NEW_FAUCET_ADDR}:")
print(f"    UST: {get_balance(NEW_FAUCET_ADDR)/1e18:.4f}")

# ── Output new .env values ─────────────────────────────────────────────────────
print()
print("=" * 65)
print("PASTE INTO .env (replace existing values):")
print("=" * 65)
print(f"USST_SIGNER_KEY={NEW_SIGNER_KEY}")
print(f"USST_SIGNER_ADDRESS={NEW_SIGNER_ADDR}")
print(f"USST_DEPLOYER_KEY={NEW_DEPLOYER_KEY}")
print(f"USST_MINER_KEY={NEW_MINER_KEY}")
print(f"USST_FAUCET_KEY={NEW_FAUCET_KEY}")
print("=" * 65)
print("After updating .env:")
print("  1. Propose new Clique signer (automated below)")
print("  2. Rebuild geth node: docker compose -f docker-compose.public.yml up -d --build unitsky-string-node")
print("  3. After node restarts, run clique.propose(OLD_SIGNER, false) to remove old signer")
print()
print(f"OLD signer address (to remove after rotation): {old_signer.address}")
print(f"NEW signer address (to propose):               {NEW_SIGNER_ADDR}")

# Save new keys to a temp file for the shell script to pick up
import json as _json
output = {
    "USST_SIGNER_KEY":   NEW_SIGNER_KEY,
    "USST_SIGNER_ADDRESS": NEW_SIGNER_ADDR,
    "USST_DEPLOYER_KEY": NEW_DEPLOYER_KEY,
    "USST_MINER_KEY":    NEW_MINER_KEY,
    "USST_FAUCET_KEY":   NEW_FAUCET_KEY,
    "OLD_SIGNER":        old_signer.address,
}
_json.dump(output, open("/tmp/new-keys.json", "w"), indent=2)
print("\nKeys saved to /tmp/new-keys.json")
