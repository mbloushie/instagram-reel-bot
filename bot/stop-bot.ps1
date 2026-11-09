# Stops the background bot: supervisor, server and tunnel.
param([switch]$Quiet, [switch]$KeepSupervisor)

if (-not $KeepSupervisor) {
    Stop-ScheduledTask -TaskName "Reel Bot" -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='pwsh.exe' OR Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like "*run-bot.ps1*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

Get-Process ngrok, cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name='uvicorn.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*app.main:app*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (-not $Quiet) { Write-Host "Reel Bot stopped." -ForegroundColor Yellow }
