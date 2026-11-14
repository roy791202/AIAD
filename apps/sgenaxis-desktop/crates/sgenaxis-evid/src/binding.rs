//! Spec hash + worktree fingerprint — evidence only supports green for matching versions.

/// Version binding stamped onto every evidence record.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct VersionBinding {
    pub spec_hash: String,
    pub worktree_fingerprint: String,
}

impl VersionBinding {
    pub fn new(
        spec_hash: impl Into<String>,
        worktree_fingerprint: impl Into<String>,
    ) -> Self {
        Self {
            spec_hash: spec_hash.into(),
            worktree_fingerprint: worktree_fingerprint.into(),
        }
    }

    /// Whether this binding still matches the live project/spec versions.
    pub fn matches_current(&self, current: &VersionBinding) -> bool {
        self == current
    }
}
