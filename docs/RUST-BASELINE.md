# Formal Rust baseline proposal

The formal source boundary is `apps/sgenaxis-desktop`. Its workspace and independent
`src-tauri` host require two effective lockfiles: `Cargo.lock` and
`src-tauri/Cargo.lock`. Keep both visible to Git. All nested Cargo `target`
directories are build outputs and are ignored; existing ignore rules remain.

`.github/workflows/rust-gate.yml` proposes a Windows GitHub-hosted gate. It installs
Python 3.12 and Rust stable, records their resolved versions, then executes the
workspace, EXEC all-feature library, and independent Tauri library tests with
`--locked`. Each Cargo step declares its own working directory. A failing command
fails its step. This is not an MSRV declaration and changes no `rust-version`.

Run the source snapshot with:

```powershell
python reports/rust-improvements/baseline/generate_report.py
```

The script records SHA256 source hashes, effective lock hashes, Git status and
HEAD. It excludes build outputs and generates a human-readable `module.html` with
embedded structured data. The snapshot describes a dirty working tree, not a
committed or reproducible release. Parallel workspace edits can change a later
snapshot.

The formal Rust sources are currently untracked. A source baseline is not
established until an owner-approved clean commit includes the intended sources
and both effective locks. Generated `ui/review-results/` reports and the exact
`ui/rust-improvements.html` preview projection are excluded from the inventory;
real UI sources such as `ui/index.html`, `ui/app.js` and `ui/styles.css` remain.
Do not include unrelated WIP. No staging, commit, push,
clean-checkout build, remote CI run, packaging, installation, DCC or live Agent
validation is claimed by this proposal. Existing CI is unchanged. GitHub-hosted
runner entitlement and eventual remote execution remain owner concerns.
