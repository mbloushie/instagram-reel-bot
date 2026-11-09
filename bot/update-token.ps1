# Replaces only IG_ACCESS_TOKEN in .env. Run from the reel-bot folder:
#   .\update-token.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$t = (Read-Host -MaskInput "New Instagram access token").Trim().Trim('"').Trim("'")
if (-not $t) { Write-Host "Empty token, nothing changed." -ForegroundColor Red; exit 1 }

$lines = Get-Content ".env" | ForEach-Object {
    if ($_ -match "^IG_ACCESS_TOKEN=") { "IG_ACCESS_TOKEN=$t" } else { $_ }
}
[IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), $lines, (New-Object Text.UTF8Encoding $false))
Write-Host "Token updated. Restart the server for it to take effect." -ForegroundColor Green
