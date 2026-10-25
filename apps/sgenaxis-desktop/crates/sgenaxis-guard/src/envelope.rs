//! Approved engineering envelope (packet) for GUARD checks.

use crate::path_gate::normalize_path;

/// Kind of RED evidence presented at the start-implementation gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RedKind {
    /// Valid behavioral failure (acceptable to start implementation).
    Behavioral,
    /// Compile/fixture failure — not a valid behavioral RED.
    CompileError,
    /// Environment／infra fault — not a valid behavioral RED.
    EnvironmentFault,
    /// Missing or empty evidence.
    Missing,
}

impl RedKind {
    /// Only behavioral RED may unlock implementation start.
    pub fn is_valid_for_implementation(self) -> bool {
        matches!(self, RedKind::Behavioral)
    }
}

/// Snapshot of RED evidence bound to an envelope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RedEvidence {
    pub kind: RedKind,
}

impl RedEvidence {
    pub fn behavioral() -> Self {
        Self {
            kind: RedKind::Behavioral,
        }
    }

    pub fn compile_error() -> Self {
        Self {
            kind: RedKind::CompileError,
        }
    }

    pub fn missing() -> Self {
        Self {
            kind: RedKind::Missing,
        }
    }
}

/// Engineering envelope: approval + allow／protect path sets + module scope.
///
/// Paths are logical repo-relative strings (forward-slash normalized).
/// No filesystem I/O — callers feed paths from Git／diff／planner.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Envelope {
    pub id: String,
    /// Explicit approval flag (FLOW／SPEC gate).
    pub approved: bool,
    /// Primary module owning this packet (e.g. `"GUARD"`).
    pub primary_module: String,
    /// Declared cross-module integration scope (empty = primary only).
    pub integration_modules: Vec<String>,
    /// Allowlist prefixes／globs (`packages/guard/**`).
    pub allowed_paths: Vec<String>,
    /// Protect list — always rejects even if also allowed.
    pub protected_paths: Vec<String>,
    /// Optional foreign-module path prefix map: module id → path prefix.
    /// Used for MODULE_BOUNDARY_ESCAPE detection.
    pub module_path_prefixes: Vec<(String, String)>,
}

impl Envelope {
    /// Builder with empty lists; caller fills allow／protect／modules.
    pub fn new(id: impl Into<String>, primary_module: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            approved: false,
            primary_module: primary_module.into(),
            integration_modules: Vec::new(),
            allowed_paths: Vec::new(),
            protected_paths: Vec::new(),
            module_path_prefixes: Vec::new(),
        }
    }

    pub fn with_approved(mut self, approved: bool) -> Self {
        self.approved = approved;
        self
    }

    pub fn with_allowed(mut self, paths: impl IntoIterator<Item = impl Into<String>>) -> Self {
        self.allowed_paths = paths.into_iter().map(Into::into).collect();
        self
    }

    pub fn with_protected(mut self, paths: impl IntoIterator<Item = impl Into<String>>) -> Self {
        self.protected_paths = paths.into_iter().map(Into::into).collect();
        self
    }

    pub fn with_integration(
        mut self,
        modules: impl IntoIterator<Item = impl Into<String>>,
    ) -> Self {
        self.integration_modules = modules.into_iter().map(Into::into).collect();
        self
    }

    pub fn with_module_prefix(
        mut self,
        module: impl Into<String>,
        prefix: impl Into<String>,
    ) -> Self {
        self.module_path_prefixes
            .push((module.into(), normalize_path(&prefix.into())));
        self
    }

    /// Stable FNV-1a 64-bit hex over canonical envelope fields (no OS).
    pub fn hash(&self) -> String {
        let mut h = Fnv64::new();
        h.write(self.id.as_bytes());
        h.write(&[u8::from(self.approved)]);
        h.write(self.primary_module.as_bytes());
        for m in &self.integration_modules {
            h.write(b"|i|");
            h.write(m.as_bytes());
        }
        for p in &self.allowed_paths {
            h.write(b"|a|");
            h.write(normalize_path(p).as_bytes());
        }
        for p in &self.protected_paths {
            h.write(b"|p|");
            h.write(normalize_path(p).as_bytes());
        }
        for (m, pref) in &self.module_path_prefixes {
            h.write(b"|m|");
            h.write(m.as_bytes());
            h.write(b"=");
            h.write(pref.as_bytes());
        }
        format!("{:016x}", h.finish())
    }
}

/// Minimal FNV-1a 64-bit (pure; no external crate).
struct Fnv64 {
    state: u64,
}

impl Fnv64 {
    const OFFSET: u64 = 0xcbf29ce484222325;
    const PRIME: u64 = 0x100000001b3;

    fn new() -> Self {
        Self { state: Self::OFFSET }
    }

    fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.state ^= u64::from(b);
            self.state = self.state.wrapping_mul(Self::PRIME);
        }
    }

    fn finish(self) -> u64 {
        self.state
    }
}
