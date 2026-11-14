# SGenAxis Design format (`.sgendesign`)

- **format:** `sgenaxis.design`
- **formatVersion:** `1` (integer)
- **Content:** UTF-8 JSON — `meta` + `nodes[]` + optional `selection`
- **Semantics:** design intent only — **not** product release, **not** acceptance PASS
- **Default path:** `design/main.sgendesign` under project root
- **Preview:** `design/build/<name>.preview.html` via `uidesign_build_preview` (communication only)

See `sample.sgendesign` for a minimal fixture.
