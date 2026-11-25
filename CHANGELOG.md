# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Cross-reference for release records: `<report>.release.json` next to each Build
Result under `reports/` (release id `v0.1.0`). Release tools no longer write any
board; the board's single source of truth is `docs/board.json`. Git tags are
**optional** and are not created by this document (see PD-CHANGELOG-01).

## [Unreleased]

### Changed — BREAKING (PD-BOARD-GAPS-RELEASE-01)

- `tools/board/release_report.py` CLI: the `append` and `list` subcommands and the
  `--board` option are removed. New `build` subcommand prints one release record
  JSON to stdout, or writes it with `build --out <path>`. Fields are the same as
  `build_release` (`id` / `version` / `kind` / `releasedAt` / `recordedAt` /
  `recordedBy` / `artifacts` / `reportPath` / optional `reportMd`).
- `tools/board/build_result.py` (`generate --record-release`),
  `tools/board/rel_hang_final.py` and `tools/board/rel_hang_post.py` (`hang`):
  `--board` is removed; they write `<report>.release.json` next to the report
  instead of the board. Python callers of `hang_to_release` /
  `hang_final_to_release` / `hang_post_to_release` /
  `pack_spec.hang_pack_spec_to_release` no longer pass `board_path`.

### Removed

- `release_report.append_release`, `release_report.list_releases` and the
  `board_watch` dependency of the release tools.

## [0.1.0] — 2026-10-24

### Added

- SGenAxis Windows x64 MSI candidate (WiX):
  `packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi`
- Structured Build Result tooling (`tools/board/build_result.py`) and release
  record hang (now written as `<report>.release.json`; see [Unreleased])
- Release record API (`tools/board/release_report.py`) for version /
  artifacts / `reportPath` (emits JSON; no longer writes a board)

### Changed — Remain 接通摘要（BDD-PD-REL-CL-REMAIN-01）

Post-Remain desktop wires landed under the same SemVer `0.1.0` candidate
(no MAJOR bump; no git tag from this entry). Summary only — not a claim of
signed / tagged / store GA release:

- **file.new / file.save / file.quit** — Command-path host project new／save／
  quit (UI → Command → host; no stub-only labels for these actions)
- **ports / arch UI** — Settings／ports and architecture panels via Command／
  DispatchHost projection (not adapter-from-UI)
- **work.tags** — batch BDD／TDD tags via `batch_work_tags` → DispatchHost →
  board task projection
- **Live CLI / Live MCP** — approved Live `start_run` paths through
  DispatchHost → EXEC (real-spawn CLI；real-mcp local endpoints); ungated／
  banned targets stay honest **NOT RUN**
- **listen 投影** — FS／Git／Agent listen events → EventBridge →
  `listen_get_projection` → Listen UI panel (host FS／Git watch pump may
  remain NOT RUN)

Anti-forge (explicit): this Remain summary does **not** mean Authenticode
signed, git tag applied, or store／external GA. Signing remains **NOT RUN**;
tags remain optional／owner-gated elsewhere.

### Status (candidate)

| Field | Value |
| --- | --- |
| SemVer | `0.1.0` |
| Release id | `v0.1.0` |
| Build Result | **PARTIAL** — `reports/build-0.1.0-20261024T021741.md` |
| Release record | `<report>.release.json` id=`v0.1.0`, `reportPath` → Build Result above (was board `snapshot.releases` before PD-BOARD-GAPS-RELEASE-01) |
| Artifact | `packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi` |
| Artifact sha256 | `facbfc8112991929b9142514cbea43903d270c4d04cc86715d805eec690ff5fb` |
| Elevated VERIFY-INSTALL | NOT RUN (not a hard gate for this candidate) |
| Signing | NOT RUN |
| macOS / Linux packs | NOT RUN (M4 — out of scope) |

### Notes

- This is a **v0.1.0 candidate**, not a claimed full release PASS.
- Owner gate (PD-DEC-V01-GATE-01): Build Result may be PARTIAL; elevated VERIFY
  and Authenticode are not hard gates for this candidate.
- Compare this entry with:
  - Build Result: `reports/build-0.1.0-20261024T021741.md`
  - Dispatch: `reports/dispatch-pd/PD-BUILD-RESULT-01.md`
  - Release record: `reports/dispatch-pd/PD-RELEASE-REC-01.md`

[0.1.0]: reports/build-0.1.0-20261024T021741.md
