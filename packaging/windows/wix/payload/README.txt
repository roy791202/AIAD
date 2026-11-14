SGenAxis WiX payload stage (PD-REL-02)

build-msi.ps1 stages the Tauri Windows release binary here as:

  SGenAxis.exe

Canonical source after `cargo tauri build` / release build:

  apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe

SHA-256 of the staged exe must match packaging.manifest.json → payload.sha256.
Do not ship the tiny scaffold stub; PD-REL-02 requires the real release exe.
macOS / Linux installers remain out of scope (M4); status=unsupported.
