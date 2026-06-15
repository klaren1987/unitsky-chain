# UST Pool Watchdog — install Windows Task Scheduler job.
# Copies pool-watchdog.py into the miner container and runs it every 30 minutes.
# Run as Administrator:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup-pool-watchdog.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TaskName = "UST-Pool-Watchdog"
$ScriptPath = Join-Path $Root "scripts\pool-watchdog.py"
$EnvFile = Join-Path $Root ".env"
$Container = "ust-miner-local"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "pool-watchdog.py not found at $ScriptPath"
}

# Parse .env file
$envVars = @{}
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $parts = $line -split '=', 2
            $envVars[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

$deployerKey = $envVars["USST_DEPLOYER_KEY"]
$contractAddr = $envVars["USST_CONTRACT_ADDRESS"]
$chainId = $envVars["USST_CHAIN_ID"]
$rpcPublic = $envVars["USST_RPC_PUBLIC"]

# Read contract address from .env.miner if not in .env
$envMiner = Join-Path $Root ".env.miner"
if (-not $contractAddr -and (Test-Path $envMiner)) {
    Get-Content $envMiner | ForEach-Object {
        if ($_ -match '^USST_CONTRACT_ADDRESS=(.+)$') {
            $contractAddr = $Matches[1].Trim()
        }
    }
}

if (-not $deployerKey) {
    Write-Error "USST_DEPLOYER_KEY not found in $EnvFile"
}
if (-not $contractAddr) {
    Write-Error "USST_CONTRACT_ADDRESS not found in .env or .env.miner"
}

Write-Host "Deployer key:     $($deployerKey.Substring(0,10))..."
Write-Host "Contract address: $contractAddr"
Write-Host "Container:        $Container"

# Build the PowerShell command that runs inside the task
$watchdogCmd = @"
docker cp "$ScriptPath" ${Container}:/app/scripts/pool-watchdog.py; ``
docker exec ``
  -e USST_DEPLOYER_KEY=$deployerKey ``
  -e USST_CONTRACT_ADDRESS=$contractAddr ``
  -e USST_CHAIN_ID=${chainId:-778889} ``
  -e USST_POOL_THRESHOLD=1000 ``
  -e USST_POOL_REFILL=5000 ``
  $Container python /app/scripts/pool-watchdog.py
"@

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command `"$watchdogCmd`""

$triggers = @(
    (New-ScheduledTaskTrigger -AtStartup),
    (New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 30) `
        -RepetitionDuration (New-TimeSpan -Days 3650))
)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Auto-refund UST mining pool when balance < 1000 UST" | Out-Null

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered."
Write-Host "Interval: every 30 minutes + at system startup"
Write-Host ""
Write-Host "Running watchdog now..."
Write-Host "---"

docker cp $ScriptPath "${Container}:/app/scripts/pool-watchdog.py"
docker exec `
    -e "USST_DEPLOYER_KEY=$deployerKey" `
    -e "USST_CONTRACT_ADDRESS=$contractAddr" `
    -e "USST_CHAIN_ID=${chainId}" `
    -e "USST_POOL_THRESHOLD=1000" `
    -e "USST_POOL_REFILL=5000" `
    $Container python /app/scripts/pool-watchdog.py

Write-Host "---"
Write-Host "Done. Pool watchdog is active."
