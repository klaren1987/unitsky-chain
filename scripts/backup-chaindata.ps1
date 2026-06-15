param(
    [string]$BackupDir = "$env:USERPROFILE\ust-chaindata-backups",
    [string]$Volume = "tebot_usst-chaindata",
    [int]$KeepCount = 7
)

$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "yyyy-MM-dd_HH-mm"
$archiveName = "chaindata-$ts.tar.gz"
$archivePath = Join-Path $BackupDir $archiveName

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$time = Get-Date -Format "HH:mm:ss"
Write-Host "[$time] Starting chaindata backup..."
Write-Host "  Volume : $Volume"
Write-Host "  Output : $archivePath"

docker run --rm `
    -v "${Volume}:/data:ro" `
    -v "${BackupDir}:/backup" `
    alpine `
    tar czf "/backup/$archiveName" --exclude="./geth.ipc" -C /data . 2>&1 |
    Where-Object { $_ -notmatch "socket ignored" } |
    ForEach-Object { Write-Host "  tar: $_" }

if (-not (Test-Path $archivePath)) {
    Write-Host "ERROR: Archive was not created" -ForegroundColor Red
    exit 1
}

$sizeMB = [Math]::Round((Get-Item $archivePath).Length / 1MB, 1)
$time2 = Get-Date -Format "HH:mm:ss"
Write-Host "[$time2] Done: $archiveName ($sizeMB MB)"

$old = Get-ChildItem $BackupDir -Filter "chaindata-*.tar.gz" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $KeepCount

if ($old) {
    foreach ($f in $old) {
        Remove-Item $f.FullName -Force
        Write-Host "  Removed old backup: $($f.Name)"
    }
}

$kept = (Get-ChildItem $BackupDir -Filter "chaindata-*.tar.gz").Count
Write-Host "  Backups kept: $kept / $KeepCount"
