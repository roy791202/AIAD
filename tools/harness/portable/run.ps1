#Requires -Version 5.1
param(
    [int]$Port = 28790,
    [int]$Stress = 0,
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $Root
if (-not (Test-Path "apps\sgenaxis-desktop\ui\index.html")) {
    throw "UI missing under $Root"
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not on PATH"
}
$pyArgs = @("tools/harness/portable/serve.py", "--port", "$Port")
if ($Stress -gt 0) { $pyArgs += @("--stress", "$Stress") }
Write-Host "Starting portable harness at http://127.0.0.1:$Port/ (stress=$Stress)"
if (-not $NoBrowser) {
    $url = "http://127.0.0.1:$Port/"
    if ($Stress -gt 0) { $url += "?stress=$Stress" }
    Start-Process $url
}
& python @pyArgs
