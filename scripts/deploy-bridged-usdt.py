#!/usr/bin/env python3
"""
Deploy BridgedUSDT.sol to Chain 778889 and update .env.miner with the address.

Usage:
    python scripts/deploy-bridged-usdt.py

Requires: USST_DEPLOYER_KEY in environment (same key used to deploy USSTMine).
"""
import os, sys, json, subprocess, urllib.request, time

RPC    = os.getenv("USST_RPC", "http://127.0.0.1:8545")
KEY    = os.getenv("USST_DEPLOYER_KEY", "")
CHAIN  = 778889

if not KEY:
    print("ERROR: USST_DEPLOYER_KEY not set")
    sys.exit(1)

from eth_account import Account
from eth_account.signers.local import LocalAccount

def rpc_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req  = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=10).read())["result"]

def deploy(bytecode, abi, constructor_args_hex=""):
    acct: LocalAccount = Account.from_key(KEY)
    nonce    = int(rpc_call("eth_getTransactionCount", [acct.address, "pending"]), 16)
    gas_price = max(int(rpc_call("eth_gasPrice", []), 16), 10**9)
    data = bytecode + constructor_args_hex

    # Estimate gas
    gas = int(rpc_call("eth_estimateGas", [{"from": acct.address, "data": data}]), 16)
    gas = int(gas * 1.2)

    tx = {
        "nonce":    nonce,
        "gasPrice": gas_price,
        "gas":      gas,
        "to":       None,
        "value":    0,
        "data":     data,
        "chainId":  CHAIN,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = rpc_call("eth_sendRawTransaction", [signed.raw_transaction.hex()])
    print(f"  Deploy tx: {tx_hash}")

    # Wait for receipt
    for _ in range(60):
        time.sleep(2)
        try:
            receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                if int(receipt["status"], 16) != 1:
                    print("  ERROR: Transaction reverted!")
                    sys.exit(1)
                return receipt["contractAddress"]
        except: pass
    print("  ERROR: Timeout waiting for receipt")
    sys.exit(1)


# ── Compile BridgedUSDT.sol ──────────────────────────────────────────────────
SOL_PATH = os.path.join(os.path.dirname(__file__), "..", "contracts", "BridgedUSDT.sol")
print("Compiling BridgedUSDT.sol …")
result = subprocess.run(
    ["solc", "--bin", "--abi", "--optimize", "--optimize-runs", "200", SOL_PATH],
    capture_output=True, text=True
)
if result.returncode != 0:
    # Try solc from PATH alternatives
    print("solc not found, trying py-solc-x …")
    try:
        import solcx
        solcx.install_solc("0.8.20")
        compiled = solcx.compile_files(
            [SOL_PATH],
            output_values=["abi", "bin"],
            optimize=True, optimize_runs=200,
            solc_version="0.8.20"
        )
        key = [k for k in compiled if "BridgedUSDT" in k][0]
        bytecode = "0x" + compiled[key]["bin"]
        abi      = compiled[key]["abi"]
    except Exception as e:
        print(f"ERROR: Cannot compile — install solc or py-solc-x: {e}")
        sys.exit(1)
else:
    lines    = result.stdout.split("\n")
    # Parse solc output
    abi_raw  = ""
    bin_raw  = ""
    for i, line in enumerate(lines):
        if "Binary:" in line:  bin_raw  = lines[i+1].strip()
        if "ABI"     in line:  abi_raw  = lines[i+1].strip()
    bytecode = "0x" + bin_raw
    abi      = json.loads(abi_raw)

# ── Constructor argument: operator = deployer ────────────────────────────────
acct = Account.from_key(KEY)
operator_hex = acct.address[2:].lower().zfill(64)   # padded to 32 bytes

print(f"Deployer (operator): {acct.address}")
print("Deploying BridgedUSDT …")
address = deploy(bytecode, abi, operator_hex)
print(f"\n✅  BridgedUSDT deployed at: {address}")
print(f"\nAdd to your .env files:")
print(f"  BRIDGED_USDT_ADDRESS={address}")
print(f"  BRIDGE_OPERATOR_KEY=<same as USST_DEPLOYER_KEY>")
print(f"\nNext step: run the bridge relayer:")
print(f"  python scripts/bridge-relayer.py")
