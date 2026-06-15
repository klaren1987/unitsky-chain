# One-time route exclusions for running two WireGuard tunnels simultaneously.
# Run ONCE as Administrator AFTER both tunnels are configured:
#   .\scripts\wireguard-dual-routes.ps1
#
# When you enable the secondary tunnel, run again (no scheduler, no background loop):
#   .\scripts\wireguard-dual-routes.ps1
#
# Do NOT use setup-wireguard-dual-routes.ps1 (old version registered a task every minute).

param(
    [string]$PrimaryTunnel   = "primary-wg",
    [string]$VpsEndpoint     = "147.45.143.23",
    [string]$SecondaryEndpoint = "0.0.0.0",
    [string]$WgSubnet        = "10.13.13.0/24"
)

$ErrorActionPreference = "SilentlyContinue"

function Get-PhysicalDefaultRoute {
    Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" |
        Where-Object {
            $_.InterfaceAlias -notmatch "WireGuard|Tailscale|ProtonVPN|OpenVPN|TAP|Wintun"
        } |
        Sort-Object RouteMetric |
        Select-Object -First 1
}

function Add-RouteOnce {
    param(
        [string]$DestinationPrefix,
        [string]$NextHop,
        [int]$InterfaceIndex,
        [int]$RouteMetric = 1,
        [switch]$Persistent
    )

    $stores = @("ActiveStore")
    if ($Persistent) { $stores = @("PersistentStore", "ActiveStore") }

    foreach ($store in $stores) {
        $exists = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $DestinationPrefix -PolicyStore $store -ErrorAction SilentlyContinue |
            Where-Object { $_.InterfaceIndex -eq $InterfaceIndex -and $_.NextHop -eq $NextHop } |
            Select-Object -First 1
        if ($exists) { continue }

        New-NetRoute -DestinationPrefix $DestinationPrefix -NextHop $NextHop -InterfaceIndex $InterfaceIndex `
            -RouteMetric $RouteMetric -PolicyStore $store -ErrorAction SilentlyContinue | Out-Null
    }
}

$primaryAdapter = Get-NetAdapter -Name $PrimaryTunnel -ErrorAction SilentlyContinue
$lanRoute = Get-PhysicalDefaultRoute
if (-not $lanRoute) {
    Write-Host "No physical default route found."
    exit 1
}

$lanIf = $lanRoute.InterfaceIndex
$lanGw = $lanRoute.NextHop

# VPS endpoint must go via the physical interface, not through the secondary tunnel
Add-RouteOnce -DestinationPrefix "$VpsEndpoint/32" -NextHop $lanGw -InterfaceIndex $lanIf -RouteMetric 1 -Persistent

# Secondary WG server — same reason (handshake must not loop through the tunnel)
if ($SecondaryEndpoint -ne "0.0.0.0") {
    Add-RouteOnce -DestinationPrefix "$SecondaryEndpoint/32" -NextHop $lanGw -InterfaceIndex $lanIf -RouteMetric 1 -Persistent
}

# Local LAN stays on the physical interface (printers, router admin, etc.)
$lanIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $lanIf |
    Where-Object { $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1
if ($lanIp) {
    $octets = $lanIp.IPAddress.Split(".")
    $lanNetwork = "$($octets[0]).$($octets[1]).$($octets[2]).0/24"
    Add-RouteOnce -DestinationPrefix $lanNetwork -NextHop $lanGw -InterfaceIndex $lanIf -RouteMetric 1 -Persistent
}

# WireGuard subnet only when the primary tunnel is up (WireGuard usually adds this itself)
if ($primaryAdapter -and $primaryAdapter.Status -eq "Up") {
    Add-RouteOnce -DestinationPrefix $WgSubnet -NextHop "0.0.0.0" -InterfaceIndex $primaryAdapter.ifIndex -RouteMetric 0 -Persistent
}

Write-Host "Routes applied successfully."
Write-Host ""
Get-NetRoute -AddressFamily IPv4 | Where-Object {
    $_.DestinationPrefix -match "10\.13\.13|147\.45\.143|192\.168"
} | Format-Table DestinationPrefix, NextHop, InterfaceAlias, RouteMetric -AutoSize
