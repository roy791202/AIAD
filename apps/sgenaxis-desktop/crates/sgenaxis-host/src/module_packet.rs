//! Explicit read-only application orchestration; lexical containment only.
use sgenaxis_ports::FileSystemPort;
use sgenaxis_spec::packet::{
    project_module_packet, source_sha256, EssDecoderPort, ExportRequest, ModulePacket, PacketError,
    PacketFreshness, SourceProvenance,
};
fn source_path(root: &str, path: &str) -> Result<String, PacketError> {
    if root.trim().is_empty() || path.trim().is_empty() {
        return Err(PacketError::new(
            "INVALID_REQUEST",
            "project root and relative path required",
        ));
    }
    if path.starts_with(['/', '\\'])
        || path.contains(':')
        || path.contains('\0')
        || path.split(['/', '\\']).any(|c| c == ".." || c.is_empty())
    {
        return Err(PacketError::new(
            "INVALID_PATH",
            "source must be a project-relative path without traversal, drive or ADS",
        ));
    }
    if !path.to_ascii_lowercase().ends_with(".ess") {
        return Err(PacketError::new(
            "UNSUPPORTED_SOURCE",
            "only explicit .ess sources supported",
        ));
    }
    Ok(format!(
        "{}/{}",
        root.trim_end_matches(['/', '\\']),
        path.replace('\\', "/")
    ))
}
pub fn export_module_packet(
    fs: &dyn FileSystemPort,
    decoder: &dyn EssDecoderPort,
    project_root: &str,
    request: &ExportRequest,
) -> Result<ModulePacket, PacketError> {
    if request.module_id.trim().is_empty()
        || request.task_id.trim().is_empty()
        || request.limits.max_depth == 0
        || request.limits.max_elements == 0
        || request.limits.max_source_bytes == 0
    {
        return Err(PacketError::new(
            "INVALID_REQUEST",
            "module, task and positive limits required",
        ));
    }
    let path = source_path(project_root, &request.relative_path)?;
    let bytes = fs
        .read(&path)
        .map_err(|e| PacketError::new("SOURCE_READ_FAILED", e.to_string()))?;
    if bytes.len() > request.limits.max_source_bytes {
        return Err(PacketError::new(
            "SOURCE_TOO_LARGE",
            "source exceeds byte limit after read",
        ));
    }
    let hash = source_sha256(&bytes);
    if request
        .expected_source_sha256
        .as_ref()
        .is_some_and(|v| v != &hash)
    {
        return Err(PacketError::new(
            "PACKET_STALE",
            "expected source hash differs",
        ));
    }
    let root = decoder.decode(&bytes, &request.limits)?;
    let packet = project_module_packet(
        &root,
        project_root,
        request,
        SourceProvenance {
            relative_path: request.relative_path.clone(),
            sha256: hash,
            format: "eluslot.ess".into(),
            format_version: "1".into(),
        },
    )?;
    let recheck = fs
        .read(&path)
        .map_err(|e| PacketError::new("SOURCE_READ_FAILED", e.to_string()))?;
    if recheck != bytes {
        return Err(PacketError::new(
            "SOURCE_CHANGED",
            "source changed during extraction",
        ));
    }
    Ok(packet)
}
pub fn check_module_packet_freshness(
    fs: &dyn FileSystemPort,
    project_root: &str,
    packet: &ModulePacket,
) -> Result<PacketFreshness, PacketError> {
    if project_root != packet.project_root {
        return Err(PacketError::new(
            "SOURCE_BINDING_MISMATCH",
            "packet belongs to another project root",
        ));
    }
    let path = source_path(project_root, &packet.source.relative_path)?;
    let bytes = fs
        .read(&path)
        .map_err(|e| PacketError::new("SOURCE_READ_FAILED", e.to_string()))?;
    Ok(if source_sha256(&bytes) == packet.source.sha256 {
        PacketFreshness::Current
    } else {
        PacketFreshness::Stale
    })
}
