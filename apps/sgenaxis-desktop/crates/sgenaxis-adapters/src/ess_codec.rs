//! Read-only product XML decoder implementing the SPEC-owned output port.
use sgenaxis_spec::packet::{EssDecoderPort, PacketError, PacketLimits, SourceElement};
#[derive(Debug, Default, Clone, Copy)]
pub struct ProductEssDecoder;
impl EssDecoderPort for ProductEssDecoder {
    fn decode(&self, bytes: &[u8], limits: &PacketLimits) -> Result<SourceElement, PacketError> {
        if limits.max_source_bytes == 0 || limits.max_depth == 0 || limits.max_elements == 0 {
            return Err(PacketError::new(
                "INVALID_REQUEST",
                "parse limits must be positive",
            ));
        }
        if bytes.len() > limits.max_source_bytes {
            return Err(PacketError::new(
                "SOURCE_TOO_LARGE",
                "source exceeds byte limit",
            ));
        }
        let xml = std::str::from_utf8(bytes)
            .map_err(|e| PacketError::new("INVALID_XML", e.to_string()))?;
        // The parser rejects actual declarations; literals in CDATA/comments are facts.
        let doc = roxmltree::Document::parse(xml).map_err(|e| {
            let code = if matches!(e, roxmltree::Error::DtdDetected) {
                "XML_DTD_FORBIDDEN"
            } else {
                "INVALID_XML"
            };
            PacketError::new(code, e.to_string())
        })?;
        let mut count = 0;
        for node in doc.descendants().filter(|n| n.is_element()) {
            count += 1;
            if count > limits.max_elements
                || node.ancestors().filter(|n| n.is_element()).count() > limits.max_depth
            {
                return Err(PacketError::new(
                    "XML_LIMIT_EXCEEDED",
                    "XML element or depth limit exceeded",
                ));
            }
            if node.tag_name().namespace().is_some()
                || node.attributes().any(|a| a.namespace().is_some())
            {
                return Err(PacketError::new(
                    "UNSUPPORTED_FORMAT",
                    "namespaced product XML is unsupported",
                ));
            }
        }
        fn capture(n: roxmltree::Node<'_, '_>, selector: String) -> SourceElement {
            let mut ord = std::collections::BTreeMap::<String, usize>::new();
            let children = n
                .children()
                .filter(|n| n.is_element())
                .map(|child| {
                    let name = child.tag_name().name();
                    let i = ord.entry(name.into()).or_default();
                    *i += 1;
                    capture(child, format!("{selector}/{name}[{i}]"))
                })
                .collect();
            SourceElement {
                name: n.tag_name().name().into(),
                attributes: n
                    .attributes()
                    .map(|a| (a.name().into(), a.value().into()))
                    .collect(),
                text: n
                    .children()
                    .filter(|c| c.is_text())
                    .filter_map(|c| c.text())
                    .collect(),
                children,
                selector,
            }
        }
        Ok(capture(
            doc.root_element(),
            format!("/{}[1]", doc.root_element().tag_name().name()),
        ))
    }
}
