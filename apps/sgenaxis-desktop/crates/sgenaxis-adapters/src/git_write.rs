//! Git write gate + credential redaction (PD-GIT-01 / PD-GIT-02).
//!
//! - [`GatedGitWrite`]: default-deny adapter (compose stays safe).
//! - [`redact_credentials`]: strip secrets from error text before surfacing.

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

/// Human-readable reason returned by the default write gate.
pub const GIT_WRITE_GATED_MSG: &str =
    "git write gated (default deny; use StdGitWrite/FakeGitWrite with approval)";

/// Returned when approval was not granted for this mutation.
pub const GIT_WRITE_NOT_APPROVED_MSG: &str = "git write requires approval";

/// Always-deny write adapter. Host boot wires this by default so write entry
/// points exist but cannot mutate a repo until an approving adapter is chosen.
#[derive(Debug, Default, Clone, Copy)]
pub struct GatedGitWrite;

impl GatedGitWrite {
    pub fn new() -> Self {
        Self
    }
}

impl GitWritePort for GatedGitWrite {
    fn commit(
        &self,
        _repo: &str,
        _message: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn push(
        &self,
        _repo: &str,
        _remote: &str,
        _refspec: Option<&str>,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn switch_branch(
        &self,
        _repo: &str,
        _branch: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn set_identity(
        &self,
        _repo: &str,
        _name: &str,
        _email: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn set_ignore(
        &self,
        _repo: &str,
        _contents: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }
}

/// Redact credentials / tokens from git or auth error text (BDD-PD-GIT-02).
///
/// Patterns covered (best-effort, not a full secret scanner):
/// - URL userinfo `scheme://user:pass@host`
/// - URL token `scheme://token@host`
/// - `password=` / `token=` / `Authorization: Bearer …`
pub fn redact_credentials(text: &str) -> String {
    let mut out = redact_url_userinfo(text);
    out = redact_keyed_secrets(&out);
    out = redact_bearer(&out);
    out
}

fn redact_url_userinfo(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(idx) = rest.find("://") {
        out.push_str(&rest[..idx + 3]);
        rest = &rest[idx + 3..];
        let end = rest
            .find(|c: char| c == '/' || c.is_whitespace() || c == '\'' || c == '"')
            .unwrap_or(rest.len());
        let authority = &rest[..end];
        if let Some(at) = authority.find('@') {
            let userinfo = &authority[..at];
            if userinfo.contains(':') {
                out.push_str("***:***");
            } else {
                out.push_str("***");
            }
            out.push('@');
            out.push_str(&authority[at + 1..]);
            rest = &rest[end..];
        } else {
            // No userinfo — copy authority as-is and continue.
            out.push_str(authority);
            rest = &rest[end..];
        }
    }
    out.push_str(rest);
    out
}

fn redact_keyed_secrets(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let lower = text.to_ascii_lowercase();
    let mut i = 0;
    while i < text.len() {
        if lower[i..].starts_with("password=") {
            out.push_str(&text[i..i + 9]);
            i += 9;
            let n = value_len(&text[i..]);
            out.push_str("[REDACTED]");
            i += n;
            continue;
        }
        if lower[i..].starts_with("token=") {
            out.push_str(&text[i..i + 6]);
            i += 6;
            let n = value_len(&text[i..]);
            out.push_str("[REDACTED]");
            i += n;
            continue;
        }
        let ch = text[i..].chars().next().unwrap();
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

fn value_len(s: &str) -> usize {
    s.chars()
        .take_while(|c| !c.is_whitespace() && *c != '\'' && *c != '"' && *c != '&')
        .map(|c| c.len_utf8())
        .sum()
}

fn redact_bearer(text: &str) -> String {
    let lower = text.to_ascii_lowercase();
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < text.len() {
        if lower[i..].starts_with("authorization:") {
            out.push_str(&text[i..i + "authorization:".len()]);
            i += "authorization:".len();
            while i < text.len() && text[i..].chars().next().unwrap().is_whitespace() {
                let ch = text[i..].chars().next().unwrap();
                out.push(ch);
                i += ch.len_utf8();
            }
            if lower[i..].starts_with("bearer ") {
                out.push_str(&text[i..i + "bearer ".len()]);
                i += "bearer ".len();
                out.push_str("[REDACTED]");
                while i < text.len() {
                    let ch = text[i..].chars().next().unwrap();
                    if ch.is_whitespace() {
                        break;
                    }
                    i += ch.len_utf8();
                }
                continue;
            }
            continue;
        }
        let ch = text[i..].chars().next().unwrap();
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

/// Map a raw git stderr into a redacted [`PortError::Git`].
pub fn git_error_redacted(context: &str, stderr: &str) -> PortError {
    let combined = if stderr.trim().is_empty() {
        context.to_string()
    } else {
        format!("{context}: {stderr}")
    };
    PortError::Git(redact_credentials(&combined))
}

#[cfg(test)]
mod redact_unit {
    use super::*;

    #[test]
    fn url_userinfo_redacted() {
        let s = redact_credentials("err https://u:p@host/r.git done");
        assert!(!s.contains("u:p@"));
        assert!(s.contains("***:***@host"));
    }
}
