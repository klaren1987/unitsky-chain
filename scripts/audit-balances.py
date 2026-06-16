#!/usr/bin/env python3
import json, urllib.request, os

RPC = os.getenv("USST_RPC", "http://unitsky-string-node:8545")

def rpc(m, p=[]):
    body = json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=10).read())["result"]

wallets = [
    ("Signer",         "0xcA17e661e964DC345130F91b0b5258fCa7eA3678"),
    ("Deployer",       "0x83e53AF59DA384800e25e30878AB7408CA1AfFe3"),
    ("Miner",          "0xdAaF67646FE057CaA5b210fB8A6B5CD78FEb69B3"),
    ("Faucet",         "0x410ba9AF695161523D41B1E4C9293558b83944B7"),
    ("BridgeTreasury", "0x36792aCCf6B72Ed07879CdE08bf602Ee045F7721"),
    ("USSTMine",       "0x6799cd720d6b1fbe4739ee25407552df96ad0314"),
    ("BridgedUSDT",    "0xcc96158a84d2821fbae89593c33f9e244964d189"),
]

print("  Role               Address                                     Balance (UST)")
print("  " + "-"*78)
for role, addr in wallets:
    wei = int(rpc("eth_getBalance", [addr, "latest"]), 16)
    ust = wei / 1e18
    print("  %-18s  %s  %12.2f UST" % (role, addr, ust))

bn = int(rpc("eth_blockNumber"), 16)
print("\n  Chain block: %d" % bn)
print("\n  Contracts:")
for label, addr in [("USSTMine", "0x6799cd720d6b1fbe4739ee25407552df96ad0314"),
                     ("BridgedUSDT", "0xcc96158a84d2821fbae89593c33f9e244964d189")]:
    code = rpc("eth_getCode", [addr, "latest"])
    print("  %-18s  %s  code=%d bytes" % (label, addr, len(code)//2 - 1))
