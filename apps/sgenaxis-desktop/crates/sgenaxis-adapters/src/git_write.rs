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

/// Names that would become flags or mutate remotes / switch HEAD.
pub(crate) fn branch_name_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('-')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains(' ')
        || t.ends_with('/')
        || t.contains('\\')
        || t.contains('~')
        || t.contains('^')
        || t.contains(':')
        || t.contains('?')
        || t.contains('*')
        || t.contains('[')
        || lower.contains("..")
        || lower == ".git"
        || lower.contains("/.git/")
        || lower.starts_with(".git/")
        || lower.ends_with("/.git")
        || lower.contains("@{")
        || lower == "head"
        || t.contains("//")
        || matches!(
            lower.as_str(),
            "-c" | "-C"
                | "--force"
                | "-f"
                | "-d"
                | "-D"
                | "-m"
                | "-M"
                | "--move"
                | "--delete"
                | "--set-upstream"
                | "--set-upstream-to"
                | "--unset-upstream"
                | "-u"
                | "--track"
                | "-t"
                | "checkout"
                | "switch"
        )
}

/// Names / URLs that would become flags or widen remote mutations.
pub(crate) fn remote_name_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('-')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains(' ')
        || t.contains('\\')
        || t.contains(':')
        || matches!(
            lower.as_str(),
            "-f" | "--force"
                | "--fetch"
                | "-t"
                | "--tags"
                | "--no-tags"
                | "--mirror"
                | "set-url"
                | "prune"
                | "push"
                | "rm"
                | "remove"
                | "rename"
                | "update"
        )
}

/// Tag names that would become flags, bulk push, force, or branch refspecs.
pub(crate) fn tag_name_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('-')
        || t.starts_with('+')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains(' ')
        || t.contains('\\')
        || t.contains(':')
        || lower.contains("..")
        || lower.contains("refs/heads/")
        || matches!(
            lower.as_str(),
            "--delete"
                | "-d"
                | "-f"
                | "--force"
                | "--force-with-lease"
                | "push"
                | "--points-at"
                | "--tags"
                | "--all"
                | "--mirror"
                | "head"
        )
}

/// Refspecs that would force-update, prune, or move HEAD during fetch.
pub(crate) fn fetch_refspec_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('+')
        || t.starts_with('-')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains(' ')
        || lower.contains("+refs/")
        || matches!(
            lower.as_str(),
            "--force"
                | "-f"
                | "--force-with-lease"
                | "--update-head-ok"
                | "--prune"
                | "-p"
                | "--prune-tags"
                | "--all"
                | "--mirror"
                | "--recurse-submodules"
        )
}

pub(crate) fn remote_url_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    t.starts_with('-')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains('\r')
        || t.contains('\t')
        || t.contains(' ')
        || t.chars().any(|c| {
            matches!(
                c,
                ';' | '|' | '&' | '$' | '`' | '<' | '>' | '(' | ')' | '\'' | '"' | '\\' | '*' | '?'
            )
        })
}

/// Same single-path rules as FILE-STAGE / FILE-UNSTAGE / CONFLICT-SAVE.
pub(crate) fn worktree_path_out_of_scope(value: &str) -> bool {
    conflict_path_out_of_scope(value)
}

/// Paths that would become flags or widen `git add` beyond one conflicted file.
pub(crate) fn conflict_path_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.is_empty()
        || t == "."
        || t == ".."
        || t == "*"
        || t.starts_with('-')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains('\\')
        || t.split('/').any(|part| part == ".." || part == ".")
        || matches!(
            lower.as_str(),
            "-a" | "-u" | "--all" | "--force" | "-f" | "--"
        )
}

pub(crate) fn conflict_markers_present(text: &str) -> bool {
    text.lines().any(|line| {
        line.starts_with("<<<<<<<") || line.starts_with(">>>>>>>") || line.starts_with("=======")
    })
}

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

    fn stash_apply(
        &self,
        _repo: &str,
        _stash_ref: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn stash_pop(
        &self,
        _repo: &str,
        _stash_ref: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn stash_drop(
        &self,
        _repo: &str,
        _stash_ref: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn stash_push(
        &self,
        _repo: &str,
        _message: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn create_tag(
        &self,
        _repo: &str,
        _name: &str,
        _message: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn delete_tag(
        &self,
        _repo: &str,
        _name: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn push_tag(
        &self,
        _repo: &str,
        _remote: &str,
        _name: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn create_branch(
        &self,
        _repo: &str,
        _name: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn delete_branch(
        &self,
        _repo: &str,
        _name: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn rename_branch(
        &self,
        _repo: &str,
        _old: &str,
        _new: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn add_remote(
        &self,
        _repo: &str,
        _name: &str,
        _url: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn remove_remote(
        &self,
        _repo: &str,
        _name: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn set_remote_url(
        &self,
        _repo: &str,
        _name: &str,
        _url: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn rename_remote(
        &self,
        _repo: &str,
        _old: &str,
        _new: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn set_upstream(
        &self,
        _repo: &str,
        _remote: &str,
        _branch: &str,
        _local: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn unset_upstream(
        &self,
        _repo: &str,
        _local: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn stage_all(&self, _repo: &str, _approval: GitWriteApproval) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn unstage_all(&self, _repo: &str, _approval: GitWriteApproval) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn unstage_path(
        &self,
        _repo: &str,
        _path: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn conflict_save(
        &self,
        _repo: &str,
        _path: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn conflict_continue(&self, _repo: &str, _approval: GitWriteApproval) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn conflict_abort(&self, _repo: &str, _approval: GitWriteApproval) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn conflict_skip(&self, _repo: &str, _approval: GitWriteApproval) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn fetch(
        &self,
        _repo: &str,
        _remote: &str,
        _refspec: Option<&str>,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn fetch_prune(
        &self,
        _repo: &str,
        _remote: &str,
        _approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(GIT_WRITE_GATED_MSG.into()))
    }

    fn pull_ff_only(
        &self,
        _repo: &str,
        _remote: &str,
        _branch: Option<&str>,
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
