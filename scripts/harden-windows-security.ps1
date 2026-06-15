# Security hardening for Windows host running the USST node.
# Run as Administrator:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\harden-windows-security.ps1

$ErrorActionPreference = "Stop"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Error "Run this script as Administrator."
}

Write-Host "==> Ensure RDP is disabled"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name fDenyTSConnections -Value 1
Disable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue
Set-Service TermService -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service TermService -Force -ErrorAction SilentlyContinue

Write-Host "==> Block inbound SMB (445) on Public profile"
$ruleName = "Security Block SMB Public"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort 445 `
        -Profile Public -Action Block | Out-Null
}

Write-Host "==> Block direct SSH/internal ports from Public profile"
foreach ($port in @(22, 3000)) {
    $name = "Security Block Public TCP $port"
    if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $port `
            -Profile Public -Action Block | Out-Null
    }
}

Write-Host "==> Allow WireGuard subnet to Caddy (80/443) only"
$wgSubnet = "10.13.13.0/24"
foreach ($port in @(80, 443)) {
    $name = "UST-Node WG TCP $port"
    if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $port `
            -RemoteAddress $wgSubnet -Action Allow | Out-Null
    }
}

Write-Host "==> Disable WinRM if enabled"
Stop-Service WinRM -Force -ErrorAction SilentlyContinue
Set-Service WinRM -StartupType Disabled -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done. Manual steps still required:"
Write-Host "  1. Set a strong Windows password for your account (ensure it is not empty)"
Write-Host "  2. Rotate VPS SSH password if it was shared"
Write-Host "  3. Review Tailscale access if installed"
