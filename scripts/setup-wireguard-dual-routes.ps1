# DISABLED — the scheduled task caused WireGuard reconnects every minute.
# Use wireguard-dual-routes.ps1 manually instead:
#   1. Enable the primary WireGuard tunnel
#   2. Run:  .\scripts\wireguard-dual-routes.ps1   (as Administrator, once)
#   3. Enable the secondary tunnel
#
# To remove old task if still present:
#   Unregister-ScheduledTask -TaskName UST-WireGuard-DualRoutes -Confirm:$false

Write-Host "This installer is disabled."
Write-Host "Run instead: .\scripts\wireguard-dual-routes.ps1"
Write-Host ""
Write-Host "Removing old scheduled task if present..."
Unregister-ScheduledTask -TaskName "UST-WireGuard-DualRoutes" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Done."
