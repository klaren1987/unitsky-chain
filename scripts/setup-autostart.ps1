# Enable WireGuard tunnel + Docker Desktop autostart on Windows.
# Run as Administrator (recommended for service startup type changes):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup-autostart.ps1
#
# Parameter:
#   -WgTunnelName  WireGuard tunnel service name (default: primary-wg)
#                  Find your tunnel name with: Get-Service WireGuardTunnel* | Select Name

param(
    [string]$WgTunnelName = "primary-wg"
)

$ErrorActionPreference = "Stop"

Write-Host "==> WireGuard autostart"
$wgServiceNames = @("WireGuardManager", "WireGuardTunnel`$$WgTunnelName")
$wgServices = Get-Service -Name $wgServiceNames -ErrorAction SilentlyContinue
if (-not $wgServices) {
    Write-Warning "WireGuard services not found. Import your tunnel in the WireGuard app first, then re-run this script with -WgTunnelName <tunnel-name>."
} else {
    foreach ($svc in $wgServices) {
        if ($svc.StartType -ne "Automatic") {
            Set-Service -Name $svc.Name -StartupType Automatic
            Write-Host "  $($svc.Name): set to Automatic"
        } else {
            Write-Host "  $($svc.Name): already Automatic"
        }
        if ($svc.Status -ne "Running") {
            Start-Service -Name $svc.Name
            Write-Host "  $($svc.Name): started"
        }
    }
}

Write-Host ""
Write-Host "==> Docker Desktop autostart"
$dockerSettings = Join-Path $env:APPDATA "Docker\settings-store.json"
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

if (-not (Test-Path $dockerExe)) {
    Write-Warning "Docker Desktop not found at $dockerExe"
} else {
    if (Test-Path $dockerSettings) {
        $settings = Get-Content $dockerSettings -Raw | ConvertFrom-Json
        if (-not $settings.AutoStart) {
            $settings.AutoStart = $true
            $json = $settings | ConvertTo-Json -Depth 10 -Compress:$false
            [System.IO.File]::WriteAllText($dockerSettings, $json, [System.Text.UTF8Encoding]::new($false))
            Write-Host "  settings-store.json: AutoStart = true"
        } else {
            Write-Host "  settings-store.json: AutoStart already true"
        }
    } else {
        Write-Warning "Docker settings not found. Enable autostart in Docker Desktop UI."
    }

    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $runValue = "`"$dockerExe`""
    $current = (Get-ItemProperty -Path $runKey -Name "Docker Desktop" -ErrorAction SilentlyContinue)."Docker Desktop"
    if ($current -ne $runValue) {
        Set-ItemProperty -Path $runKey -Name "Docker Desktop" -Value $runValue
        Write-Host "  Registry Run key: Docker Desktop added"
    } else {
        Write-Host "  Registry Run key: already set"
    }
}

$dockerSvc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerSvc -and $dockerSvc.StartType -ne "Automatic") {
    Set-Service -Name "com.docker.service" -StartupType Automatic
    Write-Host "  com.docker.service: set to Automatic"
}

Write-Host ""
Write-Host "Done. WireGuard and Docker Desktop will start automatically after login or reboot."
