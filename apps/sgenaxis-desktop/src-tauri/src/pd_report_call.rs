//! PD-REPORT-UI-01 — call boundary into `tools/pd_report` (read-only).
//!
//! Spawns a **fixed** `python -m pd_report … --json` argv (not arbitrary shell).
//! Never writes SPEC／EVID. Empty evidence → `NOT RUN`.

use std::path::{Path, PathBuf};
use std::process::Command;

use serde::{Deserialize, Serialize};

/// Args from Vanilla UI → `project_pd_report`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProjectPdReportArgs {
    /// Absolute／relative SPEC JSON. Omit with [`Self::fixture`].
    pub spec_path: Option<String>,
    /// Absolute／relative EVID JSON. Omit with [`Self::fixture`].
    pub evid_path: Option<String>,
    /// Optional out dir; default: a reserved per-call directory under system temp.
    pub out_dir: Option<String>,
    /// Built-in fixture under `tools/pd_report/fixtures/{name}` (`not_run`｜`happy`｜`xss`).
    pub fixture: Option<String>,
}

/// Read-only projection DTO for the report panel.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProjectPdReportDto {
    pub html_path: String,
    pub md_path: String,
    pub fingerprint: String,
    pub evidence_status: String,
    /// Always false — pd_report must not write back specs.
    pub write_back: bool,
    pub html_body: Option<String>,
    pub md_body: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SlimJson {
    html_path: String,
    md_path: String,
    fingerprint: String,
    evidence_status: String,
    write_back: bool,
}

/// Resolve repo `tools/` from the Tauri crate manifest (…/src-tauri → repo root).
pub fn tools_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("tools")
}

pub fn default_fixture_paths(kind: &str) -> (PathBuf, PathBuf) {
    let base = tools_dir().join("pd_report").join("fixtures").join(kind);
    (base.join("spec.json"), base.join("evid.json"))
}

fn python_candidates() -> &'static [&'static str] {
    &["python", "python3", "py"]
}

fn resolve_spec_evid(args: &ProjectPdReportArgs) -> Result<(PathBuf, PathBuf), String> {
    let spec_o = args
        .spec_path
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty());
    let evid_o = args
        .evid_path
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty());
    if let (Some(s), Some(e)) = (spec_o, evid_o) {
        return Ok((PathBuf::from(s), PathBuf::from(e)));
    }
    let kind = args
        .fixture
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or("not_run");
    if !matches!(kind, "not_run" | "happy" | "xss") {
        return Err(format!("unknown fixture {kind:?} (use not_run|happy|xss)"));
    }
    Ok(default_fixture_paths(kind))
}

/// Invoke `python -m pd_report --spec … --evid … --out … --json` (call boundary).
pub fn project_pd_report(args: &ProjectPdReportArgs) -> Result<ProjectPdReportDto, String> {
    let (spec, evid) = resolve_spec_evid(args)?;
    if !spec.is_file() {
        return Err(format!("spec not found: {}", spec.display()));
    }
    if !evid.is_file() {
        return Err(format!("evid not found: {}", evid.display()));
    }

    let spec_before = std::fs::read(&spec).map_err(|e| e.to_string())?;
    let evid_before = std::fs::read(&evid).map_err(|e| e.to_string())?;

    let out_dir = match &args.out_dir {
        Some(p) if !p.trim().is_empty() => PathBuf::from(p),
        _ => reserve_default_output_dir()?,
    };
    std::fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;

    let tools = tools_dir();
    if !tools.join("pd_report").is_dir() {
        return Err(format!(
            "pd_report package missing under {}",
            tools.display()
        ));
    }

    let mut last_err = String::from("no python interpreter found");
    let mut stdout = None;
    for prog in python_candidates() {
        let mut cmd = Command::new(prog);
        if *prog == "py" {
            cmd.arg("-3");
        }
        cmd.args([
            "-m",
            "pd_report",
            "--spec",
            spec.to_str().ok_or("spec path not utf-8")?,
            "--evid",
            evid.to_str().ok_or("evid path not utf-8")?,
            "--out",
            out_dir.to_str().ok_or("out path not utf-8")?,
            "--json",
        ])
        .current_dir(&tools)
        .env("PYTHONPATH", &tools);

        match cmd.output() {
            Ok(out) if out.status.success() => {
                stdout = Some(String::from_utf8_lossy(&out.stdout).into_owned());
                break;
            }
            Ok(out) => {
                last_err = format!(
                    "{} -m pd_report failed ({}): {}",
                    prog,
                    out.status,
                    String::from_utf8_lossy(&out.stderr).trim()
                );
            }
            Err(e) => {
                last_err = format!("spawn {prog}: {e}");
            }
        }
    }

    let raw = stdout.ok_or(last_err)?;
    let line = raw
        .lines()
        .map(str::trim)
        .find(|l| l.starts_with('{'))
        .ok_or_else(|| format!("pd_report --json produced no JSON object: {raw}"))?;
    let slim: SlimJson =
        serde_json::from_str(line).map_err(|e| format!("parse pd_report JSON: {e}; line={line}"))?;

    if slim.write_back {
        return Err("contract violation: write_back must be false".into());
    }

    let spec_after = std::fs::read(&spec).map_err(|e| e.to_string())?;
    let evid_after = std::fs::read(&evid).map_err(|e| e.to_string())?;
    if spec_after != spec_before || evid_after != evid_before {
        return Err("pd_report mutated SPEC/EVID (forbidden)".into());
    }

    let html_body = read_optional(Path::new(&slim.html_path));
    let md_body = read_optional(Path::new(&slim.md_path));

    Ok(ProjectPdReportDto {
        html_path: slim.html_path,
        md_path: slim.md_path,
        fingerprint: slim.fingerprint,
        evidence_status: slim.evidence_status,
        write_back: false,
        html_body,
        md_body,
    })
}

// Reserve with create_dir (not an exists check) so concurrent processes and
// PID reuse cannot select an existing report directory. Explicit out_dir keeps
// its existing caller-controlled destination semantics.
fn reserve_default_output_dir() -> Result<PathBuf, String> {
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT_REPORT: AtomicU64 = AtomicU64::new(0);
    let root = std::env::temp_dir().join("sgenaxis-pd-report");
    std::fs::create_dir_all(&root).map_err(|e| e.to_string())?;
    loop {
        let id = NEXT_REPORT.fetch_add(1, Ordering::Relaxed);
        let candidate = root.join(format!("{}-{id}", std::process::id()));
        match std::fs::create_dir(&candidate) {
            Ok(()) => return Ok(candidate),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(format!("reserve report output directory: {e}")),
        }
    }
}

fn read_optional(path: &Path) -> Option<String> {
    std::fs::read_to_string(path).ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_fixture_projects_not_run_via_pd_report() {
        let (spec, evid) = default_fixture_paths("not_run");
        assert!(spec.is_file(), "required not_run fixture missing");
        let dto = project_pd_report(&ProjectPdReportArgs {
            spec_path: None,
            evid_path: None,
            out_dir: None,
            fixture: Some("not_run".into()),
        }).expect("required pd_report invocation failed");
        assert_eq!(dto.evidence_status, "NOT RUN");
        assert!(!dto.write_back);
        let body = dto.html_body.unwrap_or_default();
        assert!(body.contains("NOT RUN"));
        assert!(!body.contains("PASS"));
        let _ = (spec, evid);
    }

    #[test]
    fn happy_fixture_projects_pass() {
        let dto = project_pd_report(&ProjectPdReportArgs {
            spec_path: None,
            evid_path: None,
            out_dir: None,
            fixture: Some("happy".into()),
        }).expect("required pd_report invocation failed");
        assert_eq!(dto.evidence_status, "PASS");
        assert!(!dto.write_back);
    }

    #[test]
    fn concurrent_default_reports_keep_independent_artifacts() {
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let handles: Vec<_> = ["not_run", "happy"].into_iter().map(|fixture| {
            let barrier = barrier.clone();
            std::thread::spawn(move || {
                barrier.wait();
                project_pd_report(&ProjectPdReportArgs {
                    spec_path: None, evid_path: None, out_dir: None,
                    fixture: Some(fixture.into()),
                }).expect("required concurrent report invocation failed")
            })
        }).collect();
        let reports: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();
        assert_ne!(reports[0].html_path, reports[1].html_path,
            "default calls must not overwrite the same artifact");
        assert_ne!(reports[0].md_path, reports[1].md_path);
        for (dto, expected) in reports.iter().zip(["NOT RUN", "PASS"]) {
            assert_eq!(dto.evidence_status, expected);
            assert!(!dto.write_back);
            let html = std::fs::read_to_string(&dto.html_path).unwrap();
            let md = std::fs::read_to_string(&dto.md_path).unwrap();
            assert_eq!(dto.html_body.as_deref(), Some(html.as_str()));
            assert_eq!(dto.md_body.as_deref(), Some(md.as_str()));
            assert!(html.contains(expected));
            assert!(html.contains(&dto.fingerprint));
            assert!(md.contains(&dto.fingerprint));
        }
        for dto in reports {
            std::fs::remove_dir_all(Path::new(&dto.html_path).parent().unwrap()).unwrap();
        }
    }

}
