#!/usr/bin/env python3
"""
Deploy Uniswap V2 (Factory + Router + WUST) on Chain 778889
and create UST/bUSDT liquidity pool.

Usage: run inside deploy container or any Python env with web3+py-solc-x
"""
import os, sys, json, time, subprocess, urllib.request, hashlib
from pathlib import Path
from eth_account import Account

# ── Config ────────────────────────────────────────────────────────────────────
RPC           = os.getenv("USST_RPC", "http://unitsky-string-node:8545")
KEY           = os.getenv("USST_DEPLOYER_KEY", "0x3014dac8e7e8082dd791032d9b451bcaf5f5b3b59f1bcc748516e78ba35555bc")
CHAIN_ID      = 778889
BRIDGED_USDT  = os.getenv("BRIDGED_USDT_ADDRESS", "0xcd7cb25f025B20D5f90C0FDA3463D91AF76A8EF1")

# Initial liquidity to seed pool: 10 UST + 1 bUSDT (just enough for price discovery)
LIQUIDITY_UST_WEI  = 10 * 10**18      # 10 UST (native)
LIQUIDITY_USDT_RAW = 1 * 10**18       # 1 bUSDT (18 decimals)

DEPLOY_DIR = Path("/tmp/uniswap-v2-deploy")
DEPLOY_DIR.mkdir(exist_ok=True)

# ── Minimal web3 helpers ──────────────────────────────────────────────────────
import urllib.request as req_lib

def rpc(method, params=[]):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    r = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in resp:
        raise RuntimeError(f"{method} error: {resp['error']}")
    return resp["result"]

def get_nonce(addr):
    return int(rpc("eth_getTransactionCount", [addr, "pending"]), 16)

def get_gas_price():
    # Use 1 gwei fixed to stay under fee cap
    return 10**9

def estimate_gas(tx):
    return int(int(rpc("eth_estimateGas", [tx]), 16) * 1.3)

def deploy_contract(abi, bytecode, constructor_args_hex=""):
    from eth_account import Account
    acct = Account.from_key(KEY)
    nonce = get_nonce(acct.address)
    gas_price = get_gas_price()
    data = "0x" + bytecode + constructor_args_hex
    gas = estimate_gas({"from": acct.address, "data": data})
    tx = {
        "nonce": nonce, "gasPrice": gas_price, "gas": int(gas),
        "to": None, "value": 0, "data": data, "chainId": CHAIN_ID
    }
    signed = acct.sign_transaction(tx)
    raw = "0x" + signed.raw_transaction.hex() if not signed.raw_transaction.hex().startswith("0x") else signed.raw_transaction.hex()
    tx_hash = rpc("eth_sendRawTransaction", [raw])
    print(f"  tx: {tx_hash}")
    return wait_receipt(tx_hash)

def to_checksum(addr):
    from eth_utils import to_checksum_address
    return to_checksum_address(addr)

def send_tx(to, data, value=0):
    acct = Account.from_key(KEY)
    nonce = get_nonce(acct.address)
    gas_price = get_gas_price()
    to = to_checksum(to)
    gas = estimate_gas({"from": acct.address, "to": to, "data": data, "value": hex(value)})
    tx = {
        "nonce": nonce, "gasPrice": gas_price, "gas": int(gas),
        "to": to, "value": value, "data": data, "chainId": CHAIN_ID
    }
    signed = acct.sign_transaction(tx)
    raw = "0x" + signed.raw_transaction.hex() if not signed.raw_transaction.hex().startswith("0x") else signed.raw_transaction.hex()
    tx_hash = rpc("eth_sendRawTransaction", [raw])
    print(f"  tx: {tx_hash}")
    return wait_receipt(tx_hash)

def wait_receipt(tx_hash, timeout=120):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                if receipt["status"] == "0x1":
                    return receipt
                else:
                    raise RuntimeError(f"Transaction FAILED: {tx_hash}")
        except RuntimeError as e:
            if "Transaction FAILED" in str(e): raise
    raise TimeoutError(f"Timeout waiting for {tx_hash}")

def pad32(val_hex):
    """Pad hex value to 32 bytes (64 hex chars)"""
    return val_hex[2:].zfill(64) if val_hex.startswith("0x") else val_hex.zfill(64)

def encode_address(addr):
    return addr[2:].lower().zfill(64)

# ── Download Uniswap V2 contracts from GitHub ──────────────────────────────────
def download(url, dest):
    if dest.exists():
        return
    print(f"  Downloading {dest.name}...")
    urllib.request.urlretrieve(url, dest)

BASE_CORE = "https://raw.githubusercontent.com/Uniswap/v2-core/master/contracts"
BASE_PERI = "https://raw.githubusercontent.com/Uniswap/v2-periphery/master/contracts"
BASE_LIB  = "https://raw.githubusercontent.com/Uniswap/v2-periphery/master/contracts/libraries"
BASE_ICORE = "https://raw.githubusercontent.com/Uniswap/v2-core/master/contracts/interfaces"
BASE_IPERI = "https://raw.githubusercontent.com/Uniswap/v2-periphery/master/contracts/interfaces"

print("=== Downloading Uniswap V2 contracts ===")
CORE_DIR = DEPLOY_DIR / "core"
PERI_DIR = DEPLOY_DIR / "periphery"
(CORE_DIR / "interfaces").mkdir(parents=True, exist_ok=True)
(CORE_DIR / "libraries").mkdir(parents=True, exist_ok=True)
(PERI_DIR / "interfaces").mkdir(parents=True, exist_ok=True)
(PERI_DIR / "libraries").mkdir(parents=True, exist_ok=True)

# Core (solc 0.5.16)
download(f"{BASE_CORE}/UniswapV2Factory.sol",           CORE_DIR / "UniswapV2Factory.sol")
download(f"{BASE_CORE}/UniswapV2Pair.sol",              CORE_DIR / "UniswapV2Pair.sol")
download(f"{BASE_CORE}/UniswapV2ERC20.sol",             CORE_DIR / "UniswapV2ERC20.sol")
download(f"{BASE_ICORE}/IUniswapV2Factory.sol",         CORE_DIR / "interfaces/IUniswapV2Factory.sol")
download(f"{BASE_ICORE}/IUniswapV2Pair.sol",            CORE_DIR / "interfaces/IUniswapV2Pair.sol")
download(f"{BASE_ICORE}/IUniswapV2Callee.sol",          CORE_DIR / "interfaces/IUniswapV2Callee.sol")
download(f"{BASE_ICORE}/IERC20.sol",                    CORE_DIR / "interfaces/IERC20.sol")
download(f"{BASE_ICORE}/IUniswapV2ERC20.sol",           CORE_DIR / "interfaces/IUniswapV2ERC20.sol")
download(f"{BASE_CORE}/libraries/Math.sol",             CORE_DIR / "libraries/Math.sol")
download(f"{BASE_CORE}/libraries/UQ112x112.sol",        CORE_DIR / "libraries/UQ112x112.sol")
download(f"{BASE_CORE}/libraries/SafeMath.sol",         CORE_DIR / "libraries/SafeMath.sol")

# Periphery (solc 0.6.6)
download(f"{BASE_PERI}/UniswapV2Router02.sol",          PERI_DIR / "UniswapV2Router02.sol")
download(f"{BASE_LIB}/UniswapV2Library.sol",            PERI_DIR / "libraries/UniswapV2Library.sol")
download(f"{BASE_LIB}/UniswapV2OracleLibrary.sol",      PERI_DIR / "libraries/UniswapV2OracleLibrary.sol")
download(f"{BASE_LIB}/SafeMath.sol",                    PERI_DIR / "libraries/SafeMath.sol")
download("https://raw.githubusercontent.com/Uniswap/solidity-lib/master/contracts/libraries/TransferHelper.sol",
         PERI_DIR / "libraries/TransferHelper.sol")
download(f"{BASE_IPERI}/IUniswapV2Router01.sol",        PERI_DIR / "interfaces/IUniswapV2Router01.sol")
download(f"{BASE_IPERI}/IUniswapV2Router02.sol",        PERI_DIR / "interfaces/IUniswapV2Router02.sol")
download(f"{BASE_IPERI}/IWETH.sol",                     PERI_DIR / "interfaces/IWETH.sol")
# Periphery also imports core interfaces
download(f"{BASE_ICORE}/IUniswapV2Factory.sol",         PERI_DIR / "interfaces/IUniswapV2Factory.sol")
download(f"{BASE_ICORE}/IUniswapV2Pair.sol",            PERI_DIR / "interfaces/IUniswapV2Pair.sol")
download(f"{BASE_ICORE}/IERC20.sol",                    PERI_DIR / "interfaces/IERC20.sol")

# WUST9 — wrapped native UST (WETH equivalent)
wust_src = '''// SPDX-License-Identifier: GPL-3.0
pragma solidity =0.5.16;

contract WUST9 {
    string public name     = "Wrapped UST";
    string public symbol   = "WUST";
    uint8  public decimals = 18;

    event  Approval(address indexed src, address indexed guy, uint wad);
    event  Transfer(address indexed src, address indexed dst, uint wad);
    event  Deposit(address indexed dst, uint wad);
    event  Withdrawal(address indexed src, uint wad);

    mapping (address => uint)                       public  balanceOf;
    mapping (address => mapping (address => uint))  public  allowance;

    function() external payable { deposit(); }
    function deposit() public payable {
        balanceOf[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }
    function withdraw(uint wad) public {
        require(balanceOf[msg.sender] >= wad);
        balanceOf[msg.sender] -= wad;
        msg.sender.transfer(wad);
        emit Withdrawal(msg.sender, wad);
    }
    function totalSupply() public view returns (uint) {
        return address(this).balance;
    }
    function approve(address guy, uint wad) public returns (bool) {
        allowance[msg.sender][guy] = wad;
        emit Approval(msg.sender, guy, wad);
        return true;
    }
    function transfer(address dst, uint wad) public returns (bool) {
        return transferFrom(msg.sender, dst, wad);
    }
    function transferFrom(address src, address dst, uint wad) public returns (bool) {
        require(balanceOf[src] >= wad);
        if (src != msg.sender && allowance[src][msg.sender] != uint(-1)) {
            require(allowance[src][msg.sender] >= wad);
            allowance[src][msg.sender] -= wad;
        }
        balanceOf[src] -= wad;
        balanceOf[dst] += wad;
        emit Transfer(src, dst, wad);
        return true;
    }
}
'''
(DEPLOY_DIR / "WUST9.sol").write_text(wust_src)

# ── Install solc 0.5.16 ────────────────────────────────────────────────────────
print("\n=== Installing solc versions ===")
try:
    import solcx
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "py-solc-x", "-q"], check=True)
    import solcx

from eth_hash.auto import keccak

solcx.install_solc("0.5.16", show_progress=False)
solcx.install_solc("0.6.6",  show_progress=False)
print("  solc 0.5.16 and 0.6.6 ready")

def compile_contract(sol_file, contract_name, ver, base_dir, extra_allow=None):
    print(f"  Compiling {contract_name} (solc {ver})...")
    allow = [str(base_dir)]
    if extra_allow:
        allow.extend(extra_allow)
    result = solcx.compile_files(
        [str(sol_file)],
        output_values=["abi", "bin"],
        solc_version=ver,
        allow_paths=allow,
        optimize=True,
        optimize_runs=200,
    )
    for key, art in result.items():
        if contract_name in key:
            return art["abi"], art["bin"]
    raise RuntimeError(f"{contract_name} not found in {sol_file}")

print("\n=== Compiling contracts ===")
# WUST9 uses 0.5.16
(DEPLOY_DIR / "WUST9.sol").write_text((DEPLOY_DIR / "WUST9.sol").read_text())
wust_abi, wust_bin = compile_contract(DEPLOY_DIR / "WUST9.sol", "WUST9", "0.5.16", DEPLOY_DIR)

# Core with 0.5.16
factory_abi, factory_bin = compile_contract(CORE_DIR / "UniswapV2Factory.sol", "UniswapV2Factory", "0.5.16", CORE_DIR)

# Compute INIT_CODE_HASH from compiled Pair
print("\n=== Computing INIT_CODE_HASH ===")
pair_abi, pair_bin = compile_contract(CORE_DIR / "UniswapV2Pair.sol", "UniswapV2Pair", "0.5.16", CORE_DIR)
pair_bytecode_bytes = bytes.fromhex(pair_bin)
init_code_hash = "0x" + keccak(pair_bytecode_bytes).hex()
print(f"  INIT_CODE_HASH = {init_code_hash}")

# Patch UniswapV2Library with correct init_code_hash
# In the .sol file the hash is in hex'' literal format (no 0x prefix)
lib_path = PERI_DIR / "libraries/UniswapV2Library.sol"
lib_src = lib_path.read_text()
old_hex_literal = "hex'96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f'"
new_hex_literal  = "hex'" + init_code_hash[2:] + "'"  # strip 0x
lib_path.write_text(lib_src.replace(old_hex_literal, new_hex_literal))
print(f"  Patched UniswapV2Library: {new_hex_literal}")

# Compile Router with 0.6.6 — patch npm-style imports to relative paths
def patch_imports(path):
    src = path.read_text()
    src = src.replace("'@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol'",
                      "'./interfaces/IUniswapV2Factory.sol'")
    src = src.replace("'@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol'",
                      "'./interfaces/IUniswapV2Pair.sol'")
    src = src.replace("'@uniswap/lib/contracts/libraries/TransferHelper.sol'",
                      "'./libraries/TransferHelper.sol'")
    path.write_text(src)

def patch_lib_imports(path):
    src = path.read_text()
    src = src.replace("'@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol'",
                      "'../interfaces/IUniswapV2Pair.sol'")
    path.write_text(src)

patch_imports(PERI_DIR / "UniswapV2Router02.sol")
patch_lib_imports(PERI_DIR / "libraries" / "UniswapV2Library.sol")
patch_lib_imports(PERI_DIR / "libraries" / "UniswapV2OracleLibrary.sol")
print("  Patched periphery imports to relative paths")

router_abi, router_bin = compile_contract(
    PERI_DIR / "UniswapV2Router02.sol", "UniswapV2Router02", "0.6.6", PERI_DIR)

# ── Deploy ─────────────────────────────────────────────────────────────────────
from eth_utils import to_checksum_address

deployer = Account.from_key(KEY)
print(f"\n=== Deploying from {deployer.address} ===")

# Resume file — skip already-deployed contracts
resume_file = Path("/tmp/dex-resume.json")
resume = json.loads(resume_file.read_text()) if resume_file.exists() else {}

def save_resume():
    resume_file.write_text(json.dumps(resume, indent=2))

# 1. WUST9
if "wust" in resume:
    wust_addr = resume["wust"]
    print(f"\n[1/4] WUST9 already deployed at {wust_addr}")
else:
    print("\n[1/4] Deploying WUST9...")
    receipt = deploy_contract(wust_abi, wust_bin)
    wust_addr = to_checksum_address(receipt["contractAddress"])
    resume["wust"] = wust_addr
    save_resume()
    print(f"  WUST9 = {wust_addr}")

# 2. Factory (feeToSetter = deployer)
if "factory" in resume:
    factory_addr = resume["factory"]
    print(f"\n[2/4] Factory already deployed at {factory_addr}")
else:
    print("\n[2/4] Deploying UniswapV2Factory...")
    factory_args = encode_address(deployer.address)
    receipt = deploy_contract(factory_abi, factory_bin, factory_args)
    factory_addr = to_checksum_address(receipt["contractAddress"])
    resume["factory"] = factory_addr
    save_resume()
    print(f"  Factory = {factory_addr}")

# 3. Router02 (factory, WUST)
if "router" in resume:
    router_addr = resume["router"]
    print(f"\n[3/4] Router already deployed at {router_addr}")
else:
    print("\n[3/4] Deploying UniswapV2Router02...")
    router_args = encode_address(factory_addr) + encode_address(wust_addr)
    receipt = deploy_contract(router_abi, router_bin, router_args)
    router_addr = to_checksum_address(receipt["contractAddress"])
    resume["router"] = router_addr
    save_resume()
    print(f"  Router = {router_addr}")

# 4. Create WUST/bUSDT pair via Factory
if "pair" in resume:
    pair_addr = resume["pair"]
    print(f"\n[4/4] Pair already created at {pair_addr}")
else:
    print("\n[4/4] Creating WUST/bUSDT pair...")
    selector = "0x" + keccak(b"createPair(address,address)").hex()[:8]
    data = selector + encode_address(wust_addr) + encode_address(BRIDGED_USDT)
    receipt = send_tx(to_checksum(factory_addr), data)
    # getPair fallback
    sel_gp = "0x" + keccak(b"getPair(address,address)").hex()[:8]
    d2 = sel_gp + encode_address(wust_addr) + encode_address(BRIDGED_USDT)
    result = rpc("eth_call", [{"to": factory_addr, "data": d2}, "latest"])
    pair_addr = to_checksum("0x" + result[-40:])
    resume["pair"] = pair_addr
    save_resume()
    print(f"  Pair = {pair_addr}")

# 5. Add initial liquidity using addLiquidityETH (native UST + bUSDT)
print("\n[5/5] Adding initial liquidity (10 UST + 1 bUSDT)...")

sel_approve = "0x" + keccak(b"approve(address,uint256)").hex()[:8]
max_uint = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

# Check if deployer already has bUSDT (from previous run)
sel_bal = "0x" + keccak(b"balanceOf(address)").hex()[:8]
raw_bal = rpc("eth_call", [{"to": BRIDGED_USDT, "data": sel_bal + encode_address(deployer.address)}, "latest"])
deployer_busdt = int(raw_bal, 16)
print(f"  Deployer bUSDT balance: {deployer_busdt / 1e18}")

if deployer_busdt < LIQUIDITY_USDT_RAW:
    # Mint bUSDT to deployer via bridgeMint(address,uint256,bytes32)
    print("  Minting 1 bUSDT to deployer...")
    sel_mint = "0x" + keccak(b"bridgeMint(address,uint256,bytes32)").hex()[:8]
    # Use unique txhash based on current time to avoid duplicate processing
    import struct
    fake_txhash = ("dex" + hex(int(time.time()))[2:]).encode().hex().ljust(64, '0')[:64]
    data_mint = sel_mint + encode_address(deployer.address) + hex(LIQUIDITY_USDT_RAW)[2:].zfill(64) + fake_txhash
    receipt = send_tx(to_checksum(BRIDGED_USDT), data_mint)
    print("  bUSDT minted")
else:
    print("  Deployer already has enough bUSDT")

# Approve bUSDT for Router
print("  Approving bUSDT...")
receipt = send_tx(to_checksum(BRIDGED_USDT), sel_approve + encode_address(router_addr) + max_uint)

# Use addLiquidityETH: pairs native UST (msg.value) with bUSDT
# addLiquidityETH(address token, uint256 amountTokenDesired, uint256 amountTokenMin, uint256 amountETHMin, address to, uint256 deadline)
sel_addliq = "0x" + keccak(b"addLiquidityETH(address,uint256,uint256,uint256,address,uint256)").hex()[:8]
deadline = int(time.time()) + 3600
data = (sel_addliq
    + encode_address(BRIDGED_USDT)
    + hex(LIQUIDITY_USDT_RAW)[2:].zfill(64)         # amountTokenDesired
    + hex(LIQUIDITY_USDT_RAW * 9 // 10)[2:].zfill(64)  # amountTokenMin (90%)
    + hex(LIQUIDITY_UST_WEI * 9 // 10)[2:].zfill(64)   # amountETHMin (90%)
    + encode_address(deployer.address)
    + hex(deadline)[2:].zfill(64)
)
print("  Adding liquidity (ETH + bUSDT)...")
receipt = send_tx(router_addr, data, value=LIQUIDITY_UST_WEI)
print("  Liquidity added!")

# ── Save results ───────────────────────────────────────────────────────────────
results = {
    "WUST":       wust_addr,
    "Factory":    factory_addr,
    "Router":     router_addr,
    "Pair":       pair_addr,
    "BridgedUSDT": BRIDGED_USDT,
    "InitCodeHash": init_code_hash,
}
out = Path("/app/dex-deployed.json")
out.write_text(json.dumps(results, indent=2))
print(f"\n=== Deployment complete ===")
for k, v in results.items():
    print(f"  {k}: {v}")
print(f"\nSaved to {out}")
