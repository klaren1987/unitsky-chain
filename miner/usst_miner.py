#!/usr/bin/env python3
"""
UST Network — UST Miner (GPU/CPU)

Proof-of-Work miner for the USSTMine smart contract.
Uses CUDA GPU by default; falls back to CPU with --cpu.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

from eth_account import Account
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from web3 import Web3

from miner.cpu_engine import CPUSearcher
from miner.gpu_engine import GPUSearcher, create_gpu_searcher, hash_work

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPLOYED = Path(os.getenv("USST_DEPLOYED_PATH", str(ROOT / "deployed.json")))

DEFAULT_MINER_KEY = os.getenv("USST_MINER_KEY", "")

USST_MINE_ABI = [
    {
        "inputs": [],
        "name": "difficulty",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "reward",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "poolBalance",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalMined",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "nonce", "type": "uint256"},
            {"name": "workBlock", "type": "uint256"},
        ],
        "name": "mine",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "miner", "type": "address"},
            {"name": "nonce", "type": "uint256"},
            {"name": "workBlock", "type": "uint256"},
        ],
        "name": "verifyWork",
        "outputs": [{"type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]

_POOL_POLL_INTERVAL = 30
_GPU_UI_INTERVAL = float(os.getenv("USST_GPU_UI_INTERVAL", "0.25"))
_GPU_BLOCK_CHECK_BATCHES = max(1, int(os.getenv("USST_GPU_BLOCK_CHECK_BATCHES", "16")))
# Contract allows 10 blocks; stop mining/submitting earlier to avoid stale proofs.
_WORK_BLOCK_MAX_AGE = max(1, int(os.getenv("USST_WORK_BLOCK_MAX_AGE", "8")))


def load_config(path: Path) -> dict:
    contract = os.getenv("USST_CONTRACT_ADDRESS")
    if contract:
        return {
            "network": "UST Network",
            "chainId": int(os.getenv("USST_CHAIN_ID", "778889")),
            "symbol": "UST",
            "rpcUrl": os.getenv("USST_RPC", "http://127.0.0.1:8545"),
            "contractAddress": contract,
        }

    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Set UST_CONTRACT_ADDRESS or run deploy on the server."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def create_searcher(force_cpu: bool):
    if force_cpu:
        return CPUSearcher()
    if os.getenv("USST_GPU", "1") == "0":
        return CPUSearcher()
    try:
        return create_gpu_searcher()
    except Exception as exc:
        if os.getenv("USST_GPU_REQUIRED") == "1":
            raise
        Console().print(f"[yellow]GPU unavailable ({exc}), falling back to CPU[/yellow]")
        return CPUSearcher()


def build_status(
    miner_addr: str,
    work_block: int,
    difficulty: int,
    reward_wei: int,
    pool_wei: int,
    total_mined: int,
    session_hashes: int,
    blocks_found: int,
    hashrate: float,
    current_nonce: int,
    device: str,
) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Network", "UST Network")
    table.add_row("Symbol", "UST")
    table.add_row("Device", device)
    table.add_row("Miner", miner_addr)
    table.add_row("Work block", str(work_block))
    table.add_row("Difficulty", f"{difficulty:,}")
    table.add_row("Reward", f"{Web3.from_wei(reward_wei, 'ether')} UST")
    table.add_row("Pool", f"{Web3.from_wei(pool_wei, 'ether')} UST")
    table.add_row("Total mined", str(total_mined))
    table.add_row("Session hashes", f"{session_hashes:,}")
    table.add_row("Blocks found", str(blocks_found))
    mhs = hashrate / 1_000_000
    if mhs >= 1:
        hr_str = f"{mhs:,.2f} MH/s"
    elif hashrate >= 1000:
        hr_str = f"{hashrate / 1000:,.1f} KH/s"
    else:
        hr_str = f"{hashrate:,.0f} H/s"
    table.add_row("Hashrate", hr_str)
    table.add_row("Current nonce", f"{current_nonce:,}")
    return table


def work_block_stale(w3: Web3, work_block: int) -> bool:
    return w3.eth.block_number - work_block > _WORK_BLOCK_MAX_AGE


def _gas_price_with_buffer(w3: Web3) -> int:
    """Gas price with a 20 % buffer to avoid underpriced-tx rejections."""
    base = w3.eth.gas_price
    return max(base * 6 // 5, 1_000_000_000)  # +20%, minimum 1 gwei


def submit_mine_sync(
    w3: Web3,
    miner: Account,
    contract,
    chain_id: int,
    pow_nonce: int,
    work_block: int,
    console: Console,
    *,
    max_retries: int = 2,
) -> bool:
    """Submit mine() synchronously after final on-chain checks."""
    if work_block_stale(w3, work_block):
        console.print(
            f"[yellow]Skipping stale workBlock {work_block} "
            f"(chain head {w3.eth.block_number})[/yellow]"
        )
        return False

    if not contract.functions.verifyWork(miner.address, pow_nonce, work_block).call():
        console.print("[yellow]verifyWork failed before submit, continuing…[/yellow]")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            tx = contract.functions.mine(pow_nonce, work_block).build_transaction(
                {
                    "from": miner.address,
                    "nonce": w3.eth.get_transaction_count(miner.address, "pending"),
                    "chainId": chain_id,
                    "gas": 200_000,
                    "gasPrice": _gas_price_with_buffer(w3),
                }
            )
            signed = miner.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            break
        except Exception as exc:
            err_str = str(exc).lower()
            if "insufficient funds" in err_str or "insufficient balance" in err_str:
                console.print(
                    f"[bold red]✗ Insufficient gas:[/bold red] wallet {miner.address} "
                    f"has {Web3.from_wei(w3.eth.get_balance(miner.address), 'ether')} UST — "
                    f"need at least 0.0002 UST to pay gas.\n"
                    f"  Get free UST at the faucet: https://147-45-143-23.sslip.io/faucet"
                )
                return False
            console.print(f"[red]Transaction error (attempt {attempt}/{max_retries}): {exc}[/red]")
            if attempt == max_retries:
                return False
            time.sleep(1)

    if receipt.status != 1:
        console.print("[yellow]Transaction reverted, continuing…[/yellow]")
        return False

    reward = contract.functions.reward().call()
    console.print(
        f"[green]Mined![/green] nonce={pow_nonce} "
        f"reward={Web3.from_wei(reward, 'ether')} UST "
        f"tx={tx_hash.hex()}"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="UST Network UST Miner")
    parser.add_argument("--rpc", default=os.getenv("USST_RPC", "http://127.0.0.1:8545"))
    parser.add_argument("--deployed", type=Path, default=DEFAULT_DEPLOYED)
    parser.add_argument(
        "--private-key",
        default=os.getenv("USST_MINER_KEY", DEFAULT_MINER_KEY),
        help="Miner wallet private key (receives UST rewards)",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU mining (disable GPU)",
    )
    args = parser.parse_args()

    console = Console()
    config = load_config(args.deployed)
    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        console.print("[red]Cannot connect to RPC. Start node: docker compose up -d[/red]")
        return 1

    if not args.private_key:
        console.print("[red]USST_MINER_KEY env var or --private-key is required[/red]")
        return 1
    miner = Account.from_key(args.private_key)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(config["contractAddress"]),
        abi=USST_MINE_ABI,
    )

    searcher = create_searcher(args.cpu)
    device_label = getattr(searcher, "device_name", "CPU")
    gpu_mode = isinstance(searcher, GPUSearcher)
    if gpu_mode:
        device_label = (
            f"{searcher.device_name} "
            f"(batch={searcher.batch_size:,}, streams={searcher.stream_count})"
        )

    console.print(
        Panel.fit(
            "[bold magenta]UST Network[/bold magenta]\n"
            f"[bold]UST Miner[/bold] — Proof of Work ({device_label})\n"
            f"RPC: {args.rpc}",
            border_style="magenta",
        )
    )

    # Pre-flight: warn if wallet balance is below 1 transaction worth of gas.
    _GAS_MIN_WEI = 1_000_000_000 * 200_000  # 200 000 gas @ 1 gwei = 0.0002 UST
    balance = w3.eth.get_balance(miner.address)
    if balance < _GAS_MIN_WEI:
        console.print(
            f"[bold yellow]⚠  Low gas balance:[/bold yellow] {miner.address} "
            f"has {Web3.from_wei(balance, 'ether')} UST — not enough to submit transactions.\n"
            f"   Get free gas at the faucet: https://147-45-143-23.sslip.io/faucet\n"
            f"   Enter your address and receive 0.01 UST instantly (enough for ~200 transactions)."
        )

    session_hashes = 0
    blocks_found = 0
    nonce = random.randint(0, 2**48)
    t0 = time.monotonic()

    with Live(console=console, refresh_per_second=4) as live:
        while True:
            # Wait for pool to be funded before doing any work.
            reward = contract.functions.reward().call()
            pool = contract.functions.poolBalance().call()
            while pool < reward:
                live.update(
                    Panel(
                        f"[yellow]Mining pool empty (pool={Web3.from_wei(pool, 'ether')} UST, "
                        f"reward={Web3.from_wei(reward, 'ether')} UST).\n"
                        f"If reward shows 1 UST you are on the OLD contract — update USST_CONTRACT_ADDRESS to "
                        f"0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0 in .env.miner\n"
                        f"Retrying in {_POOL_POLL_INTERVAL}s…[/yellow]",
                        title="UST Miner — paused",
                        border_style="yellow",
                    )
                )
                time.sleep(_POOL_POLL_INTERVAL)
                reward = contract.functions.reward().call()
                pool = contract.functions.poolBalance().call()

            work_block = w3.eth.block_number
            difficulty = contract.functions.difficulty().call()
            target = (2**256 - 1) // difficulty
            total = contract.functions.totalMined().call()

            # Randomize nonce on each new work block so parallel miners
            # don't duplicate effort and to keep nonces in a sane range.
            nonce = random.randint(0, 2**48)

            found_nonce = None
            batches_since_block_check = 0
            last_ui = 0.0
            while found_nonce is None:
                candidate, tried = searcher.search(miner.address, work_block, target, nonce)
                nonce += tried
                session_hashes += tried
                batches_since_block_check += 1

                if candidate is not None:
                    found_nonce = candidate
                    break

                now = time.monotonic()
                update_ui = (not gpu_mode) or (now - last_ui >= _GPU_UI_INTERVAL)
                check_block = batches_since_block_check >= _GPU_BLOCK_CHECK_BATCHES

                if update_ui or check_block:
                    if update_ui:
                        elapsed = now - t0
                        hashrate = session_hashes / elapsed if elapsed > 0 else 0
                        live.update(
                            Panel(
                                build_status(
                                    miner.address,
                                    work_block,
                                    difficulty,
                                    reward,
                                    pool,
                                    total,
                                    session_hashes,
                                    blocks_found,
                                    hashrate,
                                    nonce,
                                    device_label,
                                ),
                                title="Mining…",
                                border_style="green",
                            )
                        )
                        last_ui = now

                    if check_block:
                        batches_since_block_check = 0
                        if work_block_stale(w3, work_block):
                            work_block = w3.eth.block_number
                            break

            if found_nonce is None:
                continue

            if submit_mine_sync(
                w3, miner, contract, config["chainId"], found_nonce, work_block, live.console
            ):
                blocks_found += 1
                pool = contract.functions.poolBalance().call()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nMiner stopped.")
        sys.exit(0)
