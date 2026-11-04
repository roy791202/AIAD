# PackSpec v1 — cross-platform artifact contract (PD-M4-PACK-SPEC-01)

Defines pack artifact fields shared by **windows / macos / linux**:

| Field | Meaning |
| --- | --- |
| `os` | `windows` \| `macos` \| `linux` |
| `arch` | `x64` \| `arm64` \| `x86` \| `universal` |
| `path` | Repo-relative (or absolute) artifact path |
| `sha256` | 64 hex chars, or empty when missing / NOT RUN |
| `status` | `PASS` \| `FAIL` \| `BLOCKED` \| `NOT RUN` \| `PARTIAL` |

Same status vocabulary as Build Result (`tools/board/build_result.py`).

## SSOT files

| Path | Role |
| --- | --- |
| `packaging/pack-spec.schema.json` | JSON Schema |
| `packaging/pack-spec.v1.json` | v0.1.0 mac\|linux\|win matrix instance |
| `tools/board/pack_spec.py` | Validate / resolve / hang helpers |

## Hang points

- **Build Result** (`PD-BUILD-RESULT-01`): `pack_spec.apply_to_build_result` merges artifacts + `targetMatrix` + requirement trace.
- **releases** (`PD-RELEASE-REC-01`): `pack_spec.to_release_artifacts` / `hang_pack_spec_to_release` via `release_report`.

## Policy

Real pack **PASS is not required**. Missing mac/linux paths stay **NOT RUN**; missing files cannot remain PASS. Do not forge cross-OS green for CI.

```text
python tools/board/pack_spec.py validate packaging/pack-spec.v1.json
python tools/board/pack_spec.py generate --out packaging/pack-spec.v1.json --resolve
python -m pytest tools/board/test_pack_spec.py -q
```
