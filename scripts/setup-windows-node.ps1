# USST node on Windows — Docker Desktop + WireGuard
# Run in PowerShell (as Administrator for firewall rules):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup-windows-node.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command docker)) {
    Write-Error "Docker not found. Install Docker Desktop for Windows first."
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon is not running. Start Docker Desktop."
}

$envFile = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.windows-node.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.windows-node.example"
}

Write-Host "==> Building and starting USST node stack..."
docker compose -f docker-compose.windows-node.yml up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> Services:"
docker compose -f docker-compose.windows-node.yml ps

# Windows Firewall — allow RPC/WS/P2P (needs elevation)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if ($isAdmin) {
    $ports = @(8545, 8546, 30303)
    foreach ($port in $ports) {
        $ruleName = "USST Node TCP $port"
        if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
            Write-Host "Firewall: allowed inbound TCP $port"
        }
    }
} else {
    Write-Warning "Run as Administrator once to open Windows Firewall for ports 8545, 8546, 30303."
}

Write-Host ""
Write-Host "==> Contract address (after deploy finishes):"
Write-Host "    docker compose -f docker-compose.windows-node.yml logs deploy"
Write-Host ""
Write-Host "==> Check RPC locally:"
Write-Host '    curl -s -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}"'
Write-Host ""
Write-Host "==> WireGuard: import config/wireguard/windows-client.conf.example (fill keys + VPS IP)"
Write-Host "==> VPS: apply config/wireguard/wg0.server.conf.example and restart wg-quick@wg0"
Write-Host "==> Remote miners: USST_RPC=http://YOUR_VPS_PUBLIC_IP:8545"
Write-Host "==> MetaMask on this PC: RPC http://127.0.0.1:8545 (metamask-network.json)"
