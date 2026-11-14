#Requires -Version 5.1
<#
.SYNOPSIS
  PD-REL-03 VERIFY-INSTALL hook — silent install/uninstall checklist runner.

.DESCRIPTION
  Runs the VERIFY-INSTALL checklist against the WiX MSI.
  Without elevation (default): elevated checks are marked NOT RUN (never forged PASS).
  With -RunElevated and an elevated process: executes msiexec /qn install+uninstall
  and asserts exit / log / files / Start Menu shortcut.

  Does not self-elevate. Does not touch :8788. NSIS/Inno are not the channel.

.PARAMETER MsiPath
  Path to SGenAxis-*-windows-x64.msi (default: .\out\SGenAxis-0.1.0-windows-x64.msi).

.PARAMETER OutDir
  Directory for logs + result JSON (default: .\out).

.PARAMETER RunElevated
  Actually run msiexec /qn. Requires an already-elevated PowerShell. Never used to
  force CI green — contract tests pass with NOT RUN when this is absent.

.PARAMETER Version
  Package version (default: 0.1.0).

.PARAMETER Card
  Result JSON card id (default: PD-REL-03). Use PD-ELEV-VERIFY-01 for approved elevated runs.
#>
[CmdletBinding()]
param(
    [string]$MsiPath = "",
    [string]$OutDir = "",
    [string]$Version = "0.1.0",
    [string]$Card = "PD-REL-03",
    [switch]$RunElevated
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $OutDir) { $OutDir = Join-Path $Root "out" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$checklistPath = Join-Path $Root "verify-install.checklist.json"
$manifestPath = Join-Path $Root "packaging.manifest.json"
if (-not $MsiPath) {
    $MsiPath = Join-Path $OutDir "SGenAxis-$Version-windows-x64.msi"
}

function Test-IsElevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Expand-EnvPath([string]$template) {
    $expanded = [Environment]::ExpandEnvironmentVariables($template)
    return $expanded -replace "/", "\"
}

$elevated = Test-IsElevated
$wantLive = [bool]$RunElevated
$canLive = $wantLive -and $elevated

if (-not (Test-Path -LiteralPath $checklistPath)) {
    throw "Missing checklist: $checklistPath"
}
$checklist = Get-Content -LiteralPath $checklistPath -Raw -Encoding UTF8 | ConvertFrom-Json
$checks = @($checklist.checks)

$script:ViResults = @()
$logInstall = Join-Path $OutDir "verify-install-install.log"
$logUninstall = Join-Path $OutDir "verify-install-uninstall.log"
$exePath = Expand-EnvPath "%ProgramFiles%/SGenAxis/SGenAxis.exe"
$shortcutPath = Expand-EnvPath "%ProgramData%/Microsoft/Windows/Start Menu/Programs/SGenAxis/SGenAxis.lnk"

function Add-ViResult {
    param(
        [string]$Id,
        [string]$Category,
        [string]$Status,
        [string]$Detail
    )
    $script:ViResults += [pscustomobject]@{
        id       = $Id
        category = $Category
        status   = $Status
        detail   = $Detail
    }
}

# --- Non-elevated contract checks (always runnable) ---
$msiOk = Test-Path -LiteralPath $MsiPath
if ($msiOk) {
    Add-ViResult -Id "VI-CONTRACT-MSI" -Category "files" -Status "PASS" -Detail "MSI present: $MsiPath"
} else {
    Add-ViResult -Id "VI-CONTRACT-MSI" -Category "files" -Status "FAIL" -Detail "MSI missing: $MsiPath - run build-msi.ps1 first"
}

$silentOk = $false
$silentDetail = "manifest missing"
if (Test-Path -LiteralPath $manifestPath) {
    $man = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $inst = [string]$man.silent.install
    $un = [string]$man.silent.uninstall
    $silentOk = ($inst -match "msiexec" -and $inst -match "/qn" -and $un -match "msiexec" -and $un -match "/qn")
    if ($silentOk) {
        $silentDetail = "silent.install/uninstall are msiexec /qn"
    } else {
        $silentDetail = "silent commands not msiexec /qn: install=$inst uninstall=$un"
    }
}
if ($silentOk) {
    Add-ViResult -Id "VI-CONTRACT-SILENT" -Category "exit" -Status "PASS" -Detail $silentDetail
} else {
    Add-ViResult -Id "VI-CONTRACT-SILENT" -Category "exit" -Status "FAIL" -Detail $silentDetail
}

# --- Elevated live path OR NOT RUN ---
if (-not $canLive) {
    if (-not $wantLive) {
        $why = "RunElevated not set - elevated VERIFY-INSTALL NOT RUN (not forged PASS)"
    } elseif (-not $elevated) {
        $why = "process not elevated - elevated VERIFY-INSTALL NOT RUN (not forged PASS)"
    } else {
        $why = "elevated path unavailable"
    }
    foreach ($c in $checks) {
        if ($c.requires_elevated) {
            Add-ViResult -Id ([string]$c.id) -Category ([string]$c.category) -Status "NOT RUN" -Detail $why
        }
    }
} else {
    if (-not $msiOk) {
        foreach ($c in $checks) {
            if ($c.requires_elevated) {
                Add-ViResult -Id ([string]$c.id) -Category ([string]$c.category) -Status "FAIL" `
                    -Detail "cannot run live VERIFY-INSTALL without MSI"
            }
        }
    } else {
        if (Test-Path -LiteralPath $logInstall) { Remove-Item -LiteralPath $logInstall -Force }
        $pInstall = Start-Process -FilePath "msiexec.exe" -ArgumentList @(
            "/i", $MsiPath, "/qn", "/norestart", "/l*v", $logInstall
        ) -Wait -PassThru
        $codeIn = [int]$pInstall.ExitCode
        if ($codeIn -eq 0) {
            Add-ViResult -Id "VI-EXIT-INSTALL" -Category "exit" -Status "PASS" -Detail "msiexec /i exit=$codeIn"
        } else {
            Add-ViResult -Id "VI-EXIT-INSTALL" -Category "exit" -Status "FAIL" -Detail "msiexec /i exit=$codeIn"
        }

        $logOk = (Test-Path -LiteralPath $logInstall) -and ((Get-Item -LiteralPath $logInstall).Length -gt 0)
        if ($logOk) {
            Add-ViResult -Id "VI-LOG-INSTALL" -Category "log" -Status "PASS" -Detail "log: $logInstall"
        } else {
            Add-ViResult -Id "VI-LOG-INSTALL" -Category "log" -Status "FAIL" -Detail "missing/empty log: $logInstall"
        }

        $exeOk = Test-Path -LiteralPath $exePath
        if ($exeOk) {
            Add-ViResult -Id "VI-FILE-EXE" -Category "files" -Status "PASS" -Detail "found $exePath"
        } else {
            Add-ViResult -Id "VI-FILE-EXE" -Category "files" -Status "FAIL" -Detail "missing $exePath"
        }

        $lnkOk = Test-Path -LiteralPath $shortcutPath
        if ($lnkOk) {
            Add-ViResult -Id "VI-SHORTCUT-STARTMENU" -Category "shortcut" -Status "PASS" -Detail "found $shortcutPath"
        } else {
            Add-ViResult -Id "VI-SHORTCUT-STARTMENU" -Category "shortcut" -Status "FAIL" -Detail "missing $shortcutPath"
        }

        if (Test-Path -LiteralPath $logUninstall) { Remove-Item -LiteralPath $logUninstall -Force }
        $pUn = Start-Process -FilePath "msiexec.exe" -ArgumentList @(
            "/x", $MsiPath, "/qn", "/norestart", "/l*v", $logUninstall
        ) -Wait -PassThru
        $codeUn = [int]$pUn.ExitCode
        if ($codeUn -eq 0) {
            Add-ViResult -Id "VI-EXIT-UNINSTALL" -Category "exit" -Status "PASS" -Detail "msiexec /x exit=$codeUn"
        } else {
            Add-ViResult -Id "VI-EXIT-UNINSTALL" -Category "exit" -Status "FAIL" -Detail "msiexec /x exit=$codeUn"
        }

        Start-Sleep -Seconds 1
        $goneExe = -not (Test-Path -LiteralPath $exePath)
        if ($goneExe) {
            Add-ViResult -Id "VI-FILE-GONE" -Category "files" -Status "PASS" -Detail "removed $exePath"
        } else {
            Add-ViResult -Id "VI-FILE-GONE" -Category "files" -Status "FAIL" -Detail "still present $exePath"
        }

        $goneLnk = -not (Test-Path -LiteralPath $shortcutPath)
        if ($goneLnk) {
            Add-ViResult -Id "VI-SHORTCUT-GONE" -Category "shortcut" -Status "PASS" -Detail "removed $shortcutPath"
        } else {
            Add-ViResult -Id "VI-SHORTCUT-GONE" -Category "shortcut" -Status "FAIL" -Detail "still present $shortcutPath"
        }
    }
}

$statuses = @($script:ViResults | ForEach-Object { $_.status })
$passCount = @($statuses | Where-Object { $_ -eq "PASS" }).Count
if ($statuses -contains "FAIL") {
    $overall = "FAIL"
} elseif ($statuses -contains "NOT RUN") {
    if ($passCount -gt 0) { $overall = "PARTIAL" } else { $overall = "NOT RUN" }
} else {
    $overall = "PASS"
}

$cardId = if ($Card) { [string]$Card } else { "PD-REL-03" }
$elevUnavailable = $wantLive -and -not $elevated
$payloadMap = [ordered]@{
    card                 = $cardId
    elev_card            = "PD-ELEV-VERIFY-01"
    overall              = $overall
    elevated_process     = [bool]$elevated
    run_elevated         = [bool]$wantLive
    live_executed        = [bool]$canLive
    elev_unavailable     = [bool]$elevUnavailable
    elev_unavailable_reason = $(if ($elevUnavailable) { "process not elevated / UAC-admin unavailable - elevated checks NOT RUN (not forged PASS)" } else { $null })
    msi                  = [string]$MsiPath
    checks               = @($script:ViResults)
    categories_covered   = @("exit", "log", "files", "shortcut")
}
$payload = [pscustomobject]$payloadMap

$resultPath = Join-Path $OutDir "verify-install-result.json"
($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $resultPath -Encoding UTF8

Write-Host "VERIFY-INSTALL overall=$overall (elevated_process=$elevated run_elevated=$wantLive live=$canLive)"
foreach ($r in $script:ViResults) {
    Write-Host ("  [{0}] {1} ({2}) - {3}" -f $r.status, $r.id, $r.category, $r.detail)
}
Write-Host "Result JSON: $resultPath"

# Exit 0 when no FAIL (PASS or PARTIAL/NOT RUN are OK for non-elevated contract).
if ($overall -eq "FAIL") { exit 1 }
exit 0
