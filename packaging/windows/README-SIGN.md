# Windows Authenticode signing — stub + live

## Live path — PD-REMAIN-SIGN-LIVE-01

**BDD:** `BDD-PD-REMAIN-SIGN-LIVE-01` — certificate present → **real** `signtool sign` + `signtool verify /pa`, hang on Build Result; no certificate → **NOT RUN** (never forge **PASS**). Buying a cert is an **owner decision** elsewhere — this path never forces purchase.

```powershell
python packaging/windows/sign_live.py
python packaging/windows/sign-live.py
.\packaging\windows\sign-live.ps1
python tools/board/sign_live.py   # Build Result signingStatus hang
```

| Condition | status |
|-----------|--------|
| No cert env | **NOT RUN** |
| Cert set + `--dry-cert` | **BLOCKED** (live refuses harness PASS) |
| Cert set, signtool missing | **BLOCKED** |
| Cert set, target missing / sign or verify fail | **FAIL** |
| Signed + verified, no timestamp URL | **PARTIAL** |
| Signed + timestamp + verified | **PASS** |

Contract: `python packaging/windows/sign_live_contract_selftest.py`

---

## Stub path — PD-SIGN-STUB-01

**BDD:** `BDD-PD-SIGN-STUB-01` — re-runnable signing entry; no certificate / unset env → **NOT RUN**; with certificate → attempt sign; never forge **PASS** from NOT RUN; result can hang on Build Result `signingStatus`.

**Does not** purchase, import, or require buying a code-signing certificate.

## Entry points

```powershell
# From repo root (any of these)
python packaging/windows/sign_authenticode.py
python packaging/windows/sign-authenticode.py
python scripts/pd_sign_stub_01.py
.\packaging\windows\sign-authenticode.ps1
```

Default target: `packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi`  
Result JSON: `packaging/windows/out/sign-authenticode-result.json`

## Certificate env (optional)

| Variable | Role |
|----------|------|
| `AIAD_AUTHENTICODE_CERT` | Path to `.pfx` / `.p12` |
| `AIAD_AUTHENTICODE_PASSWORD` | Optional PFX password |
| `AIAD_AUTHENTICODE_THUMBPRINT` | Cert store SHA1 thumbprint |
| `AIAD_AUTHENTICODE_TIMESTAMP` | RFC3161 timestamp URL (recommended) |

Unset / empty → **`NOT RUN`** (exit 0). Script exists ≠ PASS.

## Status semantics

| Condition | status |
|-----------|--------|
| No cert env | **NOT RUN** |
| Cert set, signtool missing | **BLOCKED** |
| Cert set, target missing / signtool fail | **FAIL** |
| Signed, no timestamp URL | **PARTIAL** |
| Signed + timestamp | **PASS** |

## Build Result hang

```powershell
python packaging/windows/sign_authenticode.py
python tools/board/sign_stub.py
# → prints signingStatus=NOT RUN (typical lab host without cert)
```

Pass `signing_status=load_signing_status()` from `tools/board/sign_stub.py` into `build_result.build_result(...)`.

## Contract tests

```powershell
python packaging/windows/sign_contract_selftest.py
```

## Related

- WiX MSI: `packaging/windows/wix/` (PD-REL-02 / PD-REL-03)
- Build Result vocabulary: `tools/board/build_result.py` (`signingStatus`)
