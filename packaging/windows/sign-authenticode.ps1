<#
.SYNOPSIS
  PD-SIGN-STUB-01 — Windows Authenticode signing stub (re-runnable).

.DESCRIPTION
  Thin PowerShell entry for the Python stub. Without AIAD_AUTHENTICODE_CERT /
  AIAD_AUTHENTICODE_THUMBPRINT → status NOT RUN (never forged PASS).
  Does not purchase or import certificates.

.EXAMPLE
  .\packaging\windows\sign-authenticode.ps1
  .\packaging\windows\sign-authenticode.ps1 -Target .\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi
#>
[CmdletBinding()]
param(
    [string]$Target = "",
    [string]$OutDir = "",
    [switch]$DryCert
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = (Resolve-Path (Join-Path $Here "..\..")).Path
$Py = Join-Path $Here "sign_authenticode.py"

$argsList = @($Py)
if ($OutDir) { $argsList += @("--out", $OutDir) }
if ($Target) { $argsList += @("--target", $Target) }
if ($DryCert) { $argsList += "--dry-cert" }

Push-Location $Repo
try {
    & python @argsList
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
