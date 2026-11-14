# macOS packaging stub (PD-M4-MAC-STUB-01)

**Format chosen:** app-stub (`.stub` placeholder; not a real `.app` / `.pkg`).

**BDD:** `BDD-PD-M4-MAC-STUB-01` — provide a re-runnable macOS packaging entry; on non-Darwin hosts report **NOT RUN**; never forge **PASS**. Notarize / stapling not required.

## Entry points

```bash
# Cross-platform (recommended)
python packaging/macos/build_macos_stub.py
# Manifest / hyphenated aliases:
python packaging/macos/build_macos.py
python packaging/macos/build-macos-stub.py

# Darwin shell wrapper
bash packaging/macos/build-macos.sh
```

Output: `packaging/macos/out/macos-pack-result.json` with PackSpec-shaped fields:

| Field | Meaning |
|-------|---------|
| `os` | always `macos` (target) |
| `arch` | host arch label (`x64` / `arm64` / …) |
| `path` | stub path on Darwin; `null` when NOT RUN |
| `sha256` | digest on Darwin; `null` when NOT RUN |
| `status` | `PASS` \| `FAIL` \| `BLOCKED` \| `NOT RUN` \| `PARTIAL` |

## Status rules

| Host | Result |
|------|--------|
| Windows / Linux / other | **`NOT RUN`** (exit 0) — script exists ≠ PASS |
| Darwin | writes placeholder `.stub` → **`PARTIAL`** (stub only; no notarize/stapling PASS) |

## Contract self-test

```bash
python packaging/macos/contract_selftest.py
```

## Docs

See [`docs/MACOS-PACKAGING-STUB.md`](../../docs/MACOS-PACKAGING-STUB.md).

## Notarize / stapling（預留 · NOT RUN）

**Card:** `PD-NOTARY-PREP-01` · **BDD:** `BDD-PD-NOTARY-PREP-01`

| Item | Status |
|------|--------|
| Apple notarization (`notarytool` submit) | **NOT RUN** — not executed |
| Stapling (`stapler staple`) | **NOT RUN** — not executed |
| Claim “Apple 公證已完成” | **Forbidden** |

Prep-only steps and host limits: [`docs/MACOS-NOTARIZE-PREP.md`](../../docs/MACOS-NOTARIZE-PREP.md).  
This README and the stub do **not** imply notarize/stapling **PASS**. Result JSON keeps `notarize: false` / `stapling: false`.

## Out of scope

- Notarize / stapling gates (must stay **NOT RUN** until a separate live card with evidence)
- Claiming full cross-platform release from this stub alone
- Implying Apple notarization is complete because docs or this stub exist
