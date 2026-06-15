# UST System Status — quick overview.
# Run from repo root:
#   .\scripts\status.ps1

$rpc      = $env:USST_RPC              ?? "http://127.0.0.1:8545"
$contract = $env:USST_CONTRACT_ADDRESS ?? "0x71e63fb263613e0ca086Ef4A995eB5A2D148Ecb0"
$treasury = $env:USST_DEPLOYER_ADDRESS ?? ""
$signer   = $env:USST_SIGNER_ADDRESS   ?? ""

function rpc_call($method, $params = @()) {
    $body = @{jsonrpc="2.0"; id=1; method=$method; params=$params} | ConvertTo-Json -Depth 5
    try {
        (Invoke-RestMethod -Uri $rpc -Method POST -ContentType "application/json" -Body $body -TimeoutSec 5).result
    } catch { $null }
}

function call_contract($selector) {
    rpc_call "eth_call" @(@{to=$contract; data=$selector}, "latest")
}

function hex_to_ust($hex) {
    if (-not $hex -or $hex -eq "0x") { return "0 UST" }
    $clean = $hex -replace "^0x", ""
    while ($clean.Length -lt 64) { $clean = "0" + $clean }
    $bi = [System.Numerics.BigInteger]::Parse("0" + $clean, [System.Globalization.NumberStyles]::HexNumber)
    $ust = [decimal]$bi / [decimal]1e18
    "$([Math]::Round($ust, 4)) UST"
}

function hex_to_dec($hex) {
    if (-not $hex -or $hex -eq "0x") { return 0 }
    $clean = $hex -replace "^0x", ""
    while ($clean.Length -lt 64) { $clean = "0" + $clean }
    [System.Numerics.BigInteger]::Parse("0" + $clean, [System.Globalization.NumberStyles]::HexNumber)
}

function hex_to_block($hex) {
    if (-not $hex) { return 0 }
    [Convert]::ToInt64(($hex -replace "^0x",""), 16)
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  UST Mining Hub - System Status" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Containers
Write-Host "CONTAINERS:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}" 2>$null | ForEach-Object { "  $_" }
Write-Host ""

# WireGuard
Write-Host "WIREGUARD:" -ForegroundColor Yellow
$wgServices = Get-Service "WireGuardTunnel*" -ErrorAction SilentlyContinue
foreach ($svc in $wgServices) {
    $color = if ($svc.Status -eq "Running") { "Green" } else { "Red" }
    Write-Host "  $($svc.Name.Replace('WireGuardTunnel$',''))  $($svc.Status)" -ForegroundColor $color
}
Write-Host ""

# Blockchain
Write-Host "BLOCKCHAIN:" -ForegroundColor Yellow
$blockHex = rpc_call "eth_blockNumber"
if (-not $blockHex) {
    Write-Host "  RPC unavailable at $rpc" -ForegroundColor Red
} else {
    $block = hex_to_block $blockHex
    $poolHex   = call_contract "0x96365d44"
    $diffHex   = call_contract "0x19cae462"
    $rewardHex = call_contract "0x228cb733"
    $minedHex  = call_contract "0x5556db65"
    $balTreasury = if ($treasury) { rpc_call "eth_getBalance" @($treasury, "latest") } else { $null }
    $balSigner   = if ($signer)   { rpc_call "eth_getBalance" @($signer, "latest")   } else { $null }

    $pool   = hex_to_ust $poolHex
    $reward = hex_to_ust $rewardHex
    $diff   = hex_to_dec $diffHex
    $mined  = hex_to_dec $minedHex
    $poolWei   = hex_to_dec $poolHex
    $rewardWei = hex_to_dec $rewardHex
    $proofsLeft = if ($rewardWei -gt 0) { [int]($poolWei / $rewardWei) } else { 0 }

    Write-Host "  Block:       $block"
    Write-Host "  Pool:        $pool (~$proofsLeft proofs left)" -ForegroundColor $(if ($proofsLeft -lt 1000) {"Red"} elseif ($proofsLeft -lt 3000) {"Yellow"} else {"Green"})
    Write-Host "  Difficulty:  $($diff.ToString('N0'))"
    Write-Host "  Reward:      $reward"
    Write-Host "  Total mined: $mined"
    if ($treasury) { Write-Host "  Deployer:    $(hex_to_ust $balTreasury)" }
    if ($signer)   { Write-Host "  Signer bal:  $(hex_to_ust $balSigner)" }
}
Write-Host ""

# Recent miner activity
Write-Host "MINER (last 5 proofs):" -ForegroundColor Yellow
docker logs?? UST-string-miner-local --tail=50 2>$null |
    Where-Object { $_ -match "Mined!" } |
    Select-Object -Last 5 |
    ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
Write-Host ""

# Scheduled tasks
Write-Host "SCHEDULED TASKS:" -ForegroundColor Yellow
@("UST-Pool-Watchdog", "UST-WireGuard-DualRoutes") | ForEach-Object {
    $task = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
    if ($task) {
        $info = Get-ScheduledTaskInfo -TaskName $_ -ErrorAction SilentlyContinue
        $last = if ($info.LastRunTime) { $info.LastRunTime.ToString("yyyy-MM-dd HH:mm") } else { "never" }
        $ok = ($info.LastTaskResult -eq 0)
        $status = if ($ok) { "OK" } else { "FAILED ($($info.LastTaskResult))" }
        $color = if ($ok) { "Green" } else { "Red" }
        Write-Host "  $_ -- last run: $last [$status]" -ForegroundColor $color
    }
}
Write-Host ""

Write-Host "=====================================================" -ForegroundColor Cyan
