#!/usr/bin/env python3
"""Two-step bridge operator transfer on Chain 778889."""
import json, time, urllib.request, os
from eth_account import Account
from eth_hash.auto import keccak

RPC      = "http://unitsky-string-node:8545"
OLD_KEY  = os.getenv("OLD_KEY")
NEW_KEY  = os.getenv("NEW_KEY")
BUSDT    = os.getenv("BRIDGED_USDT_ADDRESS", "0xcd7cb25f025B20D5f90C0FDA3463D91AF76A8EF1")
CHAIN_ID = 778889

old_acct = Account.from_key(OLD_KEY)
new_acct = Account.from_key(NEW_KEY)
print(f"Old operator: {old_acct.address}")
print(f"New operator: {new_acct.address}")

def rpc(method, params=[]):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in resp:
        raise RuntimeError(f"{method} error: {resp['error']}")
    return resp["result"]

def send_tx(key, to, data, value=0):
    acct = Account.from_key(key)
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "pending"]), 16)
    gas = int(int(rpc("eth_estimateGas", [{"from": acct.address, "to": to, "data": data, "value": hex(value)}]), 16) * 1.2)
    tx = {
        "nonce": nonce, "gasPrice": 10**9, "gas": int(gas),
        "to": to, "value": value, "data": data, "chainId": CHAIN_ID
    }
    signed = acct.sign_transaction(tx)
    raw = "0x" + signed.raw_transaction.hex()
    tx_hash = rpc("eth_sendRawTransaction", [raw])
    print(f"  tx: {tx_hash}")
    for _ in range(30):
        time.sleep(2)
        receipt = rpc("eth_getTransactionReceipt", [tx_hash])
        if receipt:
            if receipt["status"] == "0x1":
                return receipt
            raise RuntimeError(f"TX FAILED: {tx_hash}")
    raise TimeoutError(f"Timeout: {tx_hash}")

# Step 0: Send some UST to new address for gas
print("\n[0] Sending 1 UST to new operator for gas...")
receipt = send_tx(OLD_KEY, new_acct.address, "0x", value=1 * 10**18)
print("  Gas funded")

# Step 1: transferOperator(newAddress) from old operator
print(f"\n[1] transferOperator({new_acct.address})...")
sel = "0x" + keccak(b"transferOperator(address)").hex()[:8]
data = sel + new_acct.address[2:].lower().zfill(64)
send_tx(OLD_KEY, BUSDT, data)
print("  Pending operator set")

# Step 2: acceptOperator() from new operator
print(f"\n[2] acceptOperator() from {new_acct.address}...")
sel2 = "0x" + keccak(b"acceptOperator()").hex()[:8]
send_tx(NEW_KEY, BUSDT, sel2)
print("  Operator transferred!")

# Verify
sel_op = "0x" + keccak(b"operator()").hex()[:8]
result = rpc("eth_call", [{"to": BUSDT, "data": sel_op}, "latest"])
current_op = "0x" + result[-40:]
print(f"\n✅ Current operator: {current_op}")
print(f"   Expected:          {new_acct.address.lower()}")
assert current_op.lower() == new_acct.address.lower(), "Operator mismatch!"
print("\n✅ SUCCESS — operator transferred securely!")
