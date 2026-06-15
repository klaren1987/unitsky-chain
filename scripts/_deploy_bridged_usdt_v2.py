#!/usr/bin/env python3
"""Deploy BridgedUSDT using py-solc-x (no solc binary needed)."""
import os, sys, json
from pathlib import Path

from eth_account import Account
from solcx import compile_files, install_solc, set_solc_version
from web3 import Web3

RPC    = os.getenv("USST_RPC", "http://127.0.0.1:8545")
KEY    = os.getenv("USST_DEPLOYER_KEY", "")
CHAIN    = 778889
OPERATOR = os.getenv("BRIDGE_OPERATOR_ADDRESS", "")

if not KEY:
    sys.exit("USST_DEPLOYER_KEY not set")
if not OPERATOR:
    # Derive operator address from operator key if provided
    op_key = os.getenv("BRIDGE_OPERATOR_KEY", "")
    if op_key:
        OPERATOR = Account.from_key(op_key).address
    else:
        sys.exit("BRIDGE_OPERATOR_ADDRESS or BRIDGE_OPERATOR_KEY not set")

ROOT = Path(__file__).resolve().parents[1]
SOL  = ROOT / "contracts" / "BridgedUSDT.sol"

print("Installing solc 0.8.20...")
install_solc("0.8.20")
set_solc_version("0.8.20")

print("Compiling BridgedUSDT.sol...")
compiled = compile_files([str(SOL)], output_values=["abi", "bin"], solc_version="0.8.20", evm_version="paris")
abi, bytecode = None, None
for key, art in compiled.items():
    if "BridgedUSDT" in key:
        abi, bytecode = art["abi"], art["bin"]
        break
if not bytecode:
    sys.exit("BridgedUSDT artifact not found")

w3 = Web3(Web3.HTTPProvider(RPC))
if not w3.is_connected():
    sys.exit(f"Cannot connect to {RPC}")

acct  = Account.from_key(KEY)
nonce = w3.eth.get_transaction_count(acct.address)
contract = w3.eth.contract(abi=abi, bytecode=bytecode)

print(f"Deploying from {acct.address} (nonce={nonce}), operator={OPERATOR}...")
tx = contract.constructor(OPERATOR).build_transaction({
    "from": acct.address,
    "nonce": nonce,
    "chainId": CHAIN,
    "gasPrice": w3.eth.gas_price,
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
if receipt.status != 1:
    sys.exit("Deployment failed")

addr = receipt.contractAddress
print(f"\nBridgedUSDT deployed: {addr}")
print(f"Update in .env: BRIDGED_USDT_ADDRESS={addr}")
