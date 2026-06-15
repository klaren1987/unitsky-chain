#!/usr/bin/env python3
"""
Migrate UST treasury to a new private key.

The Clique SIGNER key (0xf39F...) cannot be changed without resetting the chain —
it is baked into genesis.json extradata. However, the DEPLOYER/TREASURY key can
and MUST be replaced if it was set to the well-known Hardhat default.

This script:
  1. Generates a new deployer key (or accepts one via --new-key).
  2. Transfers all ETH from the old deployer address to the new one.
  3. Prints updated .env values to paste.

After running:
  - Update .env: set USST_DEPLOYER_KEY=<new key>
  - Run: docker compose -f docker-compose.windows-node.yml up -d  (restart to reload)
  - The Clique SIGNER_KEY stays the same (needed for Clique consensus).

Usage:
    python scripts/migrate-keys.py
    python scripts/migrate-keys.py --new-key 0xYOUR_EXISTING_KEY
    python scripts/migrate-keys.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

from eth_account import Account
from web3 import Web3

RPC_URL = os.getenv("USST_RPC", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("USST_CHAIN_ID", "778889"))
OLD_DEPLOYER_KEY = os.getenv("USST_DEPLOYER_KEY", "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate UST treasury key")
    parser.add_argument("--new-key", help="New private key (0x...). Generated if omitted.")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    args = parser.parse_args()

    if not OLD_DEPLOYER_KEY:
        print("Set USST_DEPLOYER_KEY in .env before running.", file=sys.stderr)
        return 1

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Cannot connect to {RPC_URL}. Start node first.", file=sys.stderr)
        return 1

    old_acc = Account.from_key(OLD_DEPLOYER_KEY)
    balance = w3.eth.get_balance(old_acc.address)
    print(f"Old deployer  : {old_acc.address}")
    print(f"Balance       : {Web3.from_wei(balance, 'ether')} UST")

    # Generate or load new key
    if args.new_key:
        new_acc = Account.from_key(args.new_key)
        print(f"New deployer  : {new_acc.address} (provided)")
    else:
        new_acc = Account.create()
        print(f"New deployer  : {new_acc.address} (generated)")
        print(f"New key       : 0x{new_acc.key.hex()}")

    if old_acc.address.lower() == new_acc.address.lower():
        print("Old and new keys are the same — nothing to migrate.")
        return 0

    gas_price = w3.eth.gas_price
    gas_limit = 21_000
    fee = gas_price * gas_limit
    transfer_amount = balance - fee

    if transfer_amount <= 0:
        print(f"Insufficient balance to cover gas ({Web3.from_wei(fee, 'ether')} UST)")
        return 1

    print(f"\nPlan:")
    print(f"  Transfer {Web3.from_wei(transfer_amount, 'ether')} UST -> {new_acc.address}")
    print(f"  Gas fee : {Web3.from_wei(fee, 'ether')} UST")

    if args.dry_run:
        print("\n[dry-run] Skipping actual transfer.")
    else:
        confirm = input("\nProceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

        nonce = w3.eth.get_transaction_count(old_acc.address)
        tx = {
            "from": old_acc.address,
            "to": new_acc.address,
            "value": transfer_amount,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "gas": gas_limit,
            "gasPrice": gas_price,
        }
        signed = old_acc.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            print("Transfer FAILED")
            return 1

        new_balance = w3.eth.get_balance(new_acc.address)
        print(f"\nTransfer complete: {tx_hash.hex()}")
        print(f"New deployer balance: {Web3.from_wei(new_balance, 'ether')} UST")

    print("\n" + "=" * 60)
    print("Update your .env with:")
    print("=" * 60)
    print(f"USST_DEPLOYER_KEY=0x{new_acc.key.hex()}")
    print("=" * 60)
    print("\nNOTE: USST_SIGNER_KEY must remain unchanged (Clique consensus).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
