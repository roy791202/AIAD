//! HOST-derived, transient packet admission. This is separate from the
//! inspection-only `ModulePacket::readiness` marker.

use crate::{authorize_exec_start, GuardExecPass, GuardPacketDto};
use serde::{Deserialize, Serialize};

/// Caller-selected identity and expected snapshot. These values are comparison
/// inputs only; they never confer authority.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacketBoundStartRequest {
    pub expected_project_root: String,
    pub source_path: String,
    pub task_id: String,
    pub module_id: String,
    pub expected_source_sha256: String,
    pub approved_spec_revision: String,
}

/// Facts collected by trusted HOST ports and authorization projections.
/// Callers must not deserialize this structure from IPC.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerifiedPacketFacts {
    pub normalized_project_root: String,
    pub source_path: String,
    pub task_id: String,
    pub module_id: String,
    pub source_sha256: String,
    pub spec_revision: String,
    pub spec_module_id: String,
    pub spec_approved: bool,
    pub spec_content_hash: Option<String>,
    pub task_in_approved_envelope: bool,
    pub module_in_approved_envelope: bool,
    pub envelope_complete: bool,
    pub qualified_red: bool,
    pub ui_references_resolved: bool,
}

/// Field-specific fail-closed rejection from HOST admission derivation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PacketAdmissionRejection {
    ProjectRootMismatch,
    SourcePathOutsideProject,
    SourceChanged,
    TaskNotInApprovedSpec,
    ModuleNotInApprovedSpec,
    SpecRevisionMismatch,
    EnvelopeIncomplete,
    ReadinessEvidenceMissing,
    UiReferenceUnresolved,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "status", content = "reason", rename_all = "snake_case")]
pub enum PacketAdmissionVerdict {
    Admissible,
    Rejected(PacketAdmissionRejection),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PacketBoundStartError {
    Admission(PacketAdmissionRejection),
    GuardDenied(String),
}

/// Both independent predicates required for a packet-bound start. This only
/// composes authorization; reserving WORK state and invoking EXEC remain the
/// responsibility of the DispatchHost start path.
pub fn authorize_packet_bound_start(
    request: &PacketBoundStartRequest,
    facts: &VerifiedPacketFacts,
    guard: &GuardPacketDto,
) -> Result<GuardExecPass, PacketBoundStartError> {
    match derive_packet_admission(request, facts) {
        PacketAdmissionVerdict::Admissible => {}
        PacketAdmissionVerdict::Rejected(reason) => {
            return Err(PacketBoundStartError::Admission(reason));
        }
    }
    if !guard.envelope.approved || guard.envelope.primary_module != request.module_id {
        return Err(PacketBoundStartError::GuardDenied(
            "GUARD_ENVELOPE_BINDING_MISMATCH".into(),
        ));
    }
    authorize_exec_start(guard, Some(request.task_id.clone()))
        .map_err(PacketBoundStartError::GuardDenied)
}

/// Derive HOST admission from verified source/spec/envelope facts.
///
/// The v1 `PacketReadiness::NotReady` marker is intentionally neither read nor
/// rewritten here. It remains a legacy inspection marker, not this transient
/// HOST verdict.
pub fn derive_packet_admission(
    request: &PacketBoundStartRequest,
    facts: &VerifiedPacketFacts,
) -> PacketAdmissionVerdict {
    let expected_root = normalize_root(&request.expected_project_root);
    let actual_root = normalize_root(&facts.normalized_project_root);
    if expected_root.is_none() || expected_root != actual_root {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::ProjectRootMismatch);
    }

    let Some(request_path) = normalize_source_path(&request.source_path) else {
        return PacketAdmissionVerdict::Rejected(
            PacketAdmissionRejection::SourcePathOutsideProject,
        );
    };
    let Some(fact_path) = normalize_source_path(&facts.source_path) else {
        return PacketAdmissionVerdict::Rejected(
            PacketAdmissionRejection::SourcePathOutsideProject,
        );
    };
    if request_path != fact_path {
        return PacketAdmissionVerdict::Rejected(
            PacketAdmissionRejection::SourcePathOutsideProject,
        );
    }

    if request.task_id.trim().is_empty()
        || facts.task_id.trim().is_empty()
        || request.task_id != facts.task_id
        || !facts.task_in_approved_envelope
    {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::TaskNotInApprovedSpec);
    }
    if request.module_id.trim().is_empty()
        || facts.module_id.trim().is_empty()
        || facts.spec_module_id.trim().is_empty()
        || request.module_id != facts.module_id
        || request.module_id != facts.spec_module_id
        || !facts.module_in_approved_envelope
    {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::ModuleNotInApprovedSpec);
    }
    if request.approved_spec_revision.trim().is_empty()
        || facts.spec_revision.trim().is_empty()
        || request.approved_spec_revision != facts.spec_revision
        || !facts.spec_approved
    {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::SpecRevisionMismatch);
    }
    if request.expected_source_sha256.is_empty()
        || facts.source_sha256.is_empty()
        || !is_sha256(&request.expected_source_sha256)
        || !is_sha256(&facts.source_sha256)
        || request.expected_source_sha256 != facts.source_sha256
    {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::SourceChanged);
    }
    if facts
        .spec_content_hash
        .as_deref()
        .map_or(true, str::is_empty)
    {
        return PacketAdmissionVerdict::Rejected(
            PacketAdmissionRejection::ReadinessEvidenceMissing,
        );
    }
    if !facts.envelope_complete {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::EnvelopeIncomplete);
    }
    if !facts.qualified_red {
        return PacketAdmissionVerdict::Rejected(
            PacketAdmissionRejection::ReadinessEvidenceMissing,
        );
    }
    if !facts.ui_references_resolved {
        return PacketAdmissionVerdict::Rejected(PacketAdmissionRejection::UiReferenceUnresolved);
    }
    PacketAdmissionVerdict::Admissible
}

fn normalize_root(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }

    if cfg!(windows) {
        let path = trimmed.replace('\\', "/");
        let (prefix, remainder, unc) = if path.starts_with("//") {
            ("//", path.trim_start_matches('/'), true)
        } else if path.as_bytes().get(1) == Some(&b':')
            && path.as_bytes().get(2) == Some(&b'/')
            && path.as_bytes()[0].is_ascii_alphabetic()
        {
            (&path[..2], &path[3..], false)
        } else {
            return None;
        };
        let components = if unc {
            normalize_unc_components(remainder)?
        } else {
            normalize_components(remainder, 0)?
        };
        let suffix = components.join("/").to_ascii_lowercase();
        return Some(if unc {
            format!("//{suffix}")
        } else if suffix.is_empty() {
            format!("{}:/", prefix[..1].to_ascii_lowercase())
        } else {
            format!("{}:/{suffix}", prefix[..1].to_ascii_lowercase())
        });
    }

    if !trimmed.starts_with('/') {
        return None;
    }
    let components = normalize_components(trimmed.trim_start_matches('/'), 0)?;
    Some(if components.is_empty() {
        "/".into()
    } else {
        format!("/{}", components.join("/"))
    })
}

fn normalize_unc_components(path: &str) -> Option<Vec<String>> {
    let mut raw = path.split('/').filter(|component| !component.is_empty());
    let server = raw.next()?;
    let share = raw.next()?;
    if matches!(server, "." | "..") || matches!(share, "." | "..") {
        return None;
    }

    let mut parts = vec![server.to_string(), share.to_string()];
    for component in raw {
        match component {
            "." => {}
            ".." if parts.len() > 2 => {
                parts.pop();
            }
            ".." => return None,
            value => parts.push(value.to_string()),
        }
    }
    Some(parts)
}

fn normalize_components(path: &str, parent_floor: usize) -> Option<Vec<String>> {
    let mut parts = Vec::new();
    for component in path.split('/') {
        match component {
            "" | "." => {}
            ".." => {
                if parts.len() <= parent_floor {
                    return None;
                }
                parts.pop()?;
            }
            value => parts.push(value.to_string()),
        }
    }
    Some(parts)
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|b| b.is_ascii_hexdigit())
}

fn normalize_source_path(value: &str) -> Option<String> {
    let normalized = value.trim().replace('\\', "/");
    if normalized.is_empty()
        || normalized.starts_with('/')
        || normalized.contains(':')
        || normalized.contains('\0')
        || !normalized.to_ascii_lowercase().ends_with(".ess")
        || normalized
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return None;
    }
    Some(normalized)
}
