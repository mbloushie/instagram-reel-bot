# Keeps the bot server and the ngrok tunnel running in the background.
# If either one stops (crash, sleep, internet drop), it is restarted within ~10 seconds.
# Started automatically at Windows login by the scheduled task from install-autostart.ps1.

Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\logs" | Out-Null

# Read NGROK_DOMAIN from .env
$domain = @(Get-Content "$PSScriptRoot\.env" | Where-Object { $_ -match "^NGROK_DOMAIN=.+" } | ForEach-Object { $_ -replace "^NGROK_DOMAIN=", "" })[-1]
$domain = $domain.Trim()
if (-not $domain) {
    Add-Content "$PSScriptRoot\logs\supervisor.log" "$(Get-Date -f s) NGROK_DOMAIN missing in .env"
    exit 1
}

function Log($m) { Add-Content "$PSScriptRoot\logs\supervisor.log" "$(Get-Date -f s) $m" }

function Start-Server {
    Log "starting server"
    Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\uvicorn.exe" `
        -ArgumentList "app.main:app", "--port", "8000" `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$PSScriptRoot\logs\server.log" `
        -RedirectStandardError "$PSScriptRoot\logs\server-errors.log"
}

function Start-Tunnel {
    Log "starting ngrok tunnel https://$domain"
    Start-Process -FilePath "ngrok" `
        -ArgumentList "http", "--domain=$domain", "8000", "--log=stdout" `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$PSScriptRoot\logs\tunnel.log" `
        -RedirectStandardError "$PSScriptRoot\logs\tunnel-errors.log"
}

# Clean up anything left from a previous run
& "$PSScriptRoot\stop-bot.ps1" -Quiet -KeepSupervisor

# Keep dependencies up to date (adds new ones like gallery-dl automatically)
Log "installing requirements"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m pip install -q -r "$PSScriptRoot\requirements.txt" *>> "$PSScriptRoot\logs\pip.log"

$server = Start-Server
$tunnel = Start-Tunnel

while ($true) {
    Start-Sleep -Seconds 10
    if ($server.HasExited) { Log "server stopped (code $($server.ExitCode))"; $server = Start-Server }
    if ($tunnel.HasExited) { Log "tunnel stopped (code $($tunnel.ExitCode))"; Start-Sleep 5; $tunnel = Start-Tunnel }
}
