# Creates .env by asking for each secret. Run from the reel-bot folder:
#   .\setup-env.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ask($label) {
    $v = Read-Host -MaskInput $label
    return $v.Trim().Trim('"').Trim("'")
}

Write-Host ""
Write-Host "Reel Bot setup - paste each value and press Enter." -ForegroundColor Cyan
Write-Host "(Characters are hidden while you paste.)" -ForegroundColor DarkGray
Write-Host ""

$igToken   = Ask "1/4 Instagram access token"
$igSecret  = Ask "2/4 Instagram app secret"
$verify    = Ask "3/4 Verify token (leave empty to generate one)"
$anthropic = Ask "4/4 Anthropic API key"

if ([string]::IsNullOrWhiteSpace($verify)) {
    $verify = -join ((48..57) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
}

$values = @{
    "IG_ACCESS_TOKEN"   = $igToken
    "IG_APP_SECRET"     = $igSecret
    "IG_VERIFY_TOKEN"   = $verify
    "ANTHROPIC_API_KEY" = $anthropic
}

$lines = Get-Content ".env.example" | ForEach-Object {
    $line = $_
    foreach ($k in $values.Keys) {
        if ($line -match "^$k=") { $line = "$k=$($values[$k])" }
    }
    $line
}

[IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), $lines, (New-Object Text.UTF8Encoding $false))

Write-Host ""
Write-Host ".env created." -ForegroundColor Green
foreach ($k in "IG_ACCESS_TOKEN","IG_APP_SECRET","ANTHROPIC_API_KEY") {
    $state = if ($values[$k]) { "filled" } else { "EMPTY" }
    Write-Host ("  {0,-18} {1}" -f $k, $state)
}
Write-Host ""
Write-Host "Your verify token (you will paste this in Meta):" -ForegroundColor Yellow
Write-Host $verify
