#!/usr/bin/env python3
"""Generate a new miner wallet for a worker machine."""

from eth_account import Account

account = Account.create()
print("New miner wallet for this computer:")
print(f"  Address:     {account.address}")
print(f"  Private key: 0x{account.key.hex()}")
print()
print("Add to .env on this machine:")
print(f"  USST_MINER_KEY=0x{account.key.hex()}")
print()
print("Then fund it for gas (on the server):")
print(f"  python scripts/fund-miner.py {account.address}")
