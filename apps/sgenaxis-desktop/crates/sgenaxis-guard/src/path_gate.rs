//! Path allow vs protect matching (logical paths only; no FS I/O).

/// Normalize separators; drop empty and `.` segments (logical repo-relative paths).
pub fn normalize_path(path: &str) -> String {
    let s = path.replace('\\', "/");
    let mut parts: Vec<&str> = Vec::new();
    for seg in s.split('/') {
        if seg.is_empty() || seg == "." {
            continue;
        }
        parts.push(seg);
    }
    parts.join("/")
}

/// True if any path segment is `..` (traversal escape).
pub fn has_traversal(path: &str) -> bool {
    normalize_path(path)
        .split('/')
        .any(|seg| seg == "..")
}

/// Glob match: `*` = one segment fragment, `**` = zero or more path segments.
/// Patterns and paths are compared after [`normalize_path`].
pub fn path_matches(pattern: &str, path: &str) -> bool {
    let pat = normalize_path(pattern);
    let cand = normalize_path(path);
    match_glob(&pat, &cand)
}

fn match_glob(pattern: &str, path: &str) -> bool {
    let p_segs: Vec<&str> = if pattern.is_empty() {
        Vec::new()
    } else {
        pattern.split('/').collect()
    };
    let c_segs: Vec<&str> = if path.is_empty() {
        Vec::new()
    } else {
        path.split('/').collect()
    };
    match_segs(&p_segs, &c_segs)
}

fn match_segs(pat: &[&str], cand: &[&str]) -> bool {
    let mut i = 0;
    let mut j = 0;
    while i < pat.len() {
        if pat[i] == "**" {
            // Greedy: try consuming zero..remaining candidate segments.
            if i + 1 == pat.len() {
                return true;
            }
            for k in j..=cand.len() {
                if match_segs(&pat[i + 1..], &cand[k..]) {
                    return true;
                }
            }
            return false;
        }
        if j >= cand.len() {
            return false;
        }
        if !seg_match(pat[i], cand[j]) {
            return false;
        }
        i += 1;
        j += 1;
    }
    j == cand.len()
}

fn seg_match(pat: &str, seg: &str) -> bool {
    if pat == "*" {
        return true;
    }
    if !pat.contains('*') {
        return pat == seg;
    }
    // Simple single-segment wildcard: prefix*suffix
    let parts: Vec<&str> = pat.split('*').collect();
    if parts.len() == 2 {
        let (pre, suf) = (parts[0], parts[1]);
        return seg.starts_with(pre) && seg.ends_with(suf) && seg.len() >= pre.len() + suf.len();
    }
    // Multi-* in one segment: sequential contains
    let mut rest = seg;
    for (idx, part) in parts.iter().enumerate() {
        if part.is_empty() {
            continue;
        }
        if idx == 0 {
            if !rest.starts_with(part) {
                return false;
            }
            rest = &rest[part.len()..];
        } else if idx == parts.len() - 1 {
            if !rest.ends_with(part) {
                return false;
            }
        } else if let Some(pos) = rest.find(part) {
            rest = &rest[pos + part.len()..];
        } else {
            return false;
        }
    }
    true
}

/// True if `path` matches any pattern in `patterns`.
pub fn matches_any(patterns: &[String], path: &str) -> bool {
    patterns.iter().any(|p| path_matches(p, path))
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn normalize_backslashes() {
        assert_eq!(normalize_path(r"packages\guard\a.rs"), "packages/guard/a.rs");
    }

    #[test]
    fn glob_double_star() {
        assert!(path_matches("packages/guard/**", "packages/guard/src/lib.rs"));
        assert!(!path_matches("packages/guard/**", "packages/other/x.rs"));
    }

    #[test]
    fn traversal_detected() {
        assert!(has_traversal("../other-project/secret"));
        assert!(!has_traversal("packages/guard/src/lib.rs"));
    }
}
