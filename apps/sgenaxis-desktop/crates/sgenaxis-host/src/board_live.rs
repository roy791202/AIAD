//! PD-BOARD-LIVE-01 — read-only local PROJECT-BOARD projection.
//!
//! Parses `#board-snapshot` from an HTML file (or raw JSON). **No** HTTP,
//! **no** `:8788` / `:28789` dependency, **no** write-back.
//!
//! Writes (PD-BOARD-SAFE-01): use `tools/board/board_core/snapshot_safe.py` /
//! `board.py` — replace only `#board-snapshot`; never whole-file overwrite the HTML shell.

use serde::Deserialize;
use sgenaxis_ports::FileSystemPort;

use crate::error::HostError;

/// One work-item row extracted from the local board snapshot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SnapshotTask {
    pub id: String,
    pub title: String,
    /// Lamp zone string: `gray`｜`blue`｜`yellow`｜`red`｜`green`.
    pub zone: String,
}

/// Parsed local board snapshot (product data only — not a write store).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct BoardSnapshot {
    pub as_of: Option<String>,
    pub version: Option<String>,
    pub tasks: Vec<SnapshotTask>,
}

#[derive(Debug, Deserialize)]
struct SnapshotFile {
    #[serde(default, rename = "asOf")]
    as_of: Option<String>,
    #[serde(default)]
    version: Option<String>,
    #[serde(default)]
    tasks: Vec<SnapshotTaskSerde>,
}

#[derive(Debug, Deserialize)]
struct SnapshotTaskSerde {
    id: String,
    #[serde(default)]
    title: String,
    #[serde(default = "default_gray")]
    zone: String,
}

fn default_gray() -> String {
    "gray".into()
}

const MARKER: &str = "id=\"board-snapshot\"";

/// Extract the JSON payload of `#board-snapshot` from HTML, or pass through
/// when `text` is already a JSON object.
pub fn extract_snapshot_json(text: &str) -> Result<&str, HostError> {
    let trimmed = text.trim_start();
    if trimmed.starts_with('{') {
        return Ok(trimmed);
    }
    let start = text
        .find(MARKER)
        .ok_or_else(|| HostError::Board("board-snapshot marker missing".into()))?;
    let after_marker = &text[start + MARKER.len()..];
    let gt = after_marker
        .find('>')
        .ok_or_else(|| HostError::Board("board-snapshot tag not closed".into()))?;
    let body = &after_marker[gt + 1..];
    let end = body
        .find("</script>")
        .ok_or_else(|| HostError::Board("board-snapshot script end missing".into()))?;
    let json = body[..end].trim();
    if json.is_empty() {
        return Err(HostError::Board("board-snapshot JSON empty".into()));
    }
    Ok(json)
}

/// Parse snapshot JSON (already extracted) into [`BoardSnapshot`].
pub fn parse_board_snapshot(json: &str) -> Result<BoardSnapshot, HostError> {
    let file: SnapshotFile =
        serde_json::from_str(json).map_err(|e| HostError::Board(format!("parse snapshot: {e}")))?;
    let tasks = file
        .tasks
        .into_iter()
        .filter(|t| !t.id.trim().is_empty())
        .map(|t| SnapshotTask {
            id: t.id,
            title: if t.title.is_empty() {
                "(untitled)".into()
            } else {
                t.title
            },
            zone: normalize_zone(&t.zone),
        })
        .collect();
    Ok(BoardSnapshot {
        as_of: file.as_of,
        version: file.version,
        tasks,
    })
}

fn normalize_zone(raw: &str) -> String {
    match raw.trim().to_ascii_lowercase().as_str() {
        "gray" | "blue" | "yellow" | "red" | "green" => raw.trim().to_ascii_lowercase(),
        _ => "gray".into(),
    }
}

/// Read a local board file via [`FileSystemPort`] and parse `#board-snapshot`.
///
/// Read-only: never writes. Does not open sockets or call `:8788`／`:28789`.
pub fn load_board_file(fs: &dyn FileSystemPort, path: &str) -> Result<BoardSnapshot, HostError> {
    let path = path.trim();
    if path.is_empty() {
        return Err(HostError::Board(
            "board path not set (configure host board_path)".into(),
        ));
    }
    if !fs.exists(path)? {
        return Err(HostError::Board(format!("board file not found: {path}")));
    }
    let raw = fs.read_to_string(path)?;
    let json = extract_snapshot_json(&raw)?;
    parse_board_snapshot(json)
}

#[cfg(test)]
mod tests {
    use sgenaxis_adapters::FakeFileSystem;

    use super::*;

    const MINI_HTML: &str = r#"<!DOCTYPE html><html><body>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T01:00:00+08:00",
  "version": "test",
  "tasks": [
    {"id": "PD-A", "title": "Alpha", "zone": "yellow"},
    {"id": "PD-B", "title": "Beta", "zone": "green"},
    {"id": "", "title": "skip", "zone": "red"}
  ]
}
</script>
</body></html>"#;

    #[test]
    fn extract_and_parse_html_snapshot() {
        let json = extract_snapshot_json(MINI_HTML).expect("extract");
        let snap = parse_board_snapshot(json).expect("parse");
        assert_eq!(snap.tasks.len(), 2);
        assert_eq!(snap.tasks[0].id, "PD-A");
        assert_eq!(snap.tasks[0].zone, "yellow");
        assert_eq!(snap.tasks[1].zone, "green");
    }

    #[test]
    fn parse_raw_json_without_html() {
        let raw = r#"{"tasks":[{"id":"T1","title":"One","zone":"blue"}]}"#;
        let snap = parse_board_snapshot(extract_snapshot_json(raw).unwrap()).unwrap();
        assert_eq!(snap.tasks.len(), 1);
        assert_eq!(snap.tasks[0].zone, "blue");
    }

    #[test]
    fn missing_marker_errors() {
        let err = extract_snapshot_json("<html></html>").expect_err("must fail");
        assert!(err.to_string().contains("marker"));
    }

    #[test]
    fn load_via_fake_fs() {
        let fs = FakeFileSystem::new();
        fs.seed("/repo/docs/PROJECT-BOARD.html", MINI_HTML.as_bytes());
        let snap = load_board_file(&fs, "/repo/docs/PROJECT-BOARD.html").expect("load");
        assert_eq!(snap.tasks.len(), 2);
        assert_eq!(snap.as_of.as_deref(), Some("2026-10-24T01:00:00+08:00"));
    }

    #[test]
    fn missing_file_errors() {
        let fs = FakeFileSystem::new();
        let err = load_board_file(&fs, "/missing.html").expect_err("missing");
        assert!(err.to_string().contains("not found"));
    }

    #[test]
    fn empty_path_errors() {
        let fs = FakeFileSystem::new();
        let err = load_board_file(&fs, "  ").expect_err("empty");
        assert!(err.to_string().contains("not set"));
    }

    #[test]
    fn unknown_zone_becomes_gray() {
        let raw = r#"{"tasks":[{"id":"X","title":"x","zone":"neon"}]}"#;
        let snap = parse_board_snapshot(raw).unwrap();
        assert_eq!(snap.tasks[0].zone, "gray");
    }
}
