//! PD-UIDESIGNER-FORMAT-01 / BUILD-01 — `.sgendesign` + preview HTML (communication only).
//!
//! Format is SGenAxis-owned (`sgenaxis.design`); not Qt `.ui`. Preview is not product PASS.

use serde::{Deserialize, Serialize};
use sgenaxis_ports::FileSystemPort;

use crate::error::HostError;

pub const DESIGN_FORMAT: &str = "sgenaxis.design";
pub const DESIGN_FORMAT_VERSION: u32 = 1;
pub const DEFAULT_REL_PATH: &str = "design/main.sgendesign";
pub const PREVIEW_BANNER: &str = "SGenAxis Design Preview · 溝通用 · 非產品／非正式 PASS";

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DesignMeta {
    #[serde(default)]
    pub title: String,
    #[serde(default, rename = "updatedAt")]
    pub updated_at: String,
    #[serde(default = "default_stack", rename = "targetStack")]
    pub target_stack: String,
}

fn default_stack() -> String {
    "vanilla-tauri".into()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DesignNode {
    pub id: String,
    #[serde(rename = "type")]
    pub node_type: String,
    #[serde(default, rename = "parentId")]
    pub parent_id: Option<String>,
    #[serde(default)]
    pub props: serde_json::Map<String, serde_json::Value>,
    #[serde(default, rename = "bddHint")]
    pub bdd_hint: String,
    #[serde(default, rename = "tddHint")]
    pub tdd_hint: String,
    #[serde(default, rename = "behaviorHints")]
    pub behavior_hints: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DesignDoc {
    pub format: String,
    #[serde(rename = "formatVersion")]
    pub format_version: u32,
    #[serde(default)]
    pub meta: DesignMeta,
    #[serde(default)]
    pub nodes: Vec<DesignNode>,
    #[serde(default)]
    pub selection: Option<String>,
    /// Always false for design artifacts (never product acceptance).
    #[serde(default)]
    pub product_pass: bool,
}

impl Default for DesignMeta {
    fn default() -> Self {
        Self {
            title: "Untitled Form".into(),
            updated_at: String::new(),
            target_stack: default_stack(),
        }
    }
}

impl DesignDoc {
    pub fn new_blank() -> Self {
        let form_id = "node-form-root";
        Self {
            format: DESIGN_FORMAT.into(),
            format_version: DESIGN_FORMAT_VERSION,
            meta: DesignMeta::default(),
            nodes: vec![DesignNode {
                id: form_id.into(),
                node_type: "Form".into(),
                parent_id: None,
                props: serde_json::Map::from_iter([
                    ("name".into(), serde_json::json!("Form")),
                    ("x".into(), serde_json::json!(0)),
                    ("y".into(), serde_json::json!(0)),
                    ("w".into(), serde_json::json!(800)),
                    ("h".into(), serde_json::json!(600)),
                    ("zIndex".into(), serde_json::json!(0)),
                    ("layout".into(), serde_json::json!("none")),
                ]),
                bdd_hint: String::new(),
                tdd_hint: String::new(),
                behavior_hints: vec![],
            }],
            selection: Some(form_id.into()),
            product_pass: false,
        }
    }

    pub fn validate(&self) -> Result<(), HostError> {
        if self.format != DESIGN_FORMAT {
            return Err(HostError::Settings(format!(
                "invalid design format {:?} — expected {DESIGN_FORMAT}",
                self.format
            )));
        }
        if self.format_version != DESIGN_FORMAT_VERSION {
            return Err(HostError::Settings(format!(
                "unsupported formatVersion {} — expected {DESIGN_FORMAT_VERSION}",
                self.format_version
            )));
        }
        if self.product_pass {
            return Err(HostError::Settings(
                "design artifact must not set product_pass=true".into(),
            ));
        }
        Ok(())
    }
}

pub fn parse_design_json(raw: &str) -> Result<DesignDoc, HostError> {
    let doc: DesignDoc = serde_json::from_str(raw)
        .map_err(|e| HostError::Settings(format!(".sgendesign JSON parse error: {e}")))?;
    doc.validate()?;
    Ok(doc)
}

pub fn serialize_design(doc: &DesignDoc) -> Result<String, HostError> {
    doc.validate()?;
    let mut out = doc.clone();
    out.product_pass = false;
    serde_json::to_string_pretty(&out)
        .map_err(|e| HostError::Settings(format!("serialize design: {e}")))
}

pub fn join_project_rel(project_root: &str, rel: &str) -> Result<String, HostError> {
    let root = project_root.trim();
    if root.is_empty() {
        return Err(HostError::Settings(
            "project_root unbound — bind a project before save/load/build design".into(),
        ));
    }
    if root == "/demo/root" {
        return Err(HostError::Settings(
            "project_root must not be /demo/root".into(),
        ));
    }
    let rel = rel.trim();
    // Validate before pushing: Windows drive components can replace the project root.
    // Colons also introduce NTFS alternate streams, which are not document paths.
    if rel.starts_with(['/', '\\']) || rel.contains(':') {
        return Err(HostError::Settings(
            "design path must be project-relative without a root or drive prefix".into(),
        ));
    }
    if rel.is_empty() {
        return Err(HostError::Settings("relative design path empty".into()));
    }
    let mut p = std::path::PathBuf::from(root);
    for part in rel.replace('\\', "/").split('/') {
        if part.is_empty() || part == "." {
            continue;
        }
        if part == ".." {
            return Err(HostError::Settings(
                "design path must not contain ..".into(),
            ));
        }
        p.push(part);
    }
    Ok(p.to_string_lossy().into_owned())
}

pub fn save_design_file(
    fs: &dyn FileSystemPort,
    project_root: &str,
    rel_path: &str,
    doc: &DesignDoc,
) -> Result<String, HostError> {
    let path = join_project_rel(project_root, rel_path)?;
    let json = serialize_design(doc)?;
    if let Some(parent) = std::path::Path::new(&path).parent() {
        let parent_s = parent.to_string_lossy();
        if !parent_s.is_empty() {
            fs.create_dir_all(&parent_s)
                .map_err(|e| HostError::Settings(format!("mkdir for design save: {e}")))?;
        }
    }
    fs.write_atomic(&path, json.as_bytes())
        .map_err(|e| HostError::Settings(format!("write .sgendesign: {e}")))?;
    Ok(path)
}

pub fn load_design_file(
    fs: &dyn FileSystemPort,
    project_root: &str,
    rel_path: &str,
) -> Result<(DesignDoc, String), HostError> {
    let path = join_project_rel(project_root, rel_path)?;
    let raw = fs
        .read_to_string(&path)
        .map_err(|e| HostError::Settings(format!("read .sgendesign: {e}")))?;
    let doc = parse_design_json(&raw)?;
    Ok((doc, path))
}

/// Build a self-contained interactive HTML preview for communication.
pub fn build_preview_html(doc: &DesignDoc) -> Result<String, HostError> {
    doc.validate()?;
    let title = if doc.meta.title.trim().is_empty() {
        "SGenAxis Design Preview"
    } else {
        doc.meta.title.trim()
    };
    fn prop_num(n: &DesignNode, key: &str, default: i64) -> i64 {
        n.props
            .get(key)
            .and_then(|v| v.as_i64().or_else(|| v.as_f64().map(|f| f as i64)))
            .unwrap_or(default)
    }
    let mut cards = String::new();
    for n in &doc.nodes {
        let name = n
            .props
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or(n.node_type.as_str());
        let bdd = html_escape(&n.bdd_hint);
        let tdd = html_escape(&n.tdd_hint);
        let id = html_escape(&n.id);
        let ty = html_escape(&n.node_type);
        let name_e = html_escape(name);
        let x = prop_num(n, "x", 0);
        let y = prop_num(n, "y", 0);
        let w = prop_num(n, "w", 120);
        let h = prop_num(n, "h", 32);
        let beh = html_escape(&n.behavior_hints.join(", "));
        let style = if n.parent_id.is_none() {
            String::new()
        } else {
            format!("left:{x}px;top:{y}px;width:{w}px;height:{h}px;")
        };
        cards.push_str(&format!(
            r#"<button type="button" class="node" style="{style}" data-id="{id}" data-type="{ty}" data-name="{name_e}" data-bdd="{bdd}" data-tdd="{tdd}" data-beh="{beh}" data-geom="{x},{y},{w},{h}"><span class="tag">{ty}</span><span class="nm">{name_e}</span></button>"#
        ));
    }
    Ok(format!(
        r#"<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title_e} — communication preview</title>
<style>
body{{margin:0;font:14px/1.45 Segoe UI,Microsoft JhengHei,sans-serif;background:#12141a;color:#e8eaef}}
.banner{{position:sticky;top:0;z-index:9;background:#252117;color:#f2b544;border-bottom:1px solid #5b4b29;padding:8px 12px}}
.wrap{{display:grid;grid-template-columns:1fr 280px;gap:12px;padding:12px;min-height:70vh}}
.stage{{background:#1a1d24;border:1px solid #2a3140;border-radius:8px;padding:16px;min-height:360px}}
.form{{border:1px dashed #5b6a82;border-radius:6px;padding:16px;min-height:280px;background:#0f1218;position:relative}}
.nodes{{position:relative;min-height:260px;margin-top:12px}}
.node{{appearance:none;position:absolute;border:1px solid #3a4558;background:#222833;color:#e8eaef;border-radius:6px;padding:8px 10px;cursor:pointer;text-align:left;box-sizing:border-box;overflow:hidden}}
.node[data-type="Form"]{{position:relative;left:auto;top:auto;width:auto;height:auto;display:block;margin-bottom:8px}}
.node:hover,.node:focus{{border-color:#6ea8fe;outline:none}}
.node.is-on{{border-color:#f2b544;box-shadow:0 0 0 1px #f2b54455}}
.tag{{display:block;font-size:11px;color:#9aa3b2}}
.nm{{font-weight:600}}
.side{{background:#1a1d24;border:1px solid #2a3140;border-radius:8px;padding:12px}}
.side h2{{margin:0 0 8px;font-size:13px;color:#9aa3b2;text-transform:uppercase}}
.kv{{margin:6px 0;font-size:13px}}
.kv b{{color:#9aa3b2;font-weight:500;display:inline-block;min-width:4.5rem}}
.hint{{margin-top:10px;padding:8px;background:#141820;border-radius:6px;white-space:pre-wrap;font-size:12px;color:#c5cad3}}
.foot{{padding:8px 12px;color:#9aa3b2;font-size:12px}}
</style>
</head>
<body>
<div class="banner" role="note">{banner}</div>
<div class="wrap">
  <main class="stage">
    <div class="form" id="form">
      <div><strong>{title_e}</strong> <span style="color:#9aa3b2">· {stack}</span></div>
      <div class="nodes" id="nodes">{cards}</div>
    </div>
  </main>
  <aside class="side" aria-label="選取摘要">
    <h2>選取</h2>
    <div class="kv"><b>Name</b> <span id="pName">—</span></div>
    <div class="kv"><b>Type</b> <span id="pType">—</span></div>
    <div class="kv"><b>Id</b> <span id="pId">—</span></div>
    <div class="hint" id="pBdd">點選左側控件檢視 BDD／需求註記</div>
    <div class="hint" id="pTdd" hidden></div>
  </aside>
</div>
<p class="foot">format={fmt} v{ver} · product_pass=false · 非 VERIFY／GA 證據</p>
<script>
(function(){{
  var nodes=document.getElementById('nodes');
  function sel(btn){{
    nodes.querySelectorAll('.node').forEach(function(b){{b.classList.remove('is-on');}});
    btn.classList.add('is-on');
    document.getElementById('pName').textContent=btn.getAttribute('data-name')||'—';
    document.getElementById('pType').textContent=btn.getAttribute('data-type')||'—';
    document.getElementById('pId').textContent=btn.getAttribute('data-id')||'—';
    var bdd=btn.getAttribute('data-bdd')||'';
    var tdd=btn.getAttribute('data-tdd')||'';
    document.getElementById('pBdd').textContent=bdd?('BDD: '+bdd):'（無 BDD 註記）';
    var t=document.getElementById('pTdd');
    var beh=btn.getAttribute('data-beh')||'';
    var geom=btn.getAttribute('data-geom')||'';
    var extra=(geom?('geom '+geom):'')+(beh?(' · behavior '+beh):'');
    if(tdd||extra){{t.hidden=false;t.textContent=(tdd?('TDD: '+tdd+'\n'):'')+extra;}} else {{t.hidden=true;}}
  }}
  nodes.addEventListener('click',function(ev){{
    var btn=ev.target.closest('.node');
    if(!btn) return;
    sel(btn);
  }});
  var first=nodes.querySelector('.node');
  if(first) sel(first);
}})();
</script>
</body>
</html>
"#,
        title_e = html_escape(title),
        banner = html_escape(PREVIEW_BANNER),
        stack = html_escape(&doc.meta.target_stack),
        cards = cards,
        fmt = DESIGN_FORMAT,
        ver = doc.format_version,
    ))
}

pub fn build_preview_file(
    fs: &dyn FileSystemPort,
    project_root: &str,
    doc: &DesignDoc,
    name: &str,
) -> Result<String, HostError> {
    let safe = name
        .trim()
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect::<String>();
    let safe = if safe.is_empty() { "main".into() } else { safe };
    let rel = format!("design/build/{safe}.preview.html");
    let path = join_project_rel(project_root, &rel)?;
    let html = build_preview_html(doc)?;
    if let Some(parent) = std::path::Path::new(&path).parent() {
        let parent_s = parent.to_string_lossy();
        if !parent_s.is_empty() {
            fs.create_dir_all(&parent_s)
                .map_err(|e| HostError::Settings(format!("mkdir preview: {e}")))?;
        }
    }
    fs.write_atomic(&path, html.as_bytes())
        .map_err(|e| HostError::Settings(format!("write preview: {e}")))?;
    Ok(path)
}

/// Local draft for Ask Agent (no product PASS). Used when DryRun／offline.
pub fn ask_agent_draft(node: &DesignNode, user_note: &str) -> (String, String) {
    let name = node
        .props
        .get("name")
        .and_then(|v| v.as_str())
        .unwrap_or(node.node_type.as_str());
    let title = format!("UI·{ty}「{name}」需求", ty = node.node_type);
    let mut bdd = format!(
        "BDD-UI-{id}: Given 設計節點 {ty}「{name}」已選取, When 使用者描述需求, Then 系統應滿足可觀察行為（草稿）。",
        id = node.id,
        ty = node.node_type,
        name = name
    );
    if !node.bdd_hint.trim().is_empty() {
        bdd.push_str("\n既有 bdd_hint: ");
        bdd.push_str(node.bdd_hint.trim());
    }
    if !user_note.trim().is_empty() {
        bdd.push_str("\n使用者註記: ");
        bdd.push_str(user_note.trim());
    }
    bdd.push_str("\n（設計草稿≠產品驗收 PASS）");
    (title, bdd)
}

fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeFileSystem;

    #[test]
    fn project_paths_reject_drive_prefixes_and_absolute_paths() {
        for rel in [
            "scene/C:/outside.ess",
            "scene/C:outside.ess",
            "C:/outside.ess",
            "/outside.ess",
            r"\\server\share\outside.ess",
            "design/main.sgendesign:stream",
        ] {
            assert!(
                join_project_rel("C:/work/project", rel).is_err(),
                "accepted {rel:?}"
            );
        }
        let normal = join_project_rel("C:/work/project", "design/nested/main.sgendesign").unwrap();
        assert!(normal
            .replace('\\', "/")
            .ends_with("/design/nested/main.sgendesign"));
    }

    #[test]
    fn roundtrip_sgendesign() {
        let doc = DesignDoc::new_blank();
        let json = serialize_design(&doc).unwrap();
        let again = parse_design_json(&json).unwrap();
        assert_eq!(again.format, DESIGN_FORMAT);
        assert_eq!(again.nodes.len(), 1);
        assert!(!again.product_pass);
    }

    #[test]
    fn rejects_wrong_format() {
        let err =
            parse_design_json(r#"{"format":"qt.ui","formatVersion":1,"nodes":[]}"#).unwrap_err();
        assert!(err.to_string().contains("sgenaxis.design"), "{err}");
    }

    #[test]
    fn rejects_product_pass_true() {
        let mut doc = DesignDoc::new_blank();
        doc.product_pass = true;
        assert!(serialize_design(&doc).is_err());
    }

    #[test]
    fn preview_contains_banner_and_node() {
        let doc = DesignDoc::new_blank();
        let html = build_preview_html(&doc).unwrap();
        assert!(html.contains(PREVIEW_BANNER));
        assert!(html.contains("product_pass=false"));
        assert!(html.contains("data-id=\"node-form-root\""));
        assert!(html.contains("class=\"node\""));
    }

    #[test]
    fn preview_includes_geometry_for_child() {
        let mut doc = DesignDoc::new_blank();
        doc.nodes.push(DesignNode {
            id: "n-btn".into(),
            node_type: "Button".into(),
            parent_id: Some("node-form-root".into()),
            props: serde_json::Map::from_iter([
                ("name".into(), serde_json::json!("Go")),
                ("x".into(), serde_json::json!(40)),
                ("y".into(), serde_json::json!(50)),
                ("w".into(), serde_json::json!(100)),
                ("h".into(), serde_json::json!(28)),
            ]),
            bdd_hint: String::new(),
            tdd_hint: String::new(),
            behavior_hints: vec!["click".into()],
        });
        let html = build_preview_html(&doc).unwrap();
        assert!(html.contains("data-geom=\"40,50,100,28\""));
        assert!(html.contains("left:40px;top:50px;width:100px;height:28px;"));
        assert!(html.contains("data-beh=\"click\""));
    }

    #[test]
    fn save_load_via_fake_fs() {
        let fs = FakeFileSystem::new();
        let doc = DesignDoc::new_blank();
        let path = save_design_file(&fs, "/work/proj", DEFAULT_REL_PATH, &doc).unwrap();
        assert!(path.replace('\\', "/").ends_with("design/main.sgendesign"));
        let (loaded, _) = load_design_file(&fs, "/work/proj", DEFAULT_REL_PATH).unwrap();
        assert_eq!(loaded.nodes[0].node_type, "Form");
    }

    #[test]
    fn build_preview_file_writes() {
        let fs = FakeFileSystem::new();
        let doc = DesignDoc::new_blank();
        let path = build_preview_file(&fs, "/work/proj", &doc, "demo").unwrap();
        let html = fs.read_to_string(&path).unwrap();
        assert!(html.contains(PREVIEW_BANNER));
    }

    #[test]
    fn ask_draft_mentions_not_pass() {
        let n = &DesignDoc::new_blank().nodes[0];
        let (title, bdd) = ask_agent_draft(n, "要播放列");
        assert!(title.contains("Form"));
        assert!(bdd.contains("≠產品驗收 PASS") || bdd.contains("設計草稿"));
    }
}
