<#
.SYNOPSIS
  PD-REMAIN-SIGN-LIVE-01 — live Windows Authenticode (or honest NOT RUN).

.DESCRIPTION
  Real signtool sign + verify when AIAD_AUTHENTICODE_CERT /
  AIAD_AUTHENTICODE_THUMBPRINT is set. Otherwise status NOT RUN (never forged PASS).
  Does not purchase or import certificates. --DryCert with cert env → BLOCKED (not PASS).

.EXAMPLE
  .\packaging\windows\sign-live.ps1
  .\packaging\windows\sign-live.ps1 -Target .\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi
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
$Py = Join-Path $Here "sign_live.py"

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
