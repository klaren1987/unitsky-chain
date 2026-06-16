#!/usr/bin/env python3
"""Deploy USSTMine contract to UST Network network."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from eth_account import Account
from solcx import compile_files, install_solc, set_solc_version
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "USSTMine.sol"
DEPLOYED = Path(os.getenv("USST_DEPLOYED_PATH", str(ROOT / "deployed.json")))

RPC_URL = os.getenv("USST_RPC", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("USST_CHAIN_ID", "778889"))
DEPLOYER_KEY = os.getenv("USST_DEPLOYER_KEY", "")
if not DEPLOYER_KEY:
    sys.exit("USST_DEPLOYER_KEY environment variable is required")
FUND_WEI = Web3.to_wei(int(os.getenv("USST_FUND_ETHER", "10000")), "ether")


def compile_contract() -> tuple[list[str], str]:
    install_solc("0.8.20")
    set_solc_version("0.8.20")
    compiled = compile_files(
        [str(CONTRACT)],
        output_values=["abi", "bin"],
        solc_version="0.8.20",
        evm_version="paris",
    )
    for key, artifact in compiled.items():
        if key.endswith(":USSTMine"):
            return artifact["abi"], artifact["bin"]
    raise RuntimeError("USSTMine artifact not found")


def main() -> int:
    if DEPLOYED.exists():
        print(f"Already deployed: {DEPLOYED}")
        print(DEPLOYED.read_text(encoding="utf-8"))
        return 0

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Cannot connect to node at {RPC_URL}. Start chain: docker compose up -d")
        return 1

    chain_id = w3.eth.chain_id
    if chain_id != CHAIN_ID:
        print(f"Unexpected chain id {chain_id}, expected {CHAIN_ID}")
        return 1

    abi, bytecode = compile_contract()
    deployer = Account.from_key(DEPLOYER_KEY)

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer.address)

    tx = contract.constructor(0).build_transaction(
        {
            "from": deployer.address,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "value": FUND_WEI,
            "gasPrice": w3.eth.gas_price,
        }
    )
    tx["gas"] = w3.eth.estimate_gas(tx) + 50_000
    signed = deployer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        print("Deployment failed")
        return 1

    address = receipt.contractAddress
    info = {
        "network": "UST Network",
        "chainId": CHAIN_ID,
        "symbol": "UST",
        "rpcUrl": RPC_URL,
        "contractAddress": address,
        "deployer": deployer.address,
        "fundedWei": str(FUND_WEI),
    }

    DEPLOYED.parent.mkdir(parents=True, exist_ok=True)
    DEPLOYED.write_text(json.dumps(info, indent=2), encoding="utf-8")

    print(f"USSTMine deployed: {address}")
    print(f"Pool funded with {Web3.from_wei(FUND_WEI, 'ether')} UST")
    print(f"Saved to {DEPLOYED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
