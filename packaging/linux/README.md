# Linux packaging stub (PD-M4-LINUX-STUB-01)

**Format chosen:** AppImage (`.deb` not used for this stub).

**BDD:** `BDD-PD-M4-LINUX-STUB-01` — provide a re-runnable Linux packaging entry; on non-Linux hosts report **NOT RUN**; never forge **PASS**. No store publish.

## Entry points

```bash
# Cross-platform (recommended)
python packaging/linux/build_linux_stub.py
# hyphenated alias also works:
python packaging/linux/build-linux-stub.py

# Linux shell wrapper
bash packaging/linux/build-appimage-stub.sh
```

Output: `packaging/linux/out/linux-stub-result.json` with PackSpec-shaped fields:

| Field | Meaning |
|-------|---------|
| `os` | always `linux` (target) |
| `arch` | host arch label (`x64` / `arm64` / …) |
| `path` | stub AppImage path on Linux; `null` when NOT RUN |
| `sha256` | digest on Linux; `null` when NOT RUN |
| `status` | `PASS` \| `FAIL` \| `BLOCKED` \| `NOT RUN` \| `PARTIAL` |

## Status rules

| Host | Result |
|------|--------|
| Windows / macOS / other | **`NOT RUN`** (exit 0) — script exists ≠ PASS |
| Linux | writes placeholder `.AppImage` → **`PARTIAL`** (stub only; not store-ready) |

## Contract self-test

```bash
python packaging/linux/contract_selftest.py
```

## Docs

See [`docs/LINUX-PACKAGING-STUB.md`](../../docs/LINUX-PACKAGING-STUB.md).

## Out of scope

- Distro store / Flathub / Snap publish
- Claiming full cross-platform release from this stub alone
