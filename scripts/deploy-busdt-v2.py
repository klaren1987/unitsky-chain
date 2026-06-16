#!/usr/bin/env python3
"""Deploy BridgedUSDT and transfer operator. Simpler version."""
import json, time, urllib.request, sys, os
from pathlib import Path
from eth_account import Account
from eth_utils import to_checksum_address
from eth_hash.auto import keccak
from solcx import compile_files, install_solc, set_solc_version

RPC      = os.getenv("USST_RPC", "http://unitsky-string-node:8545")
CHAIN_ID = 778889
KEY      = os.getenv("USST_DEPLOYER_KEY", "")
OP_KEY   = os.getenv("BRIDGE_OPERATOR_KEY", "")

if not KEY or not OP_KEY:
    sys.exit("USST_DEPLOYER_KEY and BRIDGE_OPERATOR_KEY required")

deployer  = Account.from_key(KEY)
bridge_op = Account.from_key(OP_KEY)

def rpc(m, p=[]):
    body = json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in resp: raise RuntimeError(str(resp["error"]))
    return resp["result"]

def send(key, to=None, data="0x", value=0, gas=2_000_000):
    acct = Account.from_key(key)
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "pending"]), 16)
    tx = {"nonce": nonce, "gasPrice": 10**9, "gas": gas, "value": value, "data": data, "chainId": CHAIN_ID}
    if to: tx["to"] = to_checksum_address(to)
    signed = acct.sign_transaction(tx)
    return rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])

def wait(txh):
    for _ in range(60):
        time.sleep(2)
        try:
            r = rpc("eth_getTransactionReceipt", [txh])
            if r: return r
        except: pass
    return None

print("Deployer:", deployer.address)
print("BridgeOp:", bridge_op.address)

# Compile
print("\nCompiling BridgedUSDT...")
install_solc("0.8.20"); set_solc_version("0.8.20")
compiled = compile_files(["/app/contracts/BridgedUSDT.sol"], output_values=["abi", "bin"], evm_version="paris")
bytecode = None
for k, v in compiled.items():
    if ":BridgedUSDT" in k:
        bytecode = v["bin"]
        break
if not bytecode: sys.exit("BridgedUSDT not found in compiled")
print(f"  Bytecode: {len(bytecode)//2} bytes")

# Deploy: constructor(address _operator) with deployer as operator
args = "000000000000000000000000" + deployer.address[2:].lower()
fullbc = "0x" + bytecode + args
print("\nDeploying...")
txh = send(KEY, data=fullbc)
print(f"  TX: {txh}")
receipt = wait(txh)
if not receipt:
    sys.exit("Timeout waiting for receipt")
status = int(receipt.get("status", "0x0"), 16)
contract_addr = receipt.get("contractAddress")
print(f"  Status: {status} | Address: {contract_addr}")
if status != 1:
    sys.exit(f"Deployment failed, status={status}")

print(f"\nBridgedUSDT deployed: {contract_addr}")

# Transfer operator to bridge_op
print(f"\nTransfer operator → {bridge_op.address}")
sel = keccak(b"transferOperator(address)").hex()[:8]
data = "0x" + sel + bridge_op.address[2:].lower().zfill(64)
txh = send(KEY, to=contract_addr, data=data)
r = wait(txh)
print(f"  transferOperator: {int(r['status'], 16) if r else 'timeout'}")

sel2 = keccak(b"acceptOperator()").hex()[:8]
txh = send(OP_KEY, to=contract_addr, data="0x" + sel2)
r = wait(txh)
print(f"  acceptOperator: {int(r['status'], 16) if r else 'timeout'}")

# Verify
sel3 = keccak(b"operator()").hex()[:8]
result = rpc("eth_call", [{"to": contract_addr, "data": "0x" + sel3}, "latest"])
actual_op = "0x" + result[-40:]
print(f"\nOperator verified: {actual_op}")
print(f"Expected:          {bridge_op.address.lower()}")

print(f"\n{'='*50}")
print(f"BRIDGED_USDT_ADDRESS={contract_addr}")
print(f"{'='*50}")
Path("/tmp/busdt-addr.txt").write_text(contract_addr)
