#!/usr/bin/env python3
"""Send USST to a miner wallet for transaction gas."""

from __future__ import annotations

import os
import sys

from eth_account import Account
from web3 import Web3

RPC_URL = os.getenv("USST_RPC", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("USST_CHAIN_ID", "778889"))
DEPLOYER_KEY = os.getenv("USST_DEPLOYER_KEY", "")
if not DEPLOYER_KEY:
    sys.exit("USST_DEPLOYER_KEY environment variable is required")
GAS_FUND_ETHER = float(os.getenv("USST_GAS_FUND_ETHER", "10"))


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <miner_address>")
        return 1

    recipient = Web3.to_checksum_address(sys.argv[1])
    amount = Web3.to_wei(GAS_FUND_ETHER, "ether")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Cannot connect to {RPC_URL}")
        return 1

    deployer = Account.from_key(DEPLOYER_KEY)
    tx = {
        "from": deployer.address,
        "to": recipient,
        "value": amount,
        "nonce": w3.eth.get_transaction_count(deployer.address),
        "chainId": CHAIN_ID,
        "gas": 21_000,
        "gasPrice": w3.eth.gas_price,
    }
    signed = deployer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        print("Transfer failed")
        return 1

    print(f"Sent {GAS_FUND_ETHER} UST to {recipient}")
    print(f"tx: {tx_hash.hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
