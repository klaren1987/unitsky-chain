#!/usr/bin/env python3
"""Transfer bridge operator to a new secure address."""
import json, time, urllib.request, os
from eth_account import Account
from eth_hash.auto import keccak

RPC      = os.getenv("USST_RPC", "http://unitsky-string-node:8545")
OLD_KEY  = os.getenv("OLD_KEY")
NEW_ADDR = os.getenv("NEW_ADDR")
BUSDT    = os.getenv("BRIDGED_USDT_ADDRESS", "0xcd7cb25f025B20D5f90C0FDA3463D91AF76A8EF1")
CHAIN_ID = 778889

def rpc(method, params=[]):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return resp["result"]

acct = Account.from_key(OLD_KEY)
nonce = int(rpc("eth_getTransactionCount", [acct.address, "pending"]), 16)

# setOperator(address)
data = "0xb3ab15fb" + NEW_ADDR[2:].lower().zfill(64)
gas = int(int(rpc("eth_estimateGas", [{"from": acct.address, "to": BUSDT, "data": data}]), 16) * 1.2)
tx = {
    "nonce": nonce, "gasPrice": 10**9, "gas": int(gas),
    "to": BUSDT, "value": 0, "data": data, "chainId": CHAIN_ID
}
signed = acct.sign_transaction(tx)
raw = "0x" + signed.raw_transaction.hex()
tx_hash = rpc("eth_sendRawTransaction", [raw])
print(f"setOperator tx: {tx_hash}")

for _ in range(30):
    time.sleep(2)
    receipt = rpc("eth_getTransactionReceipt", [tx_hash])
    if receipt:
        status = receipt["status"]
        print(f"Status: {status}")
        if status == "0x1":
            print("SUCCESS — operator transferred!")
        else:
            print("FAILED!")
        break
