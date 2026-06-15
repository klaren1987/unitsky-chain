# Start public HTTPS RPC + block explorer (Caddy + Otterscan).
# Requires: node stack running (docker-compose.windows-node.yml).
# VPS: re-run install-wireguard-server.sh to DNAT ports 80/443 → Windows.

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Starting public stack (HTTPS + explorer)..."
docker compose -f docker-compose.public.yml up -d

Write-Host ""
Write-Host "Public endpoints (after VPS forwards :80/:443):"
Write-Host "  Explorer:  https://147-45-143-23.sslip.io"
Write-Host "  RPC:       https://147-45-143-23.sslip.io/rpc"
Write-Host "  Chainlist: chainlist/chainid-778889.js (submit PR to DefiLlama/chainlist)"
Write-Host ""
Write-Host "Checking VPS port forward..."
$rpc = try {
  $b = '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
  (Invoke-RestMethod -Uri "http://147.45.143.23:8545" -Method POST -ContentType "application/json" -Body $b -TimeoutSec 5).result
} catch { $null }
if ($rpc -eq "0xbe289") { Write-Host "  RPC :8545  OK (chain 778889)" -ForegroundColor Green }
else { Write-Host "  RPC :8545  FAIL — check WireGuard on VPS" -ForegroundColor Yellow }

$http80 = try { (Invoke-WebRequest -Uri "http://147.45.143.23/" -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }
if ($http80 -ge 200 -and $http80 -lt 400) { Write-Host "  HTTP :80   OK" -ForegroundColor Green }
else { Write-Host "  HTTP :80   not forwarded — run install-wireguard-server.sh on VPS" -ForegroundColor Yellow }

Write-Host ""
Write-Host "Chainlist PR: .\scripts\submit-chainlist.ps1  (after gh auth login)"
