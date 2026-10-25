//! Traceable rejection reasons for GUARD decisions (BDD-PD-GUARD-01).

/// Stable machine-readable reason codes (do not rename lightly).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RejectCode {
    /// Envelope not approved for implementation.
    NotApproved,
    /// RED evidence missing or not a valid behavioral RED.
    InvalidRed,
    /// Path outside allowed_scope prefixes/globs.
    PathNotAllowed,
    /// Path matches protected_scope (protect wins over allow).
    PathProtected,
    /// Allowed list cites another module without integration scope.
    ModuleBoundaryEscape,
    /// Path contains traversal (`..`) or escapes worktree root.
    PathTraversal,
}

impl RejectCode {
    pub fn as_str(self) -> &'static str {
        match self {
            RejectCode::NotApproved => "NOT_APPROVED",
            RejectCode::InvalidRed => "INVALID_RED",
            RejectCode::PathNotAllowed => "PATH_NOT_ALLOWED",
            RejectCode::PathProtected => "PATH_PROTECTED",
            RejectCode::ModuleBoundaryEscape => "MODULE_BOUNDARY_ESCAPE",
            RejectCode::PathTraversal => "PATH_TRAVERSAL",
        }
    }
}

impl std::fmt::Display for RejectCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// One rejection with a stable code + human-readable detail (traceable).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RejectReason {
    pub code: RejectCode,
    pub detail: String,
}

impl RejectReason {
    pub fn new(code: RejectCode, detail: impl Into<String>) -> Self {
        Self {
            code,
            detail: detail.into(),
        }
    }

    /// Compact trace token: `CODE:detail`.
    pub fn trace(&self) -> String {
        format!("{}:{}", self.code.as_str(), self.detail)
    }
}

impl std::fmt::Display for RejectReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.trace())
    }
}
