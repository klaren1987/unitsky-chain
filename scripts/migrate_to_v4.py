#!/usr/bin/env python3
"""
USSTMine v3 → v4 Migration Script
===================================
1. Read v3 state (totalMined, poolBalance, owner)
2. Compile & deploy USSTMine v4 with initialTotalMined from v3
3. Fund v4 pool by withdrawing from v3 via withdrawOwner()
4. Verify v4 is live and correct
5. Write new address to deployed.json + .env

Usage:
    python scripts/migrate_to_v4.py [--dry-run]
"""

import json
import os
import sys
import time
from pathlib import Path

# ── deps ──────────────────────────────────────────────────────────────────────
try:
    import solcx
    from web3 import Web3
    from eth_account import Account
except ImportError:
    print("Missing deps. Run: pip install py-solc-x web3")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DRY_RUN = "--dry-run" in sys.argv

# ── Config ────────────────────────────────────────────────────────────────────
RPC_URL       = os.getenv("USST_RPC", "http://127.0.0.1:8545")
DEPLOYER_KEY  = os.getenv("USST_DEPLOYER_KEY", "")
CHAIN_ID      = int(os.getenv("USST_CHAIN_ID", "778889"))
V3_ADDRESS    = os.getenv("USST_CONTRACT_ADDRESS",
                           "0xB650a7B39a447A266b927d6e0908AC6d0091FC67")
DEPLOYED_PATH = Path(os.getenv("USST_DEPLOYED_PATH",
                                str(ROOT / "deployed.json")))
ENV_PATH      = ROOT / ".env"

if not DEPLOYER_KEY:
    # Try reading from .env
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("USST_DEPLOYER_KEY="):
                DEPLOYER_KEY = line.split("=", 1)[1].strip()
    if not DEPLOYER_KEY:
        print("ERROR: set USST_DEPLOYER_KEY in env or .env")
        sys.exit(1)

from web3.middleware import ExtraDataToPOAMiddleware
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
if not w3.is_connected():
    print(f"ERROR: cannot connect to {RPC_URL}")
    sys.exit(1)

deployer = Account.from_key(DEPLOYER_KEY)
print(f"Deployer:  {deployer.address}")
print(f"RPC:       {RPC_URL}")
print(f"Chain ID:  {CHAIN_ID}")
print(f"V3 addr:   {V3_ADDRESS}")
print(f"Dry run:   {DRY_RUN}")
print()

# ── Read v3 state ─────────────────────────────────────────────────────────────
V3_ABI = [
    {"name": "totalMined",   "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "poolBalance",  "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "owner",        "type": "function", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
    {"name": "totalBurned",  "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "difficulty",   "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "reward",       "type": "function", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "withdrawOwner","type": "function", "inputs": [{"name": "amount","type": "uint256"}],
     "outputs": [], "stateMutability": "nonpayable"},
]

v3 = w3.eth.contract(address=Web3.to_checksum_address(V3_ADDRESS), abi=V3_ABI)
total_mined  = v3.functions.totalMined().call()
pool_balance = v3.functions.poolBalance().call()
v3_owner     = v3.functions.owner().call()
total_burned = v3.functions.totalBurned().call()
difficulty   = v3.functions.difficulty().call()
gross_reward = v3.functions.reward().call()

print("-- V3 state ------------------------------------------")
print(f"  totalMined:   {total_mined}")
print(f"  poolBalance:  {w3.from_wei(pool_balance, 'ether'):.6f} UST")
print(f"  totalBurned:  {w3.from_wei(total_burned, 'ether'):.6f} UST")
print(f"  difficulty:   {difficulty}")
print(f"  era-0 reward: {w3.from_wei(gross_reward, 'ether'):.4f} UST")
print(f"  owner:        {v3_owner}")
print()

if v3_owner.lower() != deployer.address.lower():
    print(f"ERROR: deployer {deployer.address} is not the v3 owner {v3_owner}")
    sys.exit(1)

# ── Compile v4 ────────────────────────────────────────────────────────────────
print("Compiling USSTMine v4 ...")
solcx.install_solc("0.8.20", show_progress=False)
compiled = solcx.compile_files(
    [str(ROOT / "contracts" / "USSTMine.sol")],
    output_values=["abi", "bin"],
    solc_version="0.8.20",
    evm_version="paris",
    optimize=True,
    optimize_runs=200,
)
key = [k for k in compiled if "USSTMine" in k][0]
abi = compiled[key]["abi"]
bytecode = compiled[key]["bin"]
print(f"  compiled OK  ({len(bytecode)//2} bytes)")

if DRY_RUN:
    print("\n[DRY RUN] — stopping before any transactions.")
    sys.exit(0)

# ── Deploy v4 ─────────────────────────────────────────────────────────────────
print("\nDeploying USSTMine v4 ...")

def send_tx(tx):
    tx = dict(tx)
    tx["from"]     = deployer.address
    tx["nonce"]    = w3.eth.get_transaction_count(deployer.address)
    tx["chainId"]  = CHAIN_ID
    tx["gasPrice"] = max(w3.eth.gas_price, 10**9)
    # Remove EIP-1559 fields if present (Clique PoA uses legacy txs)
    tx.pop("maxFeePerGas", None)
    tx.pop("maxPriorityFeePerGas", None)
    tx.pop("type", None)
    if "gas" not in tx:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.3)
    signed = deployer.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    if receipt["status"] != 1:
        raise RuntimeError(f"TX failed: {h.hex()}")
    return receipt

V4 = w3.eth.contract(abi=abi, bytecode=bytecode)
deploy_tx = V4.constructor(total_mined).build_transaction({
    "from":  deployer.address,
    "value": 0,
})
receipt = send_tx(deploy_tx)
v4_address = receipt["contractAddress"]
print(f"  v4 deployed: {v4_address}  (block {receipt['blockNumber']})")

# ── Withdraw from v3 → fund v4 ────────────────────────────────────────────────
# Re-read current balance right before withdrawing (mining continues)
pool_balance = v3.functions.poolBalance().call()
print(f"\nWithdrawing {w3.from_wei(pool_balance, 'ether'):.4f} UST from v3 ...")
withdraw_tx = v3.functions.withdrawOwner(pool_balance).build_transaction({
    "from": deployer.address,
})
receipt = send_tx(withdraw_tx)
print(f"  withdrawn OK  (block {receipt['blockNumber']})")

# Wait one block
time.sleep(6)
deployer_balance = w3.eth.get_balance(deployer.address)
print(f"  deployer balance: {w3.from_wei(deployer_balance, 'ether'):.4f} UST")

# Fund v4 (send full pool_balance)
fund_amount = min(pool_balance, deployer_balance - w3.to_wei(0.01, "ether"))
print(f"\nFunding v4 with {w3.from_wei(fund_amount, 'ether'):.4f} UST ...")
fund_tx = {
    "to":    v4_address,
    "value": fund_amount,
    "data":  b"",
}
receipt = send_tx(fund_tx)
print(f"  funded OK  (block {receipt['blockNumber']})")

# ── Verify v4 ─────────────────────────────────────────────────────────────────
v4 = w3.eth.contract(address=v4_address, abi=abi)
v4_pool   = v4.functions.poolBalance().call()
v4_mined  = v4.functions.totalMined().call()
v4_era    = v4.functions.currentEra().call()
v4_reward = v4.functions.reward().call()
v4_diff   = v4.functions.difficulty().call()
v4_min_d  = v4.functions.MIN_DIFFICULTY().call()

print("\n-- V4 state ------------------------------------------")
print(f"  address:       {v4_address}")
print(f"  poolBalance:   {w3.from_wei(v4_pool, 'ether'):.6f} UST")
print(f"  totalMined:    {v4_mined} (preserved from v3)")
print(f"  currentEra:    {v4_era}")
print(f"  reward:        {w3.from_wei(v4_reward, 'ether'):.6f} UST")
print(f"  difficulty:    {v4_diff}")
print(f"  MIN_DIFFICULTY:{v4_min_d}")

assert v4_mined == total_mined, "totalMined mismatch!"
assert v4_pool > 0, "v4 pool is empty!"
print("\n  ✅ All assertions passed")

# ── Save new address ──────────────────────────────────────────────────────────
print(f"\nUpdating deployed.json and .env ...")

if DEPLOYED_PATH.exists():
    deployed = json.loads(DEPLOYED_PATH.read_text())
else:
    deployed = {}
deployed["USSTMine"] = v4_address
deployed["USSTMineV3"] = V3_ADDRESS  # keep v3 for reference
DEPLOYED_PATH.write_text(json.dumps(deployed, indent=2))
print(f"  {DEPLOYED_PATH} updated")

# Update .env USST_CONTRACT_ADDRESS if present
if ENV_PATH.exists():
    lines = ENV_PATH.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("USST_CONTRACT_ADDRESS="):
            new_lines.append(f"USST_CONTRACT_ADDRESS={v4_address}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"USST_CONTRACT_ADDRESS={v4_address}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n")
    print(f"  .env updated")

print(f"""
======================================================
  Migration complete!

  V3 (retired):  {V3_ADDRESS}
  V4 (active):   {v4_address}

  Next steps:
    1. Restart miner and rpc-filter containers
    2. Verify: python scripts/functional_test.py
======================================================
""")
