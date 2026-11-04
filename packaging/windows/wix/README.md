# SGenAxis Windows packaging (WiX) — PD-REL-03

Primary Windows release channel: **WiX → MSI**.  
**Not primary:** NSIS, Inno Setup, portable-zip-only.

PD-REL-02: `build-msi.ps1` stages the **real** Tauri release exe  
(`apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe`) into  
`payload/SGenAxis.exe`, verifies **SHA-256** against `packaging.manifest.json`  
→ `payload.sha256`, then embeds it with `wix build`.

PD-REL-03: **VERIFY-INSTALL** contract — silent install/uninstall checklist +  
runnable `verify-install.ps1` hook. Checklist covers **exit / log / files / shortcut**.  
Without elevation, elevated checks are **NOT RUN** (never forged PASS).  
This card does **not** force elevated `/qn` install for CI green.

Aligns with `docs/PRODUCT-DEVELOPMENT.md` §6.4 and VERIFY-INSTALL.

## Layout

| Path | Role |
|------|------|
| `SGenAxis.wxs` | WiX v4+ package source (Product name SGenAxis, stable UpgradeCode, `MajorUpgrade` removes prior install incl. same-Version rebuilds, Start Menu shortcut) |
| `packaging.manifest.json` | Packager contract + template hashes + payload SHA-256 + verify_install |
| `build-msi.ps1` | Stage Tauri exe → hash gate → `wix build` (not makensis / iscc) |
| `verify-install.checklist.json` | VERIFY-INSTALL checklist (exit / log / files / shortcut) |
| `verify-install.ps1` | Runnable hook — dry/contract always; live `/qn` only if already elevated + `-RunElevated` |
| `payload/` | Staged `SGenAxis.exe` (must match Tauri release digest) |
| `out/` | MSI + `.sha256` + optional verify-install logs/result JSON |

## Prerequisites

1. [WiX Toolset](https://wixtoolset.org/) **v4 / v5 / v7** (`wix.exe` on PATH).  
2. Built Tauri release: `apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe`.

```powershell
where.exe wix
Test-Path D:\AIAD\apps\sgenaxis-desktop\src-tauri\target\release\sgenaxis-desktop.exe
```

## Build MSI (stages + verifies hash)

```powershell
cd D:\AIAD\packaging\windows\wix
.\build-msi.ps1
# optional: -SkipStage if payload\SGenAxis.exe already staged and hash-matched
```

Artifact: `out\SGenAxis-0.1.0-windows-x64.msi` plus `*.sha256`.

## Upgrade / replace prior install

`SGenAxis.wxs` uses a **stable `UpgradeCode`** plus `<MajorUpgrade AllowSameVersionUpgrades="yes" Schedule="afterInstallInitialize">`:

| Scenario | Behavior |
|----------|----------|
| Newer `Version` over older | Old MSI product removed, then new files installed (overwrite under `Program Files\SGenAxis`) |
| Same `Version` (e.g. 0.1.0 rebuild, new ProductCode) | Prior install still removed — avoids duplicate ARP entries / leftover exe |
| Older over newer | Blocked (`DowngradeErrorMessage`) |

This is the MSI-native “remove old / cover with new” path — no separate NSIS-style wizard page.  
Prefer bumping SemVer when shipping intentional upgrades; same-version rebuilds remain supported for v0.1 iteration.

Re-run `.\build-msi.ps1` after changing `SGenAxis.wxs` so the on-disk MSI picks up the upgrade table.

## VERIFY-INSTALL (PD-REL-03)

Checklist SSOT: `verify-install.checklist.json`  
Categories: **exit** · **log** · **files** · **shortcut** (aligned to WiX MSI + Start Menu component).

### Contract / dry (no elevation — default)

```powershell
cd D:\AIAD\packaging\windows\wix
.\verify-install.ps1
# → overall PARTIAL (or PASS for non-elevated rows); elevated rows status=NOT RUN
# → out\verify-install-result.json
```

Non-elevated rows check MSI presence + manifest `silent` msiexec `/qn` commands.  
Elevated rows are **NOT RUN** — never reported as PASS without a real elevated run.

### Live silent install / uninstall (PD-ELEV-VERIFY-01 — approved elevated)

```powershell
# Must already be an elevated PowerShell — script does NOT self-elevate.
# Or spawn via Start-Process -Verb RunAs after owner approval (PD-DEC-ELEV).
.\verify-install.ps1 -RunElevated -Card PD-ELEV-VERIFY-01
# → overall PASS when live msiexec /qn install+uninstall asserts; else PARTIAL/NOT RUN/BLOCKED — never forge PASS
```

Equivalent manual operators:

```powershell
msiexec /i D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi /qn /norestart /l*v out\verify-install-install.log
Test-Path "${env:ProgramFiles}\SGenAxis\SGenAxis.exe"
Test-Path "${env:ProgramData}\Microsoft\Windows\Start Menu\Programs\SGenAxis\SGenAxis.lnk"
msiexec /x D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi /qn /norestart /l*v out\verify-install-uninstall.log
```

## Unsupported targets (M4)

| OS | Status |
|----|--------|
| Windows x64 MSI | supported |
| macOS | unsupported (M4) |
| Linux | unsupported (M4) |

## Contract tests

```powershell
cd D:\AIAD
python -m pytest tests/test_pd_rel_03_verify_install.py tests/test_pd_rel_02_wix.py tests/test_pd_rel_01_wix.py -v
```

## Refresh template + payload hashes

After editing templates/scripts, or after a new Tauri release binary:

```powershell
python D:\AIAD\packaging\windows\wix\refresh_manifest_hashes.py
```

## Related

- BDD: `tests/features/pd_rel_03_verify_install.feature`
- Report: `reports/dispatch-pd/PD-REL-03.md`
- Product version: `apps/sgenaxis-desktop/src-tauri/tauri.conf.json` (`0.1.0`)
