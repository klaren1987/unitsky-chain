# Opens one-click MetaMask setup page (local HTTP server required for MetaMask injection)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Port = 8765
$Url = "http://127.0.0.1:$Port/scripts/metamask-setup.html"

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $existing) {
    Start-Process -WindowStyle Hidden powershell -ArgumentList @(
        "-NoProfile", "-Command",
        "Set-Location '$Root'; python -m http.server $Port"
    )
    Start-Sleep -Seconds 2
}

Start-Process $Url
Write-Host "Opened: $Url"
Write-Host "In MetaMask click Approve when prompted, then Import account with the copied key."
