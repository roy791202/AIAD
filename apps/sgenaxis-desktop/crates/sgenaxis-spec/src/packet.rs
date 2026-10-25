//! Owner-approved A: derived .ess module packet, never an approval or writable SSOT.
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacketError {
    pub code: String,
    pub message: String,
}
impl PacketError {
    pub fn new(code: &str, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
}
impl std::fmt::Display for PacketError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.code, self.message)
    }
}
impl std::error::Error for PacketError {}

/// Parser resource bounds; byte limit is checked after the existing FS read.
/// This is not a bounded-I/O or physical filesystem containment guarantee.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacketLimits {
    pub max_source_bytes: usize,
    pub max_depth: usize,
    pub max_elements: usize,
}
impl Default for PacketLimits {
    fn default() -> Self {
        Self {
            max_source_bytes: 8 * 1024 * 1024,
            max_depth: 128,
            max_elements: 100_000,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExportRequest {
    pub relative_path: String,
    pub module_id: String,
    pub task_id: String,
    pub expected_source_sha256: Option<String>,
    pub limits: PacketLimits,
}

/// Infrastructure-neutral captured source facts, preserving order and provenance.
/// No XML library types, file handles, approvals or mutable designer state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceElement {
    pub name: String,
    pub attributes: BTreeMap<String, String>,
    pub text: String,
    pub children: Vec<SourceElement>,
    pub selector: String,
}

/// Output port; adapters translate XML into plain captured facts.
pub trait EssDecoderPort {
    fn decode(&self, bytes: &[u8], limits: &PacketLimits) -> Result<SourceElement, PacketError>;
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceProvenance {
    pub relative_path: String,
    pub sha256: String,
    pub format: String,
    pub format_version: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModuleIdentity {
    pub module_id: String,
    pub slot_id: String,
    pub layer_id: String,
    pub name: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UiContextReference {
    pub ui_node_id: String,
    pub document_ref: String,
    pub embedded_node_ids: Vec<String>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacketDiagnostic {
    pub code: String,
    pub subject: String,
    pub message: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PacketReadiness {
    #[serde(rename = "NOT_READY")]
    NotReady,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PacketFreshness {
    #[serde(rename = "CURRENT")]
    Current,
    #[serde(rename = "PACKET_STALE")]
    Stale,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModulePacket {
    pub packet_format: String,
    pub packet_version: u32,
    pub project_root: String,
    pub task_id: String,
    pub source: SourceProvenance,
    pub module: ModuleIdentity,
    pub nodes: Vec<SourceElement>,
    pub internal_edges: Vec<SourceElement>,
    pub boundary_edges: Vec<SourceElement>,
    pub task: Option<SourceElement>,
    pub ui_context: Vec<UiContextReference>,
    pub diagnostics: Vec<PacketDiagnostic>,
    pub readiness: PacketReadiness,
    pub payload_sha256: String,
}

/// Exact-byte source hash, distinct from existing SPEC revision fingerprints.
pub fn source_sha256(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(bytes))
}

/// Pure module selection/validation/projection. Existing approval stores untouched.
pub fn project_module_packet(
    root: &SourceElement,
    project_root: &str,
    request: &ExportRequest,
    source: SourceProvenance,
) -> Result<ModulePacket, PacketError> {
    use std::collections::{BTreeMap, BTreeSet};
    if project_root.trim().is_empty()
        || request.module_id.trim().is_empty()
        || request.task_id.trim().is_empty()
    {
        return Err(PacketError::new(
            "INVALID_REQUEST",
            "project/module/task required",
        ));
    }
    if root.name != "eluslotScene" || attr(root, "encoding") != "xml" {
        return Err(PacketError::new(
            "UNSUPPORTED_FORMAT",
            "expected XML eluslotScene",
        ));
    }
    format(root, "eluslot.ess", true)?;
    let architecture = section(root, "architecture", true)?.unwrap();
    if attr(architecture, "encoding") != "xml" {
        return Err(PacketError::new(
            "UNSUPPORTED_FORMAT",
            "architecture must be XML",
        ));
    }
    let arch = section(architecture, "eluslotArch", true)?.unwrap();
    format(arch, "eluslot.esml", true)?;
    let work = section(root, "work", false)?;
    let design = section(root, "design", false)?;
    for (s, f) in [(work, "eluslot.es"), (design, "eluslot.esui")] {
        if let Some(s) = s {
            format(s, f, false)?;
            if attr(s, "encoding") != "xml" {
                return Err(PacketError::new(
                    "UNSUPPORTED_FORMAT",
                    "section must use XML encoding",
                ));
            }
        }
    }
    let node_list = section(arch, "nodes", true)?.unwrap();
    let edge_list = section(arch, "edges", true)?.unwrap();
    let nodes = children(node_list, "node");
    let edges = children(edge_list, "edge");
    let mut node_ids = BTreeSet::new();
    let mut edge_ids = BTreeSet::new();
    let mut ports = BTreeSet::new();
    let mut module_ids = BTreeSet::new();
    let mut slots = BTreeSet::new();
    let mut node_map = BTreeMap::new();
    let mut module_map = BTreeMap::new();
    let mut membership = BTreeMap::new();
    let mut port_map = BTreeMap::new();
    for n in &nodes {
        let id = attr(n, "id");
        identity(&mut node_ids, id, "node")?;
        node_map.insert(id, *n);
        for (container, direction) in [("inputs", "input"), ("outputs", "output")] {
            if let Some(ps) = section(n, container, false)? {
                for p in children(ps, "port") {
                    let pid = attr(p, "id");
                    identity(&mut ports, pid, "port")?;
                    if attr(p, "direction") != direction {
                        return Err(PacketError::new(
                            "INVALID_DOCUMENT",
                            format!("port {pid} has wrong direction"),
                        ));
                    }
                    port_map.insert(pid, (id, direction));
                }
            }
        }
        if let Some(ms) = section(n, "modules", false)? {
            if attr(n, "kind") != "Layer" {
                return Err(PacketError::new(
                    "INVALID_DOCUMENT",
                    "module slots require a Layer",
                ));
            }
            for m in children(ms, "module") {
                let mid = attr(m, "moduleId");
                identity(&mut module_ids, mid, "module")?;
                identity(&mut slots, attr(m, "slotId"), "slot")?;
                module_map.insert(mid, (*n, m));
                for member in children(m, "member") {
                    let nid = attr(member, "id");
                    if nid.trim().is_empty() {
                        return Err(PacketError::new("INVALID_IDENTITY", "empty member ID"));
                    }
                    if membership.insert(nid, (mid, id)).is_some() {
                        return Err(PacketError::new(
                            "MEMBERSHIP_MISMATCH",
                            format!("multiple memberships for {nid}"),
                        ));
                    }
                }
            }
        }
    }
    for (nid, (mid, lid)) in &membership {
        let n = node_map.get(nid).ok_or_else(|| {
            PacketError::new("MISSING_REFERENCE", format!("member node {nid} absent"))
        })?;
        if attr(n, "moduleRef") != *mid || attr(n, "layerRef") != *lid {
            return Err(PacketError::new(
                "MEMBERSHIP_MISMATCH",
                format!("node {nid} disagrees with module membership"),
            ));
        }
    }
    for n in &nodes {
        let nid = attr(n, "id");
        let mid = attr(n, "moduleRef");
        let lid = attr(n, "layerRef");
        if !lid.is_empty()
            && !node_map
                .get(lid)
                .is_some_and(|l| attr(l, "kind") == "Layer")
        {
            return Err(PacketError::new(
                "MISSING_REFERENCE",
                format!("layer {lid} absent"),
            ));
        }
        if !mid.is_empty() {
            if !module_map.contains_key(mid) {
                return Err(PacketError::new(
                    "MISSING_REFERENCE",
                    format!("module {mid} absent"),
                ));
            }
            if membership.get(nid) != Some(&(mid, lid)) {
                return Err(PacketError::new(
                    "MEMBERSHIP_MISMATCH",
                    format!("node {nid} missing corresponding membership"),
                ));
            }
        }
        if let Some(ds) = section(n, "dependencies", false)? {
            for d in children(ds, "dependency") {
                if !node_map.contains_key(attr(d, "target")) {
                    return Err(PacketError::new(
                        "MISSING_REFERENCE",
                        format!("dependency target {} absent", attr(d, "target")),
                    ));
                }
            }
        }
    }
    for e in &edges {
        identity(&mut edge_ids, attr(e, "id"), "edge")?;
        for (nk, pk, dir) in [
            ("fromNode", "fromPort", "output"),
            ("toNode", "toPort", "input"),
        ] {
            let nid = attr(e, nk);
            let pid = attr(e, pk);
            if !node_map.contains_key(nid) || port_map.get(pid) != Some(&(nid, dir)) {
                return Err(PacketError::new(
                    "MISSING_REFERENCE",
                    format!("invalid edge {} endpoint {nid}/{pid}", attr(e, "id")),
                ));
            }
        }
    }
    let (layer, module) = module_map.get(request.module_id.as_str()).ok_or_else(|| {
        PacketError::new(
            "MODULE_NOT_FOUND",
            format!("module {} not found", request.module_id),
        )
    })?;
    let selected: BTreeSet<_> = children(module, "member")
        .iter()
        .map(|m| attr(m, "id"))
        .collect();
    let selected_nodes: Vec<_> = nodes
        .iter()
        .filter(|n| selected.contains(attr(n, "id")))
        .map(|n| (*n).clone())
        .collect();
    let mut internal_edges = Vec::new();
    let mut boundary_edges = Vec::new();
    for e in edges {
        let a = attr(e, "fromNode");
        let b = attr(e, "toNode");
        if selected.contains(a) && selected.contains(b) {
            internal_edges.push(e.clone());
        } else if selected.contains(a)
            || selected.contains(b)
            || a == attr(layer, "id")
            || b == attr(layer, "id")
            || (a == request.module_id && attr(node_map[a], "kind") == "Module")
            || (b == request.module_id && attr(node_map[b], "kind") == "Module")
        {
            boundary_edges.push(e.clone());
        }
    }
    let mut task = None;
    if let Some(w) = work {
        let mut all = Vec::new();
        walk(w, &mut all);
        let mut tids = BTreeSet::new();
        for t in all.into_iter().filter(|n| n.name == "task") {
            identity(&mut tids, attr(t, "id"), "task")?;
            if attr(t, "id") == request.task_id {
                task = Some(t.clone());
            }
        }
    }
    let mut diagnostics = Vec::new();
    let mut diag = |code: &str, subject: &str, message: &str| {
        diagnostics.push(PacketDiagnostic {
            code: code.into(),
            subject: subject.into(),
            message: message.into(),
        })
    };
    diag(
        "APPROVAL_UNRESOLVED",
        &request.module_id,
        "Authoritative approval/GUARD/EVID bindings are outside this read-only projection",
    );
    diag(
        "APPROVED_BEHAVIOR_UNRESOLVED",
        &request.module_id,
        "Source hints do not establish approved contracts, BDD or acceptance criteria",
    );
    if selected_nodes.is_empty() {
        diag(
            "MODULE_EMPTY",
            &request.module_id,
            "Module has no captured member nodes",
        );
    }
    if task.is_none() {
        diag(
            "TASK_NOT_FOUND",
            &request.task_id,
            "Requested task absent from work section",
        );
    }
    let mut ui_context = Vec::new();
    for n in &selected_nodes {
        if attr(n, "kind") == "UI" {
            let document_ref = attr(n, "uiDefinitionRef");
            diag(
                "UI_SCOPE_UNRESOLVED",
                attr(n, "id"),
                "Design node ownership is not established by document reference",
            );
            diag(
                "UI_DOCUMENT_UNRESOLVED",
                attr(n, "id"),
                "Document identity cannot be proven by the integrated section alone",
            );
            let mut embedded_node_ids = Vec::new();
            if let Some(d) = design {
                let mut all = Vec::new();
                walk(d, &mut all);
                embedded_node_ids = all
                    .into_iter()
                    .filter(|n| n.name == "node")
                    .map(|n| attr(n, "id").to_string())
                    .collect();
            }
            ui_context.push(UiContextReference {
                ui_node_id: attr(n, "id").into(),
                document_ref: document_ref.into(),
                embedded_node_ids,
            });
        }
    }
    let mut packet = ModulePacket {
        packet_format: "eluslot.module-packet".into(),
        packet_version: 1,
        project_root: project_root.into(),
        task_id: request.task_id.clone(),
        source,
        module: ModuleIdentity {
            module_id: attr(module, "moduleId").into(),
            slot_id: attr(module, "slotId").into(),
            layer_id: attr(layer, "id").into(),
            name: attr(module, "name").into(),
        },
        nodes: selected_nodes,
        internal_edges,
        boundary_edges,
        task,
        ui_context,
        diagnostics,
        readiness: PacketReadiness::NotReady,
        payload_sha256: String::new(),
    };
    packet.payload_sha256 = source_sha256(
        &serde_json::to_vec(&packet)
            .map_err(|e| PacketError::new("INVALID_DOCUMENT", e.to_string()))?,
    );
    Ok(packet)
}
fn attr<'a>(n: &'a SourceElement, key: &str) -> &'a str {
    n.attributes.get(key).map(String::as_str).unwrap_or("")
}
fn children<'a>(n: &'a SourceElement, name: &str) -> Vec<&'a SourceElement> {
    n.children.iter().filter(|c| c.name == name).collect()
}
fn section<'a>(
    n: &'a SourceElement,
    name: &str,
    required: bool,
) -> Result<Option<&'a SourceElement>, PacketError> {
    let found = children(n, name);
    if found.len() > 1 || (required && found.is_empty()) {
        return Err(PacketError::new(
            "INVALID_DOCUMENT",
            format!("expected unique {name} section"),
        ));
    }
    Ok(found.first().copied())
}
fn identity<'a>(
    seen: &mut std::collections::BTreeSet<&'a str>,
    id: &'a str,
    kind: &str,
) -> Result<(), PacketError> {
    if id.trim().is_empty() {
        return Err(PacketError::new(
            "INVALID_IDENTITY",
            format!("empty {kind} ID"),
        ));
    }
    if !seen.insert(id) {
        return Err(PacketError::new(
            "DUPLICATE_ID",
            format!("duplicate {kind}: {id}"),
        ));
    }
    Ok(())
}
fn walk<'a>(n: &'a SourceElement, out: &mut Vec<&'a SourceElement>) {
    out.push(n);
    for c in &n.children {
        walk(c, out)
    }
}
fn format(n: &SourceElement, name: &str, version: bool) -> Result<(), PacketError> {
    if attr(n, "format") != name || (version && attr(n, "formatVersion") != "1") {
        return Err(PacketError::new(
            "UNSUPPORTED_FORMAT",
            format!("unsupported {name} format/version"),
        ));
    }
    Ok(())
}
