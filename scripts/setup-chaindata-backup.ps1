# Register daily chaindata backup as a Windows Task Scheduler job.
# Run as Administrator:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup-chaindata-backup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TaskName = "UST-Chaindata-Backup"
$BackupScript = Join-Path $Root "scripts\backup-chaindata.ps1"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$BackupScript`""

# Daily at 04:00 + at startup (in case machine was off at 04:00)
$triggerDaily = New-ScheduledTaskTrigger -Daily -At "04:00"
$triggerBoot = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $action `
    -Trigger @($triggerDaily, $triggerBoot) `
    -Settings $settings -RunLevel Highest `
    -Description "Daily backup of UST blockchain chaindata Docker volume" | Out-Null

Write-Host "Scheduled task '$TaskName' registered (daily 04:00 + at startup)."
Write-Host ""
Write-Host "Running first backup now..."
& $BackupScript
