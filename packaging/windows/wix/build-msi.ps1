#Requires -Version 5.1
<#
.SYNOPSIS
  Build SGenAxis Windows MSI with WiX Toolset v4+ (`wix build`).

.DESCRIPTION
  PD-REL-02: stages the real Tauri release exe into payload\, verifies SHA-256
  against packaging.manifest.json, then embeds it via `wix build`.
  Does not call makensis or iscc. Does not run elevated msiexec /qn.

.PARAMETER PayloadDir
  Directory containing SGenAxis.exe (default: .\payload).

.PARAMETER OutDir
  Output directory for the MSI (default: .\out).

.PARAMETER Version
  Package version string (default: 0.1.0).

.PARAMETER TauriReleaseExe
  Absolute or repo-relative path to sgenaxis-desktop.exe. Empty = default under
  apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe.

.PARAMETER SkipStage
  Do not copy from Tauri; use existing payload\SGenAxis.exe (still hash-checked).
#>
[CmdletBinding()]
param(
    [string]$PayloadDir = "",
    [string]$OutDir = "",
    [string]$Version = "0.1.0",
    [string]$TauriReleaseExe = "",
    [switch]$SkipStage
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$RepoRoot = (Resolve-Path (Join-Path $Root "..\..\..")).Path
if (-not $PayloadDir) { $PayloadDir = Join-Path $Root "payload" }
if (-not $OutDir) { $OutDir = Join-Path $Root "out" }
$wxs = Join-Path $Root "SGenAxis.wxs"
$manifestPath = Join-Path $Root "packaging.manifest.json"
$exe = Join-Path $PayloadDir "SGenAxis.exe"
$msiName = "SGenAxis-$Version-windows-x64.msi"
$msiPath = Join-Path $OutDir $msiName

$defaultTauri = Join-Path $RepoRoot "apps\sgenaxis-desktop\src-tauri\target\release\sgenaxis-desktop.exe"
if (-not $TauriReleaseExe) {
    $TauriReleaseExe = $defaultTauri
} elseif (-not [System.IO.Path]::IsPathRooted($TauriReleaseExe)) {
    $TauriReleaseExe = Join-Path $RepoRoot $TauriReleaseExe
}

if (-not (Test-Path -LiteralPath $wxs)) {
    throw "Missing WiX source: $wxs"
}
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Missing packaging manifest: $manifestPath"
}

# --- Stage real Tauri release exe into payload (PD-REL-02) ---
if (-not $SkipStage) {
    if (-not (Test-Path -LiteralPath $TauriReleaseExe)) {
        throw "Missing Tauri release exe: $TauriReleaseExe — build apps/sgenaxis-desktop release first."
    }
    New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null
    Write-Host "Staging Tauri release -> $exe"
    Write-Host "  source: $TauriReleaseExe"
    Copy-Item -LiteralPath $TauriReleaseExe -Destination $exe -Force
}

if (-not (Test-Path -LiteralPath $exe)) {
    throw "Missing payload binary: $exe — stage Tauri release exe first (omit -SkipStage)."
}

# --- SHA-256 verify staged payload vs packaging.manifest.json ---
$manifestJson = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedHash = $null
$expectedBytes = $null
if ($manifestJson.payload) {
    $expectedHash = [string]$manifestJson.payload.sha256
    if ($manifestJson.payload.PSObject.Properties.Name -contains "bytes") {
        $expectedBytes = [int64]$manifestJson.payload.bytes
    }
}
if (-not $expectedHash) {
    throw "packaging.manifest.json missing payload.sha256 (PD-REL-02 contract)."
}
$expectedHash = $expectedHash.ToLowerInvariant()
$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
$actualBytes = (Get-Item -LiteralPath $exe).Length
if ($actualHash -ne $expectedHash) {
    throw "Payload SHA-256 mismatch: got $actualHash, expected $expectedHash ($exe)."
}
if ($null -ne $expectedBytes -and $actualBytes -ne $expectedBytes) {
    throw "Payload size mismatch: got $actualBytes bytes, expected $expectedBytes ($exe)."
}
Write-Host "Payload SHA-256 OK: $actualHash ($actualBytes bytes)"

$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) {
    Write-Error @"
WiX Toolset CLI (`wix`) not found on PATH.
Install WiX v4+ / v5 / v7, then re-run.
Classic candle/light (v3) are optional legacy; this script uses `wix build` only.
NSIS (makensis) and Inno (iscc) are not the primary SGenAxis Windows channel.
"@
    exit 2
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Building $msiName with $($wix.Source) ..."
& wix build $wxs -arch x64 -o $msiPath -b "payload=$PayloadDir"
if ($LASTEXITCODE -ne 0) {
    throw "wix build failed with exit code $LASTEXITCODE"
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $msiPath).Hash.ToLowerInvariant()
$hashFile = "$msiPath.sha256"
Set-Content -LiteralPath $hashFile -Value "$hash  $msiName" -Encoding ascii
Write-Host "MSI:  $msiPath"
Write-Host "SHA256: $hash"
Write-Host "Hash file: $hashFile"
exit 0
