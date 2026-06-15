# Internal wrapper called by Windows Task Scheduler.
# Do not run manually — use setup-pool-watchdog.ps1 to install.
$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$envVars = @{}
foreach ($file in @("$Root\.env", "$Root\.env.miner")) {
    if (Test-Path $file) {
        Get-Content $file | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
                $p = $line -split '=', 2
                $envVars[$p[0].Trim()] = $p[1].Trim()
            }
        }
    }
}

$key = $envVars["USST_DEPLOYER_KEY"]
$addr = $envVars["USST_CONTRACT_ADDRESS"]
$chain = if ($envVars["USST_CHAIN_ID"]) { $envVars["USST_CHAIN_ID"] } else { "778889" }
$container = "ust-miner-local"
$script = "$Root\scripts\pool-watchdog.py"

if (-not $key -or -not $addr) { exit 1 }

docker cp $script "${container}:/app/scripts/pool-watchdog.py" 2>$null
docker exec `
    -e "USST_DEPLOYER_KEY=$key" `
    -e "USST_CONTRACT_ADDRESS=$addr" `
    -e "USST_CHAIN_ID=$chain" `
    -e "USST_POOL_THRESHOLD=1000" `
    -e "USST_POOL_REFILL=5000" `
    $container python /app/scripts/pool-watchdog.py
