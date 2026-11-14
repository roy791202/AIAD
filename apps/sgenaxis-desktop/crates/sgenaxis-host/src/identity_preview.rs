//! Read-only inspection; does not retain or mutate an active model or draft.
use sgenaxis_adapters::ess_codec::ProductEssDecoder;
use sgenaxis_ports::{FileSystemPort, PortError};
use sgenaxis_spec::identity_preview::{
    inspect_identity_claims, DocumentKind, IdentityError, IdentityInspectionRequest,
    IdentityPreview,
};
use sgenaxis_spec::packet::{EssDecoderPort, PacketLimits, SourceElement};
use std::collections::BTreeSet;

pub fn inspect_document_identity(
    fs: &dyn FileSystemPort,
    request: &IdentityInspectionRequest,
) -> Result<IdentityPreview, IdentityError> {
    if request.path.trim().is_empty() || request.path.contains('\0') {
        return Err(IdentityError::InvalidRequest);
    }
    let bytes = fs.read(&request.path).map_err(read_error)?;
    match request.kind {
        DocumentKind::Design => validate_design(&bytes)?,
        DocumentKind::Ess => validate_ess(&bytes)?,
    }
    let preview = inspect_identity_claims(&bytes, &request.claims)?;
    let current = fs.read(&request.path).map_err(read_error)?;
    if current != bytes {
        return Err(IdentityError::StaleSource);
    }
    Ok(preview)
}
fn read_error(error: PortError) -> IdentityError {
    match error {
        PortError::PermissionDenied(_) => IdentityError::PermissionDenied,
        _ => IdentityError::SourceReadFailed,
    }
}
fn validate_design(bytes: &[u8]) -> Result<(), IdentityError> {
    let raw = std::str::from_utf8(bytes).map_err(|_| IdentityError::MalformedDocument)?;
    let value: serde_json::Value =
        serde_json::from_str(raw).map_err(|_| IdentityError::MalformedDocument)?;
    let object = value.as_object().ok_or(IdentityError::MalformedDocument)?;
    let format = object
        .get("format")
        .and_then(|v| v.as_str())
        .ok_or(IdentityError::MalformedDocument)?;
    let version = object
        .get("formatVersion")
        .and_then(|v| v.as_u64())
        .ok_or(IdentityError::MalformedDocument)?;
    if format != crate::uidesign_doc::DESIGN_FORMAT
        || version != u64::from(crate::uidesign_doc::DESIGN_FORMAT_VERSION)
    {
        return Err(IdentityError::UnsupportedSchema);
    }
    let doc = crate::uidesign_doc::parse_design_json(raw)
        .map_err(|_| IdentityError::MalformedDocument)?;
    let mut ids = BTreeSet::new();
    for node in doc.nodes {
        if node.id.trim().is_empty() {
            return Err(IdentityError::MalformedDocument);
        }
        if !ids.insert(node.id) {
            return Err(IdentityError::DuplicateElementId);
        }
    }
    Ok(())
}
fn validate_ess(bytes: &[u8]) -> Result<(), IdentityError> {
    let root = ProductEssDecoder
        .decode(bytes, &PacketLimits::default())
        .map_err(|_| IdentityError::MalformedDocument)?;
    check_format(&root, "eluslotScene", "eluslot.ess")?;
    if root.attributes.get("encoding").map(String::as_str) != Some("xml") {
        return Err(IdentityError::UnsupportedSchema);
    }
    let architecture = unique_child(&root, "architecture")?;
    if architecture.attributes.get("encoding").map(String::as_str) != Some("xml") {
        return Err(IdentityError::UnsupportedSchema);
    }
    let arch = unique_child(architecture, "eluslotArch")?;
    check_format(arch, "eluslotArch", "eluslot.esml")?;
    unique_child(arch, "nodes")?;
    unique_child(arch, "edges")?;
    validate_ids(&root)
}
fn check_format(node: &SourceElement, name: &str, format: &str) -> Result<(), IdentityError> {
    if node.name != name
        || node.attributes.get("format").map(String::as_str) != Some(format)
        || node.attributes.get("formatVersion").map(String::as_str) != Some("1")
    {
        return Err(IdentityError::UnsupportedSchema);
    }
    Ok(())
}
fn unique_child<'a>(
    node: &'a SourceElement,
    name: &str,
) -> Result<&'a SourceElement, IdentityError> {
    let mut matches = node.children.iter().filter(|c| c.name == name);
    let child = matches.next().ok_or(IdentityError::MalformedDocument)?;
    if matches.next().is_some() {
        return Err(IdentityError::MalformedDocument);
    }
    Ok(child)
}
fn validate_ids(node: &SourceElement) -> Result<(), IdentityError> {
    // IDs are scoped by their containing collection and element kind; port IDs
    // on distinct nodes must not be mistaken for duplicate document elements.
    let mut ids = BTreeSet::new();
    for child in &node.children {
        if let Some(id) = child.attributes.get("id") {
            if id.trim().is_empty() {
                return Err(IdentityError::MalformedDocument);
            }
            if !ids.insert((&child.name, id)) {
                return Err(IdentityError::DuplicateElementId);
            }
        }
        validate_ids(child)?;
    }
    Ok(())
}
