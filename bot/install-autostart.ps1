# One-time setup: makes Reel Bot start hidden every time you log into Windows,
# then starts it right now. Run from the reel-bot folder:  .\install-autostart.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$domain = (Get-Content ".env" | Where-Object { $_ -match "^NGROK_DOMAIN=" }) -replace "^NGROK_DOMAIN=", ""
if (-not $domain.Trim()) {
    $domain = (Read-Host "Your ngrok domain (example: something.ngrok-free.app)").Trim()
    $domain = $domain -replace "^https?://", "" -replace "/.*$", ""
    $envLines = @(Get-Content ".env" | Where-Object { $_ -notmatch "^NGROK_DOMAIN=" }) + "NGROK_DOMAIN=$domain"
    [IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), $envLines, (New-Object Text.UTF8Encoding $false))
}

$pwsh = (Get-Command pwsh).Source
$action = New-ScheduledTaskAction -Execute $pwsh `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-bot.ps1`"" `
    -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Register-ScheduledTask -TaskName "Reel Bot" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "Reel Bot"

Write-Host ""
Write-Host "Reel Bot now starts automatically with Windows, hidden." -ForegroundColor Green
Write-Host "Webhook URL for Meta (step 3, Callback URL):" -ForegroundColor Yellow
Write-Host "https://$($domain.Trim())/webhook"
