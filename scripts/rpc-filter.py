#!/usr/bin/env python3
"""
JSON-RPC filter proxy — blocks dangerous methods before they reach Geth.

HTTP  :8547  ->  Geth :8545
WS    :8548  ->  Geth :8546
POST  :8547/faucet  ->  auto-send USST_FAUCET_AMOUNT UST to new wallets

Blocked methods prevent external callers from:
  - eth_sendTransaction  : sending txs as an unlocked account (treasury drain)
  - eth_sign             : arbitrary message signing with unlocked account
  - personal_*           : account management
  - admin_*              : node administration
  - miner_*              : miner control
  - debug_setHead        : chain manipulation
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

GETH_URL = os.getenv("GETH_URL", "http://unitsky-string-node:8545")
GETH_WS_URL = os.getenv("GETH_WS_URL", "ws://unitsky-string-node:8546")
LISTEN_PORT = int(os.getenv("RPC_FILTER_PORT", "8547"))
LISTEN_WS_PORT = int(os.getenv("RPC_FILTER_WS_PORT", "8548"))
CHAIN_ID = int(os.getenv("USST_CHAIN_ID", "778889"))

# Rate limiting: max requests per IP per window
# Default: 600 req / 10 s = 60 req/s — enough for browser + MetaMask,
# blocks only aggressive scripts / scrapers.
RATE_LIMIT = int(os.getenv("RPC_RATE_LIMIT", "600"))
RATE_WINDOW = int(os.getenv("RPC_RATE_WINDOW", "10"))  # seconds

_rate_lock = threading.Lock()
_rate_counts: dict[str, list[float]] = defaultdict(list)

# ─── Faucet ───────────────────────────────────────────────────────────────────

FAUCET_KEY = os.getenv("USST_FAUCET_KEY", "")
# Amount to drip per claim (default 0.01 UST — enough for ~200 transactions)
FAUCET_AMOUNT_WEI = int(float(os.getenv("USST_FAUCET_AMOUNT", "0.01")) * 10**18)
# Cooldown: one claim per address per N seconds (default 24 h)
FAUCET_COOLDOWN = int(os.getenv("USST_FAUCET_COOLDOWN", str(24 * 3600)))
# Max balance to qualify: addresses with more than this amount are rejected
FAUCET_MAX_BALANCE_WEI = int(float(os.getenv("USST_FAUCET_MAX_BALANCE", "0.1")) * 10**18)
# IP cooldown: same IP can only trigger N claims per window
FAUCET_IP_LIMIT = int(os.getenv("USST_FAUCET_IP_LIMIT", "5"))

_faucet_lock = threading.Lock()
_faucet_addr_last: dict[str, float] = {}   # address.lower() -> last claim timestamp
_faucet_ip_times: dict[str, list[float]] = defaultdict(list)  # ip -> list of timestamps


def _faucet_enabled() -> bool:
    return bool(FAUCET_KEY)


def _eth_call(method: str, params: list) -> object:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        GETH_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["result"]


def _faucet_send(to_address: str) -> str:
    """Sign and broadcast a native UST transfer. Returns tx hash."""
    from eth_account import Account  # lazy import — only needed when faucet is enabled
    from eth_utils import to_checksum_address  # normalize address

    faucet = Account.from_key(FAUCET_KEY)
    to_address = to_checksum_address(to_address)

    nonce_hex = _eth_call("eth_getTransactionCount", [faucet.address, "pending"])
    nonce = int(nonce_hex, 16)
    gas_price_hex = _eth_call("eth_gasPrice", [])
    gas_price = max(int(gas_price_hex, 16) * 6 // 5, 10**9)  # +20%, min 1 gwei

    tx = {
        "to": to_address,
        "value": FAUCET_AMOUNT_WEI,
        "gas": 21_000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID,
    }
    signed = faucet.sign_transaction(tx)
    raw_hex = signed.raw_transaction.hex()
    result = _eth_call("eth_sendRawTransaction", ["0x" + raw_hex])
    return result  # tx hash


def handle_faucet(raw_body: bytes, client_ip: str) -> tuple[int, dict]:
    """Process a faucet claim. Returns (http_status, response_dict)."""
    if not _faucet_enabled():
        return 503, {"error": "Faucet is not configured on this server."}

    try:
        req = json.loads(raw_body)
        address = req.get("address", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return 400, {"error": "Invalid JSON. Send {\"address\": \"0x...\"}"}

    if not address or len(address) != 42 or not address.startswith("0x"):
        return 400, {"error": "Invalid Ethereum address."}

    # Honeypot anti-bot check: legitimate browsers always send _hp="", bots fill it
    if req.get("_hp", "") != "":
        return 400, {"error": "Invalid request."}
    address_lc = address.lower()

    now = time.monotonic()

    with _faucet_lock:
        # IP rate limit
        _faucet_ip_times[client_ip] = [
            t for t in _faucet_ip_times[client_ip] if now - t < 86400
        ]
        if len(_faucet_ip_times[client_ip]) >= FAUCET_IP_LIMIT:
            return 429, {"error": f"Too many faucet requests from your IP. Try again later."}

        # Address cooldown
        last = _faucet_addr_last.get(address_lc, 0)
        remaining = FAUCET_COOLDOWN - (now - last)
        if remaining > 0:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            return 429, {"error": f"Address already claimed. Try again in {hours}h {mins}m."}

    # Check on-chain balance (outside lock to avoid blocking)
    try:
        balance_hex = _eth_call("eth_getBalance", [address, "latest"])
        balance = int(balance_hex, 16)
    except Exception:
        return 502, {"error": "Failed to reach blockchain node. Try again later."}

    if balance >= FAUCET_MAX_BALANCE_WEI:
        bal_ust = balance / 10**18
        return 400, {"error": f"Address already has {bal_ust:.4f} UST — faucet is for new wallets only."}

    # Send UST
    try:
        tx_hash = _faucet_send(address)
    except Exception as exc:
        return 500, {"error": f"Faucet transaction failed: {exc}"}

    amount_ust = FAUCET_AMOUNT_WEI / 10**18

    with _faucet_lock:
        _faucet_addr_last[address_lc] = now
        _faucet_ip_times[client_ip].append(now)

    return 200, {
        "success": True,
        "txHash": tx_hash,
        "amount": f"{amount_ust} UST",
        "message": f"Sent {amount_ust} UST to {address}. Use it to pay gas for mining transactions.",
    }


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - RATE_WINDOW
    with _rate_lock:
        timestamps = _rate_counts[ip]
        # Drop old entries
        _rate_counts[ip] = [t for t in timestamps if t > cutoff]
        if len(_rate_counts[ip]) >= RATE_LIMIT:
            return True
        _rate_counts[ip].append(now)
    return False


def _rate_limit_response(req_id: object) -> bytes:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32005, "message": "Rate limit exceeded. Try again later."},
        }
    ).encode()

BLOCKED: frozenset[str] = frozenset(
    {
        "eth_accounts",
        "eth_sendTransaction",
        "eth_sign",
        "eth_signTransaction",
        "personal_importRawKey",
        "personal_listAccounts",
        "personal_lockAccount",
        "personal_newAccount",
        "personal_sendTransaction",
        "personal_sign",
        "personal_unlockAccount",
        "personal_ecRecover",
        "admin_addPeer",
        "admin_addTrustedPeer",
        "admin_exportChain",
        "admin_importChain",
        "admin_removePeer",
        "admin_startHTTP",
        "admin_startWS",
        "admin_stopHTTP",
        "admin_stopWS",
        "miner_getHashrate",
        "miner_setEtherbase",
        "miner_setExtra",
        "miner_setGasLimit",
        "miner_setGasPrice",
        "miner_start",
        "miner_stop",
        "debug_setHead",
        "debug_setGCPercent",
        "debug_freeOSMemory",
        "debug_writeMemProfile",
        "debug_writeMutexProfile",
        "debug_writeBlockProfile",
    }
)

BLOCKED_PREFIXES: tuple[str, ...] = ("personal_", "admin_")


def _is_blocked(method: str) -> bool:
    if method in BLOCKED:
        return True
    return any(method.startswith(p) for p in BLOCKED_PREFIXES)


def _error_response(req_id: object, method: str) -> bytes:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"The method {method} does not exist/is not available",
            },
        }
    ).encode()


def _forward_http(body: bytes) -> bytes:
    req = urllib.request.Request(
        GETH_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ─── HTTP server ──────────────────────────────────────────────────────────────


class FilterHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass  # silence access log

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"")

    def do_GET(self) -> None:
        if self.path == "/faucet/status":
            from eth_account import Account as _Acct
            faucet_addr = _Acct.from_key(FAUCET_KEY).address if FAUCET_KEY else None
            self._send(200, json.dumps({
                "enabled": _faucet_enabled(),
                "amount": f"{FAUCET_AMOUNT_WEI / 10**18} UST",
                "cooldownHours": FAUCET_COOLDOWN // 3600,
                "address": faucet_addr,
            }).encode())
            return
        if self.path == "/bridge/status":
            treasury = os.getenv("BRIDGE_TREASURY_ADDRESS", "")
            bridged_usdt = os.getenv("BRIDGED_USDT_ADDRESS", "")
            self._send(200, json.dumps({
                "enabled": bool(treasury),
                "treasury": treasury,
                "bridgedUSDT": bridged_usdt,
                "network": "Ethereum Mainnet → Chain 778889",
                "realUSDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            }).encode())
            return
        try:
            body = _forward_http(b'{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}')
            self._send(200, body)
        except Exception as exc:
            self._send(500, json.dumps({"error": str(exc)}).encode())

    def do_POST(self) -> None:
        if self.path == "/bridge/deposit":
            # Queue a deposit request — write to a log file for relayer to pick up
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)
            try:
                req = json.loads(raw)
                tx_hash   = req.get("txHash", "").strip()
                recipient = req.get("recipient", "").strip()
                import re
                if not re.match(r'^0x[0-9a-fA-F]{64}$', tx_hash):
                    self._send(400, json.dumps({"error": "Invalid txHash"}).encode()); return
                if not re.match(r'^0x[0-9a-fA-F]{40}$', recipient):
                    self._send(400, json.dumps({"error": "Invalid recipient"}).encode()); return
                # Append to bridge queue file
                import pathlib, time as _time
                queue_file = pathlib.Path(__file__).parent / "bridge-queue.jsonl"
                with open(queue_file, "a") as f:
                    f.write(json.dumps({"txHash": tx_hash, "recipient": recipient,
                                        "ts": int(_time.time())}) + "\n")
                self._send(200, json.dumps({"success": True}).encode())
            except Exception as exc:
                self._send(400, json.dumps({"error": str(exc)}).encode())
            return
        if self.path == "/faucet":
            client_ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            status, resp = handle_faucet(raw, client_ip)
            self._send(status, json.dumps(resp).encode())
            return

        client_ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        if _is_rate_limited(client_ip):
            # Use HTTP 200 so MetaMask can read the JSON-RPC error body
            self._send(200, _rate_limit_response(None))
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            self._send(200, _forward_http(raw))
            return

        if isinstance(payload, list):
            for item in payload:
                method = item.get("method", "") if isinstance(item, dict) else ""
                if _is_blocked(method):
                    self._send(200, _error_response(item.get("id"), method))
                    return
        elif isinstance(payload, dict):
            method = payload.get("method", "")
            if _is_blocked(method):
                self._send(200, _error_response(payload.get("id"), method))
                return

        try:
            self._send(200, _forward_http(raw))
        except Exception as exc:
            self._send(200, _error_response(None, str(exc)))


def _run_http() -> None:
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), FilterHandler)
    print(f"HTTP RPC filter  :{LISTEN_PORT} -> {GETH_URL}", flush=True)
    server.serve_forever()


# ─── WebSocket proxy ──────────────────────────────────────────────────────────


async def _ws_handler(client_ws: "websockets.ServerConnection") -> None:
    import websockets

    async with websockets.connect(GETH_WS_URL) as geth_ws:

        async def client_to_geth() -> None:
            async for raw in client_ws:
                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    await geth_ws.send(raw)
                    continue
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    method = item.get("method", "") if isinstance(item, dict) else ""
                    if _is_blocked(method):
                        err = _error_response(item.get("id"), method).decode()
                        await client_ws.send(err)
                        return
                await geth_ws.send(raw)

        async def geth_to_client() -> None:
            async for raw in geth_ws:
                await client_ws.send(raw)

        await asyncio.gather(client_to_geth(), geth_to_client())


async def _run_ws_async() -> None:
    import websockets

    print(f"WS  RPC filter   :{LISTEN_WS_PORT} -> {GETH_WS_URL}", flush=True)
    async with websockets.serve(_ws_handler, "0.0.0.0", LISTEN_WS_PORT):
        await asyncio.Future()


def _run_ws() -> None:
    asyncio.run(_run_ws_async())


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ws_thread = threading.Thread(target=_run_ws, daemon=True)
    ws_thread.start()
    _run_http()
