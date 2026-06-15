# Reset MetaMask extension data and related Chrome history (Chrome only)
$ErrorActionPreference = "Stop"
$mm = "nkbihfbeogaeaoehlefnkodbefgpgknn"
$profile = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data\Default"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Closing Chrome..."
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

$toRemove = @(
    Join-Path $profile "Local Extension Settings\$mm"
    Join-Path $profile "IndexedDB\chrome-extension_${mm}_0.indexeddb.leveldb"
    Join-Path $profile "IndexedDB\chrome-extension_${mm}_0.indexeddb.blob"
    Join-Path $profile "Sync Extension Settings\$mm"
)

foreach ($path in $toRemove) {
    if (Test-Path $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "Removed: $path"
    }
}

Get-ChildItem (Join-Path $profile "Session Storage") -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $mm } |
    ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force
        Write-Host "Removed: $($_.FullName)"
    }

$historyDb = Join-Path $profile "History"
if (Test-Path $historyDb) {
    python (Join-Path $root "clear-metamask-history.py") $historyDb
}

# Browser cache (Chrome Default profile)
$cacheDirs = @(
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "Service Worker\CacheStorage",
    "Storage\ext\nkbihfbeogaeaoehlefnkodbefgpgknn"
)
foreach ($dir in $cacheDirs) {
    $path = Join-Path $profile $dir
    if (Test-Path $path) {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Cleared cache: $path"
    }
}

Write-Host "Done. Start Chrome - MetaMask and browser cache cleared."
Write-Host "Run: scripts/open-metamask-setup.ps1"
