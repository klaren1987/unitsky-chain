#!/usr/bin/env python3
"""
Deploy BridgedUSDT contract, transfer operator, and run DEX deployment.
Run inside the deploy container: docker compose run deploy python scripts/deploy-busdt.py
"""
import os, sys, json, time, urllib.request
from pathlib import Path
from eth_account import Account
from eth_utils import to_checksum_address
from eth_hash.auto import keccak

try:
    from solcx import compile_files, install_solc, set_solc_version
except ImportError:
    os.system("pip install py-solc-x eth-abi -q")
    from solcx import compile_files, install_solc, set_solc_version

RPC           = os.getenv("USST_RPC", "http://unitsky-string-node:8545")
CHAIN_ID      = 778889
DEPLOYER_KEY  = os.getenv("USST_DEPLOYER_KEY", "")
BRIDGE_OP_KEY = os.getenv("BRIDGE_OPERATOR_KEY", "")

if not DEPLOYER_KEY or not BRIDGE_OP_KEY:
    sys.exit("USST_DEPLOYER_KEY and BRIDGE_OPERATOR_KEY are required")

deployer  = Account.from_key(DEPLOYER_KEY)
bridge_op = Account.from_key(BRIDGE_OP_KEY)

ROOT     = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "BridgedUSDT.sol"

print(f"Deployer:   {deployer.address}")
print(f"Bridge op:  {bridge_op.address}")

# ── RPC helpers ───────────────────────────────────────────────────────────────
def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    req  = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in resp:
        raise RuntimeError(f"{method}: {resp['error']}")
    return resp["result"]

def send_tx(key, to=None, data="0x", value=0, gas=None):
    acct  = Account.from_key(key)
    nonce = int(_rpc("eth_getTransactionCount", [acct.address, "pending"]), 16)
    gp    = max(int(_rpc("eth_gasPrice", []), 16), 10**9)
    tx = {"nonce": nonce, "gasPrice": gp,
          "value": value, "data": data, "chainId": CHAIN_ID}
    if to:
        tx["to"] = to_checksum_address(to)
    if gas is None:
        try:
            gas = int(_rpc("eth_estimateGas", [{"from": acct.address, **tx}]), 16) + 50_000
        except Exception:
            gas = 500_000
    tx["gas"] = gas
    signed = acct.sign_transaction(tx)
    return _rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])

def wait(tx_hash, label=""):
    print(f"  ⏳ {label} {tx_hash[:18]}…", end="", flush=True)
    for _ in range(60):
        time.sleep(2)
        try:
            r = _rpc("eth_getTransactionReceipt", [tx_hash])
            if r:
                status = int(r.get("status", "0x0"), 16)
                addr = r.get("contractAddress")
                print(" ✅" if status == 1 else " ❌ REVERTED")
                return addr, status == 1
        except Exception:
            pass
    print(" ⏰ timeout")
    return None, False

# ── Compile ───────────────────────────────────────────────────────────────────
print("\n[1/4] Compiling BridgedUSDT...")
install_solc("0.8.20")
set_solc_version("0.8.20")
compiled = compile_files(
    [str(CONTRACT)],
    output_values=["abi", "bin"],
    solc_version="0.8.20",
    evm_version="paris",
)
abi, bytecode = None, None
for key, artifact in compiled.items():
    if key.endswith(":BridgedUSDT"):
        abi      = artifact["abi"]
        bytecode = artifact["bin"]
        break
if not bytecode:
    sys.exit("BridgedUSDT artifact not found in compiled output")
print(f"  Bytecode size: {len(bytecode)//2} bytes")

# ── Deploy ────────────────────────────────────────────────────────────────────
print("\n[2/4] Deploying BridgedUSDT (initial operator = deployer)...")
# Encode constructor arg: address _operator = deployer.address (manual ABI encoding)
# ABI-encoded address: 12 bytes of zeros + 20-byte address
addr_hex = deployer.address[2:].lower()  # 40 hex chars
constructor_args = "0" * 24 + addr_hex   # 12 bytes zeros + 20 bytes addr = 32 bytes
full_bytecode = "0x" + bytecode + constructor_args

tx_hash = send_tx(DEPLOYER_KEY, data=full_bytecode)
contract_addr, ok = wait(tx_hash, "deploy BridgedUSDT")
if not ok or not contract_addr:
    # Try to get revert reason
    try:
        debug = _rpc("debug_traceTransaction", [tx_hash, {}])
        print(f"  Debug: {debug}")
    except Exception as e:
        print(f"  Debug error: {e}")
    sys.exit("BridgedUSDT deployment failed")
print(f"  BridgedUSDT deployed at: {contract_addr}")

# ── Transfer operator to bridge operator key ──────────────────────────────────
print(f"\n[3/4] Transferring operator from deployer → bridge op {bridge_op.address}...")

# transferOperator(address)
sel = keccak(b"transferOperator(address)").hex()[:8]
data = "0x" + sel + bridge_op.address[2:].lower().zfill(64)
tx_hash = send_tx(DEPLOYER_KEY, to=contract_addr, data=data)
wait(tx_hash, "transferOperator")

# acceptOperator()
sel2 = keccak(b"acceptOperator()").hex()[:8]
tx_hash = send_tx(BRIDGE_OP_KEY, to=contract_addr, data="0x" + sel2)
wait(tx_hash, "acceptOperator")

# Verify operator
sel3 = keccak(b"operator()").hex()[:8]
result = _rpc("eth_call", [{"to": contract_addr, "data": "0x" + sel3}, "latest"])
actual_op = "0x" + result[-40:]
print(f"  Verified operator: {actual_op}")
if actual_op.lower() != bridge_op.address.lower():
    print("  ⚠️  Operator mismatch!")
else:
    print("  ✅ Operator set correctly")

# ── Save result ───────────────────────────────────────────────────────────────
print("\n[4/4] Saving contract addresses...")
result = {
    "BRIDGED_USDT_ADDRESS": contract_addr,
    "bridge_operator": bridge_op.address,
}
print(json.dumps(result, indent=2))

# Write to a file for the shell to pick up
Path("/tmp/busdt-deploy.json").write_text(json.dumps(result, indent=2))
print(f"\nAdd to .env:  BRIDGED_USDT_ADDRESS={contract_addr}")
