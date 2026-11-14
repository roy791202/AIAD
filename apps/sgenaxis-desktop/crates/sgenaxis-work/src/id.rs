//! Stable [`ProjectId`] from canonical root (deterministic; no OS UUID).

use std::fmt;

/// Opaque project identity. Stable across rebinds; derived once at first register.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ProjectId(String);

impl ProjectId {
    pub fn new(raw: impl Into<String>) -> Self {
        Self(raw.into())
    }

    /// Deterministic id from a canonical root path (WORK-001: stable Project ID).
    pub fn from_canonical_root(canonical: &str) -> Self {
        let digest = fnv1a64(canonical.as_bytes());
        Self(format!("proj_{digest:016x}"))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for ProjectId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl AsRef<str> for ProjectId {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    const OFFSET: u64 = 0xcbf29ce484222325;
    const PRIME: u64 = 0x100000001b3;
    let mut hash = OFFSET;
    for b in bytes {
        hash ^= u64::from(*b);
        hash = hash.wrapping_mul(PRIME);
    }
    hash
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn same_canonical_yields_same_id() {
        let a = ProjectId::from_canonical_root("/fake/專案 A");
        let b = ProjectId::from_canonical_root("/fake/專案 A");
        assert_eq!(a, b);
        assert!(a.as_str().starts_with("proj_"));
    }

    #[test]
    fn different_roots_differ() {
        let a = ProjectId::from_canonical_root("/fake/A");
        let b = ProjectId::from_canonical_root("/fake/B");
        assert_ne!(a, b);
    }
}
