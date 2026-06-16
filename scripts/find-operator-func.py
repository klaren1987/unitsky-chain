import json, urllib.request
from eth_hash.auto import keccak

RPC = "http://unitsky-string-node:8545"
BUSDT = "0xcd7cb25f025B20D5f90C0FDA3463D91AF76A8EF1"
OLD = "0xa952D52c043A9C5901d28a542AAb355b2Ad4BbEC"
NEW = "0x36792aCCf6B72Ed07879CdE08bf602Ee045F7721"

def rpc_call(method, params=[]):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=10).read())

funcs = [
    "setOperator(address)",
    "transferOwnership(address)",
    "updateOperator(address)",
    "changeOperator(address)",
    "setBridgeOperator(address)",
    "setAdmin(address)",
]
for f in funcs:
    sel = "0x" + keccak(f.encode()).hex()[:8]
    data = sel + NEW[2:].lower().zfill(64)
    resp = rpc_call("eth_estimateGas", [{"from": OLD, "to": BUSDT, "data": data}])
    if "result" in resp:
        print(f"WORKS: {f} (gas={int(resp['result'],16)})")
    else:
        print(f"FAIL:  {f} - {resp.get('error',{}).get('message','')}")
