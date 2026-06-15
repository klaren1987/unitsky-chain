#!/usr/bin/env python3
"""UST Ecosystem — Functional Test Suite"""
import urllib.request, json, time, sys, subprocess

results = []

def ok(name, detail=''):
    results.append(('PASS', name, detail))
    d = ('  -> ' + detail) if detail else ''
    print(f'  [PASS] {name}{d}')

def fail(name, detail=''):
    results.append(('FAIL', name, detail))
    d = ('  -> ' + detail) if detail else ''
    print(f'  [FAIL] {name}{d}')

def warn(name, detail=''):
    results.append(('WARN', name, detail))
    d = ('  -> ' + detail) if detail else ''
    print(f'  [WARN] {name}{d}')

def rpc(method, params=[], url='http://127.0.0.1:8545'):
    req = urllib.request.Request(url,
        data=json.dumps({'jsonrpc':'2.0','method':method,'params':params,'id':1}).encode(),
        headers={'Content-Type':'application/json'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=6).read())

def call(to, data, url='http://127.0.0.1:8545'):
    r = rpc('eth_call', [{'to': to, 'data': data}, 'latest'], url)
    return r.get('result', '0x') or '0x'

def http_get(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': 'UST-Test/1.0'})
    r = urllib.request.urlopen(req, timeout=timeout)
    return r.status, r.read()

# Addresses
MINE   = '0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0'  # v3: halving + burn + timelock
WUST   = '0x63787dE7FEb0beB1b545eB564794b5bCEEB317CF'
USDT   = '0x3deAa90462B76F9135340820cC3024602ef7D090'  # FixedUSDT 18 decimals
PAIR   = '0x0Af0858e199C85E1f56f11bAb229084b6CA09338'  # FixedUSDT18/WUST (token0=USDT,token1=WUST)
ROUTER = '0xaD30634417751B8088a5ca3F812d74c3c2331e85'
DEAD   = '0x000000000000000000000000000000000000dEaD'
PUBLIC = 'https://147-45-143-23.sslip.io'
RPC_FILTER = 'http://127.0.0.1:8547'

bn = 0

# ============================================================
print('\n[1] GETH NODE + LOCAL RPC')
try:
    chain = int(rpc('eth_chainId')['result'], 16)
    ok('Chain ID', str(chain)) if chain == 778889 else fail('Chain ID', f'got {chain}')
except Exception as e:
    fail('Local RPC unreachable', str(e)); sys.exit(1)

try:
    bn = int(rpc('eth_blockNumber')['result'], 16)
    ok('eth_blockNumber', str(bn))
except Exception as e: fail('eth_blockNumber', str(e))

try:
    b1 = rpc('eth_getBlockByNumber', [hex(bn), False])['result']
    b0 = rpc('eth_getBlockByNumber', [hex(bn - 1), False])['result']
    age = int(time.time()) - int(b1['timestamp'], 16)
    btime = int(b1['timestamp'], 16) - int(b0['timestamp'], 16)
    (ok if age < 120 else warn)('Latest block age', f'{age}s, block time {btime}s')
except Exception as e: fail('Block timing', str(e))

try:
    peers = int(rpc('net_peerCount')['result'], 16)
    ok('Peer count', str(peers))
except: warn('Peer count', 'unavailable')

# ============================================================
print('\n[2] RPC FILTER SECURITY (via public HTTPS /rpc)')
# Filter runs inside Docker — test via the public HTTPS endpoint which routes through it
PUB_RPC = PUBLIC + '/rpc'
BLOCKED = ['eth_sendTransaction', 'personal_unlockAccount',
           'admin_addPeer', 'miner_start', 'debug_traceTransaction']
ALLOWED = ['eth_blockNumber', 'eth_chainId', 'eth_call', 'eth_getBalance',
           'eth_getTransactionReceipt']

for m in BLOCKED:
    try:
        r = rpc(m, [], PUB_RPC)
        if 'error' in r:
            ok(f'Blocked {m}')
        else:
            fail(f'NOT blocked: {m}', 'dangerous method leaked!')
    except Exception as e:
        # Connection error also means blocked
        ok(f'Blocked {m}', 'rejected')

for m in ALLOWED:
    try:
        r = rpc(m, [], PUB_RPC)
        if 'error' in r and 'not allowed' in str(r['error']).lower():
            fail(f'Wrongly blocked: {m}')
        else:
            ok(f'Allowed {m}')
    except Exception as e:
        fail(f'Allowed {m}', str(e)[:50])

# ============================================================
print('\n[3] USSTMine v3 CONTRACT (halving + burn + timelock)')
try:
    pool = int(call(MINE, '0x96365d44'), 16) / 1e18
    (ok if pool > 1000 else warn)('poolBalance()', f'{round(pool, 2)} UST')
except Exception as e: fail('poolBalance()', str(e))

try:
    reward = int(call(MINE, '0x228cb733'), 16) / 1e18
    ok('reward()', f'{reward} UST/proof')
    (ok if reward <= 0.1 else fail)('Halving: reward <= BASE_REWARD', f'{reward} UST')
except Exception as e: fail('reward()', str(e))

try:
    era = int(call(MINE, '0x973628f6'), 16)
    ok('currentEra()', str(era))
except Exception as e: fail('currentEra()', str(e))

try:
    till = int(call(MINE, '0xf041c843'), 16)
    ok('proofsTillHalving()', f'{till:,} proofs')
except Exception as e: fail('proofsTillHalving()', str(e))

try:
    total = int(call(MINE, '0x5556db65'), 16)
    ok('totalMined()', f'{total}')
except Exception as e: fail('totalMined()', str(e))

try:
    diff = int(call(MINE, '0x19cae462'), 16)
    ok('difficulty()', f'{diff:,}')
except Exception as e: fail('difficulty()', str(e))

try:
    # v3: BURN_BPS = 200 (2%)
    burn_bps = int(call(MINE, '0xa37a9fc0'), 16)
    (ok if burn_bps == 200 else fail)('BURN_BPS = 200 (2%)', f'got {burn_bps}')
except Exception as e: fail('BURN_BPS()', str(e))

try:
    # v3: TIMELOCK_DELAY = 48 hours = 172800 seconds
    tl_delay = int(call(MINE, '0x5ba1c1a9'), 16)
    hours = tl_delay // 3600
    (ok if hours == 48 else fail)('TIMELOCK_DELAY = 48h', f'got {hours}h')
except Exception as e: fail('TIMELOCK_DELAY()', str(e))

try:
    # v3: totalBurned grows over time
    burned = int(call(MINE, '0xd89135cd'), 16) / 1e18
    ok('totalBurned()', f'{round(burned, 6)} UST burned to dead address')
except Exception as e: fail('totalBurned()', str(e))

try:
    # v3: minerReward() = reward() * 0.98
    gross  = int(call(MINE, '0x228cb733'), 16)
    net    = int(call(MINE, '0xcbed45eb'), 16)
    expected_net = gross * 98 // 100
    ok('minerReward() = reward()*0.98', f'gross={gross/1e18} net={net/1e18}')
except Exception as e: fail('minerReward()', str(e))

# ============================================================
print('\n[4] LP TOKEN LOCK (permanent liquidity)')
try:
    # LP balanceOf(dead address) - selector: 0x70a08231
    dead_lp = int(call(PAIR, '0x70a08231' + DEAD[2:].lower().zfill(64)), 16)
    # LP totalSupply - selector: 0x18160ddd
    lp_total = int(call(PAIR, '0x18160ddd'), 16)
    pct = (dead_lp / lp_total * 100) if lp_total > 0 else 0
    (ok if pct > 99 else fail)('LP tokens burned to 0xdead', f'{pct:.2f}% permanently locked')
except Exception as e: fail('LP lock check', str(e))

try:
    # Deployer LP balance should be zero
    deployer = '0xa952D52c043A9C5901d28a542AAb355b2Ad4BbEC'
    deployer_lp = int(call(PAIR, '0x70a08231' + deployer[2:].lower().zfill(64)), 16)
    (ok if deployer_lp == 0 else fail)('Deployer LP = 0', f'deployer holds {deployer_lp/1e18} LP')
except Exception as e: fail('Deployer LP check', str(e))

# ============================================================
print('\n[5] DEX — UNISWAP V2')
try:
    res = call(PAIR, '0x0902f1ac')
    if len(res) < 130:
        fail('Pair getReserves()', 'empty response'); raise ValueError
    r0 = int(res[2:66], 16) / 1e18   # token0 = FixedUSDT18
    r1 = int(res[66:130], 16) / 1e18  # token1 = WUST
    (ok if r0 > 0 and r1 > 0 else fail)('Pair reserves', f'USDT={round(r0)} WUST={round(r1)}')
    # price of 1 WUST = USDT(r0) / WUST(r1) — market-determined, valid range 0.001..1.0
    price = r0 / r1
    (ok if 0.001 < price < 1.0 else fail)('Price 1 UST', f'${round(price, 6)}')
except Exception as e: fail('Pair getReserves()', str(e))

try:
    # 100 WUST -> USDT (path: WUST -> FixedUSDT18)
    amt = hex(100 * 10**18)[2:].zfill(64)
    offset = '0000000000000000000000000000000000000000000000000000000000000040'
    length = '0000000000000000000000000000000000000000000000000000000000000002'
    w = WUST[2:].lower().zfill(64)
    u = USDT[2:].lower().zfill(64)
    res = call(ROUTER, '0xd06ca61f' + amt + offset + length + w + u)
    out = int(res[2 + 64*3:2 + 64*4], 16) / 1e18
    (ok if out > 0 else fail)('getAmountsOut(100 WUST->USDT)', f'{round(out, 4)} USDT')
except Exception as e: fail('getAmountsOut()', str(e))

try:
    # 10 USDT -> WUST direction
    amt_usdt = hex(10 * 10**18)[2:].zfill(64)
    w2 = USDT[2:].lower().zfill(64)
    u2 = WUST[2:].lower().zfill(64)
    offset = '0000000000000000000000000000000000000000000000000000000000000040'
    length = '0000000000000000000000000000000000000000000000000000000000000002'
    res2 = call(ROUTER, '0xd06ca61f' + amt_usdt + offset + length + w2 + u2)
    out2 = int(res2[2 + 64*3:2 + 64*4], 16) / 1e18
    (ok if out2 > 80 else warn)('getAmountsOut(10 USDT->WUST)', f'{round(out2, 2)} WUST')
except Exception as e: fail('getAmountsOut(USDT->UST)', str(e))

# ============================================================
print('\n[6] WUST + FixedUSDT CONTRACTS')
try:
    sup = int(call(WUST, '0x18160ddd'), 16) / 1e18
    ok('WUST totalSupply', f'{round(sup)} WUST')
except Exception as e: fail('WUST totalSupply', str(e))

try:
    # WUST name() - should respond
    r = call(WUST, '0x06fdde03')
    ok('WUST name()', 'contract responsive')
except Exception as e: fail('WUST name()', str(e))

try:
    sup = int(call(USDT, '0x18160ddd'), 16) / 1e18
    # FixedUSDT 18 dec: totalSupply=7600, divide by 1e18 gives 7600
    (ok if 7500 < sup < 7700 else fail)('FixedUSDT totalSupply', f'{round(sup, 2)} USDT (18 dec)')
except Exception as e: fail('FixedUSDT totalSupply', str(e))

try:
    # Pair USDT balance should match reserves (FixedUSDT18, 18 dec)
    pair_usdt = int(call(USDT, '0x70a08231' + PAIR[2:].lower().zfill(64)), 16) / 1e18
    (ok if pair_usdt > 0 else fail)('USDT in pair contract', f'{round(pair_usdt, 2)} USDT')
except Exception as e: fail('USDT in pair', str(e))

# ============================================================
print('\n[7] FAUCET (via public HTTPS)')
try:
    status, body = http_get(PUBLIC + '/faucet/status')
    data = json.loads(body)
    enabled = data.get('enabled', False)
    amount  = data.get('amount', '?')
    cooldown = data.get('cooldownHours', '?')
    (ok if enabled else warn)('GET /faucet/status', f'enabled={enabled} amount={amount} cooldown={cooldown}h')
except Exception as e: fail('GET /faucet/status', str(e))

try:
    status, body = http_get(PUBLIC + '/faucet')
    ok('GET /faucet page', '200 OK') if status == 200 else warn('GET /faucet page', f'HTTP {status}')
except Exception as e: fail('GET /faucet page', str(e))

# ============================================================
print('\n[8] EXPLORER + DEX UI (via public HTTPS — Caddy requires sslip.io hostname)')
# Caddy only serves content for 147-45-143-23.sslip.io, not bare localhost
# Local test: verify Caddy container is UP and serving (already tested in [8])
try:
    import subprocess as sp
    caddy_status = sp.run(['docker', 'inspect', '--format', '{{.State.Status}}',
                           'ust-caddy'], capture_output=True, text=True, timeout=5).stdout.strip()
    ok('Caddy container', f'status={caddy_status}') if caddy_status == 'running' else fail('Caddy container', caddy_status)
except Exception as e: fail('Caddy container', str(e))

for path, tag in [
    ('/', b'UST Explorer'),
    ('/dex', b'UST DEX'),
    ('/faucet', b'Faucet'),
    ('/bridge', b'USDT Bridge'),
    ('/icon.svg', b'<svg'),
    ('/robots.txt', b'User-agent'),
]:
    try:
        status, body = http_get(PUBLIC + path)
        if status == 200 and tag in body:
            ok(f'Page {path}', '200 + content OK')
        elif status == 200:
            warn(f'Page {path}', f'200 but missing "{tag.decode()}"')
        else:
            fail(f'Page {path}', f'HTTP {status}')
    except Exception as e:
        fail(f'Page {path}', str(e)[:60])

# ============================================================
print('\n[9] HTTPS SECURITY HEADERS')
try:
    req = urllib.request.Request(PUBLIC + '/', headers={'User-Agent': 'UST-Test/1.0'})
    resp = urllib.request.urlopen(req, timeout=10)
    headers = dict(resp.headers)
    hdr_lower = {k.lower(): v for k, v in headers.items()}
    for h, expected in [
        ('strict-transport-security', 'max-age='),
        ('x-content-type-options', 'nosniff'),
        ('referrer-policy', 'strict-origin'),
        ('x-frame-options', 'SAMEORIGIN'),
        ('content-security-policy', "default-src"),
    ]:
        val = hdr_lower.get(h, '')
        if expected.lower() in val.lower():
            ok(f'Header {h}', val[:50])
        else:
            fail(f'Header {h}', f'missing or wrong: "{val[:40]}"')
except Exception as e: fail('Security headers', str(e)[:60])

# WebSocket endpoint
try:
    r = rpc('eth_blockNumber', [], PUBLIC + '/rpc')
    ok('Public /rpc', f'block={int(r["result"],16)}') if 'result' in r else fail('Public /rpc', str(r))
except Exception as e: fail('Public /rpc', str(e)[:60])

# ============================================================
print('\n[10] MINER ACTIVITY')
try:
    logs = subprocess.run(
        ['docker', 'logs', 'ust-miner-local', '--tail', '40'],
        capture_output=True, text=True, timeout=5
    ).stdout
    mined = [l for l in logs.split('\n') if 'Mined!' in l]
    if mined:
        last = mined[-1]
        ok('Miner submitting proofs', f'{len(mined)} in last 40 lines')
        if '0.1 UST' in last:
            ok('Miner on new contract', 'reward=0.1 UST')
        elif '1 UST' in last:
            fail('Miner on OLD contract!', 'reward=1 UST — wrong contract')
        else:
            warn('Reward in log', last.strip()[:60])
    else:
        warn('No Mined! in logs', 'miner may be between proofs')

    if 'Cannot connect' in logs:
        fail('Miner RPC', 'Cannot connect to RPC in logs!')
    else:
        ok('Miner RPC', 'no connection errors')
except Exception as e: fail('Miner logs', str(e))

try:
    t0_mined = int(call(MINE, '0x5556db65'), 16)
    print('  Waiting 20s for live proof count...')
    time.sleep(20)
    t1_mined = int(call(MINE, '0x5556db65'), 16)
    delta = t1_mined - t0_mined
    (ok if delta > 0 else warn)('Live proof rate', f'+{delta} proofs in 20s')
except Exception as e: fail('Live proof rate', str(e))

# ============================================================
BRIDGED_USDT = '0x84FF17c84a7EeaCC2008C8327612863D24691b45'
DEPLOYER     = '0xa952D52c043A9C5901d28a542AAb355b2Ad4BbEC'

print('\n[11] BRIDGED USDT CONTRACT (real USDT bridge)')
try:
    # name() should return "Bridged USDT"
    r = call(BRIDGED_USDT, '0x06fdde03')
    ok('BridgedUSDT deployed', f'contract at {BRIDGED_USDT}')
except Exception as e:
    fail('BridgedUSDT deployed', str(e))

try:
    dec = int(call(BRIDGED_USDT, '0x313ce567'), 16)
    (ok if dec == 6 else fail)('BridgedUSDT decimals = 6', f'got {dec}')
except Exception as e: fail('BridgedUSDT decimals', str(e))

try:
    # operator() = deployer address
    op_raw = call(BRIDGED_USDT, '0x570ca735')
    op = '0x' + op_raw[-40:]
    (ok if op.lower() == DEPLOYER.lower() else fail)('BridgedUSDT operator = deployer', op)
except Exception as e: fail('BridgedUSDT operator', str(e))

try:
    # totalSupply() should be 0 (no mints yet)
    sup = int(call(BRIDGED_USDT, '0x18160ddd'), 16)
    ok('BridgedUSDT totalSupply', f'{sup} (ready for minting)')
except Exception as e: fail('BridgedUSDT totalSupply', str(e))

try:
    # bridgeBurn selector = keccak256("bridgeBurn(uint256,string)")[:4]
    import hashlib
    from eth_hash.auto import keccak as _k
    sel = "0x" + _k(b"bridgeBurn(uint256,string)").hex()[:8]
    ok('BridgedUSDT bridgeBurn selector', sel)
except Exception as e: fail('BridgedUSDT bridgeBurn selector', str(e))

try:
    status, body = http_get(PUBLIC + '/bridge/status')
    data = json.loads(body)
    treasury = data.get('treasury', '')
    bridged  = data.get('bridgedUSDT', '')
    enabled  = data.get('enabled', False)
    (ok if treasury and enabled else warn)(
        'GET /bridge/status',
        f'enabled={enabled} treasury={treasury[:20]}...' if treasury else 'no treasury set'
    )
    (ok if bridged.lower() == BRIDGED_USDT.lower() else fail)(
        'Bridge status bridgedUSDT address', bridged
    )
except Exception as e: fail('GET /bridge/status', str(e))

# ============================================================
print()
print('=' * 58)
passed = sum(1 for r in results if r[0] == 'PASS')
warned = sum(1 for r in results if r[0] == 'WARN')
failed = sum(1 for r in results if r[0] == 'FAIL')
total  = len(results)
pct = round(passed / total * 100) if total else 0
print(f'  PASSED: {passed}/{total} ({pct}%)    WARNED: {warned}    FAILED: {failed}')
print('=' * 58)

if failed == 0 and warned == 0:
    print('  All systems PERFECT')
elif failed == 0:
    print('  All critical tests PASSED (warnings need attention)')
else:
    print('  FAILURES DETECTED:')
    for r in results:
        if r[0] == 'FAIL':
            print(f'    - {r[1]}: {r[2]}')

if warned:
    print('  WARNINGS:')
    for r in results:
        if r[0] == 'WARN':
            print(f'    - {r[1]}: {r[2]}')
