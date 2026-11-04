//! Read-only, syntax-level preview of explicitly selected Rust source files.
//!
//! This module never mutates architecture state or source files. Reads go through
//! the existing FileSystemPort; the size limits are checked after `read` returns,
//! because that port does not expose a bounded-read capability. Path containment
//! here is lexical; the current Port has no canonicalize/no-follow seam, so this
//! implementation does not claim symlink/junction containment.

use serde::{Deserialize, Serialize};
use sgenaxis_ports::FileSystemPort;
use std::path::{Component, Path, PathBuf};
use syn::visit::Visit;

pub const PARSER_VERSION: &str = "syn 2.0.119";
pub const MAX_FILES: usize = 128;
pub const MAX_TOTAL_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_FILE_BYTES: usize = 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportPreviewRequest {
    pub relative_paths: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportPreview {
    pub parser_version: String,
    pub files: Vec<ImportFilePreview>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportFilePreview {
    pub relative_path: String,
    pub source_sha256: String,
    pub symbols: Vec<SyntaxSymbol>,
    pub unresolved_references: Vec<UnresolvedSyntaxReference>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SyntaxSymbol {
    pub kind: String,
    pub name: String,
    pub span: SourceSpan,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnresolvedSyntaxReference {
    pub expression: String,
    pub reason: String,
    pub span: Option<SourceSpan>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceSpan {
    pub start_line: usize,
    pub start_column: usize,
    pub end_line: usize,
    pub end_column: usize,
}

impl SourceSpan {
    /// proc_macro2 columns are zero-based UTF-8 character counts within each line.
    /// The parser receives BOM-stripped text, so restore the one BOM character
    /// for locations on the first line only.
    fn from_span(span: proc_macro2::Span, first_line_bom_characters: usize) -> Self {
        let start = span.start();
        let end = span.end();
        Self {
            start_line: start.line,
            start_column: start.column
                + if start.line == 1 { first_line_bom_characters } else { 0 },
            end_line: end.line,
            end_column: end.column + if end.line == 1 { first_line_bom_characters } else { 0 },
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportPreviewError {
    pub code: String,
    pub relative_path: Option<String>,
    pub message: String,
}

impl ImportPreviewError {
    fn new(code: &str, relative_path: Option<&str>, message: impl Into<String>) -> Self {
        Self {
            code: code.to_owned(),
            relative_path: relative_path.map(str::to_owned),
            message: message.into(),
        }
    }
}

/// Private application seam. Implementations must use the bound root and never
/// return a partial preview if any selected file fails.
pub fn preview_selected(
    fs: &dyn FileSystemPort,
    bound_project_root: &str,
    request: &ImportPreviewRequest,
) -> Result<ImportPreview, ImportPreviewError> {
    if bound_project_root.trim().is_empty() || bound_project_root.contains('\0') {
        return Err(ImportPreviewError::new(
            "UNBOUND_PROJECT",
            None,
            "a non-empty bound project root is required",
        ));
    }
    if request.relative_paths.len() > MAX_FILES {
        return Err(ImportPreviewError::new(
            "INPUT_LIMIT",
            None,
            format!("at most {MAX_FILES} source files are allowed"),
        ));
    }

    let mut total_bytes = 0usize;
    let mut previews = Vec::with_capacity(request.relative_paths.len());
    for relative_path in &request.relative_paths {
        validate_relative_rust_path(relative_path)?;
        let full_path = PathBuf::from(bound_project_root).join(relative_path);
        let bytes = fs.read(&full_path.to_string_lossy()).map_err(|error| {
            ImportPreviewError::new("READ_FAILED", Some(relative_path), error.to_string())
        })?;
        if bytes.len() > MAX_FILE_BYTES {
            return Err(ImportPreviewError::new(
                "INPUT_LIMIT",
                Some(relative_path),
                format!("source file exceeds {MAX_FILE_BYTES} bytes"),
            ));
        }
        total_bytes = total_bytes.saturating_add(bytes.len());
        if total_bytes > MAX_TOTAL_BYTES {
            return Err(ImportPreviewError::new(
                "INPUT_LIMIT",
                Some(relative_path),
                format!("selected sources exceed {MAX_TOTAL_BYTES} bytes"),
            ));
        }

        let source_sha256 = sgenaxis_spec::packet::source_sha256(&bytes);
        let parse_bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(&bytes);
        let first_line_bom_characters = usize::from(bytes.len() != parse_bytes.len());
        let source = std::str::from_utf8(parse_bytes).map_err(|_| {
            ImportPreviewError::new(
                "INVALID_UTF8",
                Some(relative_path),
                "source is not valid UTF-8",
            )
        })?;
        let syntax = syn::parse_file(source).map_err(|error| {
            ImportPreviewError::new("PARSE_FAILED", Some(relative_path), error.to_string())
        })?;
        let mut facts = SyntaxFacts {
            first_line_bom_characters,
            ..SyntaxFacts::default()
        };
        facts.visit_file(&syntax);
        previews.push(ImportFilePreview {
            relative_path: relative_path.clone(),
            source_sha256,
            symbols: facts.symbols,
            unresolved_references: facts.references,
        });
    }

    Ok(ImportPreview {
        parser_version: PARSER_VERSION.to_owned(),
        files: previews,
    })
}

fn validate_relative_rust_path(path: &str) -> Result<(), ImportPreviewError> {
    let normalized = path.replace('\\', "/");
    let parts: Vec<&str> = normalized.split('/').collect();
    let invalid = normalized.trim().is_empty()
        || normalized.contains('\0')
        || normalized.starts_with('/')
        || normalized.contains(':')
        || parts
            .iter()
            .any(|part| part.is_empty() || *part == "." || *part == "..")
        || Path::new(path).components().any(|component| {
            matches!(
                component,
                Component::Prefix(_) | Component::RootDir | Component::ParentDir
            )
        });
    if invalid {
        return Err(ImportPreviewError::new(
            "UNBOUND_PROJECT",
            Some(path),
            "source path must stay project-relative",
        ));
    }
    if !normalized.ends_with(".rs") {
        return Err(ImportPreviewError::new(
            "UNSUPPORTED_LANGUAGE",
            Some(path),
            "only Rust .rs files are supported",
        ));
    }
    Ok(())
}

#[derive(Default)]
struct SyntaxFacts {
    symbols: Vec<SyntaxSymbol>,
    references: Vec<UnresolvedSyntaxReference>,
    first_line_bom_characters: usize,
}

impl<'ast> syn::visit::Visit<'ast> for SyntaxFacts {
    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        self.symbols.push(SyntaxSymbol {
            kind: "function".into(),
            name: node.sig.ident.to_string(),
            span: SourceSpan::from_span(node.sig.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_fn(self, node);
    }

    fn visit_item_struct(&mut self, node: &'ast syn::ItemStruct) {
        self.symbols.push(SyntaxSymbol {
            kind: "struct".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_struct(self, node);
    }

    fn visit_item_enum(&mut self, node: &'ast syn::ItemEnum) {
        self.symbols.push(SyntaxSymbol {
            kind: "enum".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_enum(self, node);
    }

    fn visit_item_trait(&mut self, node: &'ast syn::ItemTrait) {
        self.symbols.push(SyntaxSymbol {
            kind: "trait".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_trait(self, node);
    }

    fn visit_item_type(&mut self, node: &'ast syn::ItemType) {
        self.symbols.push(SyntaxSymbol {
            kind: "type".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_type(self, node);
    }

    fn visit_item_mod(&mut self, node: &'ast syn::ItemMod) {
        self.symbols.push(SyntaxSymbol {
            kind: "module".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_mod(self, node);
    }

    fn visit_item_const(&mut self, node: &'ast syn::ItemConst) {
        self.symbols.push(SyntaxSymbol {
            kind: "const".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_const(self, node);
    }

    fn visit_item_static(&mut self, node: &'ast syn::ItemStatic) {
        self.symbols.push(SyntaxSymbol {
            kind: "static".into(),
            name: node.ident.to_string(),
            span: SourceSpan::from_span(node.ident.span(), self.first_line_bom_characters),
        });
        syn::visit::visit_item_static(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        let expression = match node.func.as_ref() {
            syn::Expr::Path(path) => path
                .path
                .segments
                .iter()
                .map(|s| s.ident.to_string())
                .collect::<Vec<_>>()
                .join("::"),
            _ => "call expression".to_owned(),
        };
        self.references.push(UnresolvedSyntaxReference {
            expression,
            reason: "syntax-only; target resolution is not performed".into(),
            span: match node.func.as_ref() {
                syn::Expr::Path(path) => path
                    .path
                    .segments
                    .last()
                    .map(|segment| {
                        SourceSpan::from_span(segment.ident.span(), self.first_line_bom_characters)
                    }),
                _ => None,
            },
        });
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        self.references.push(UnresolvedSyntaxReference {
            expression: node.method.to_string(),
            reason: "syntax-only; method dispatch is not resolved".into(),
            span: Some(SourceSpan::from_span(
                node.method.span(),
                self.first_line_bom_characters,
            )),
        });
        syn::visit::visit_expr_method_call(self, node);
    }

    fn visit_macro(&mut self, node: &'ast syn::Macro) {
        self.references.push(UnresolvedSyntaxReference {
            expression: node
                .path
                .segments
                .iter()
                .map(|segment| segment.ident.to_string())
                .collect::<Vec<_>>()
                .join("::"),
            reason: "syntax-only; macro expansion is not performed".into(),
            span: node
                .path
                .segments
                .last()
                .map(|segment| {
                    SourceSpan::from_span(segment.ident.span(), self.first_line_bom_characters)
                }),
        });
        syn::visit::visit_macro(self, node);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_ports::PortError;
    use std::collections::BTreeMap;
    use std::sync::Mutex;

    #[derive(Default)]
    struct FakeFs {
        files: Mutex<BTreeMap<String, Vec<u8>>>,
        reads: Mutex<Vec<String>>,
        writes: Mutex<Vec<String>>,
    }

    impl FakeFs {
        fn key(path: &str) -> String {
            path.replace('\\', "/")
        }
        fn with_files(files: &[(&str, &[u8])]) -> Self {
            Self {
                files: Mutex::new(
                    files
                        .iter()
                        .map(|(p, b)| ((*p).to_owned(), b.to_vec()))
                        .collect(),
                ),
                ..Self::default()
            }
        }
    }

    impl FileSystemPort for FakeFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> {
            Ok(self.files.lock().unwrap().contains_key(&Self::key(path)))
        }
        fn read_to_string(&self, path: &str) -> Result<String, PortError> {
            String::from_utf8(self.read(path)?).map_err(|e| PortError::Io(e.to_string()))
        }
        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
            let key = Self::key(path);
            self.reads.lock().unwrap().push(key.clone());
            self.files
                .lock()
                .unwrap()
                .get(&key)
                .cloned()
                .ok_or_else(|| PortError::NotFound(path.into()))
        }
        fn write_atomic(&self, path: &str, _contents: &[u8]) -> Result<(), PortError> {
            self.writes.lock().unwrap().push(path.to_owned());
            Ok(())
        }
        fn create_dir_all(&self, _path: &str) -> Result<(), PortError> {
            Ok(())
        }
        fn is_file(&self, path: &str) -> Result<bool, PortError> {
            self.exists(path)
        }
        fn remove_file(&self, _path: &str) -> Result<(), PortError> {
            Ok(())
        }
    }

    fn req(paths: &[&str]) -> ImportPreviewRequest {
        ImportPreviewRequest {
            relative_paths: paths.iter().map(|p| (*p).to_owned()).collect(),
        }
    }

    #[test]
    fn nat01_valid_rust_returns_syntax_facts_and_unresolved_calls() {
        let fs = FakeFs::with_files(&[(
            "/project/src/lib.rs",
            b"mod api { pub struct Item; }\nuse crate::api::Item;\npub trait Runner { fn run(&self); }\npub fn run<T: Runner>(x: &T, item: Item) { x.run(); invoke(item); marker!(); }\n",
        )]);
        let preview = preview_selected(&fs, "/project", &req(&["src/lib.rs"])).unwrap();
        assert_eq!(preview.parser_version, PARSER_VERSION);
        let file = &preview.files[0];
        assert_eq!(file.relative_path, "src/lib.rs");
        assert!(file
            .symbols
            .iter()
            .any(|s| s.kind == "struct" && s.name == "Item"));
        assert!(file
            .symbols
            .iter()
            .any(|s| s.kind == "function" && s.name == "run"));
        assert!(file.symbols.iter().any(|s| {
            s.kind == "function"
                && s.name == "run"
                && s.span.start_line == 4
                && s.span.end_line == 4
                && s.span.end_column > s.span.start_column
        }));
        assert!(file
            .symbols
            .iter()
            .any(|s| s.kind == "trait" && s.name == "Runner"));
        assert!(file
            .unresolved_references
            .iter()
            .any(|r| r.expression.contains("invoke")));
        assert!(file
            .unresolved_references
            .iter()
            .any(|r| { r.expression == "run" && r.reason.contains("dispatch is not resolved") }));
        assert!(file.unresolved_references.iter().any(|r| {
            r.expression == "marker" && r.reason.contains("macro expansion is not performed")
        }));
        assert!(
            !file.unresolved_references.is_empty(),
            "syntax calls must not be claimed as resolved graph edges"
        );
        assert!(fs.writes.lock().unwrap().is_empty());
    }

    #[test]
    fn nat11_locations_are_one_based_lines_and_zero_based_unicode_columns_in_original_source() {
        let multiline = b"// preface\nfn /*\xE7\x8C\xAB*/ run() { invoke(); }\n";
        let bom = b"\xEF\xBB\xBFfn /*\xE7\x8C\xAB*/ run() { invoke(); }\n";
        let fs = FakeFs::with_files(&[
            ("/project/multiline.rs", multiline),
            ("/project/bom.rs", bom),
        ]);
        let preview = preview_selected(
            &fs,
            "/project",
            &req(&["multiline.rs", "bom.rs"]),
        )
        .unwrap();

        let multiline_file = &preview.files[0];
        let function = multiline_file
            .symbols
            .iter()
            .find(|symbol| symbol.kind == "function" && symbol.name == "run")
            .unwrap();
        assert_eq!((function.span.start_line, function.span.start_column), (2, 9));
        let call = multiline_file
            .unresolved_references
            .iter()
            .find(|reference| reference.expression == "invoke")
            .unwrap();
        assert_eq!(
            (call.span.as_ref().unwrap().start_line, call.span.as_ref().unwrap().start_column),
            (2, 17)
        );

        let bom_file = &preview.files[1];
        let function = bom_file
            .symbols
            .iter()
            .find(|symbol| symbol.kind == "function" && symbol.name == "run")
            .unwrap();
        assert_eq!((function.span.start_line, function.span.start_column), (1, 10));
        let call = bom_file
            .unresolved_references
            .iter()
            .find(|reference| reference.expression == "invoke")
            .unwrap();
        assert_eq!(
            (call.span.as_ref().unwrap().start_line, call.span.as_ref().unwrap().start_column),
            (1, 18)
        );
        assert_eq!(bom_file.source_sha256, sgenaxis_spec::packet::source_sha256(bom));
    }

    #[test]
    fn nat02_malformed_source_returns_existing_parse_failed_diagnostic_without_partial_result() {
        let fs = FakeFs::with_files(&[
            ("/project/a.rs", b"pub fn first() {}"),
            ("/project/b.rs", b"pub fn broken( {"),
        ]);
        let error = preview_selected(&fs, "/project", &req(&["a.rs", "b.rs"])).unwrap_err();
        assert_eq!(error.code, "PARSE_FAILED");
        assert_eq!(error.relative_path.as_deref(), Some("b.rs"));
        assert!(fs.writes.lock().unwrap().is_empty());
    }

    #[test]
    fn nat03_bom_is_removed_only_for_parsing_and_digest_covers_original_bytes() {
        let plain = b"pub fn run() {}";
        let bom = b"\xEF\xBB\xBFpub fn run() {}";
        let fs = FakeFs::with_files(&[("/project/plain.rs", plain), ("/project/bom.rs", bom)]);
        let preview = preview_selected(&fs, "/project", &req(&["plain.rs", "bom.rs"])).unwrap();
        let a = &preview.files[0];
        let b = &preview.files[1];
        assert_eq!(
            a.symbols
                .iter()
                .map(|symbol| (&symbol.kind, &symbol.name))
                .collect::<Vec<_>>(),
            b.symbols
                .iter()
                .map(|symbol| (&symbol.kind, &symbol.name))
                .collect::<Vec<_>>()
        );
        assert_eq!(a.symbols[0].span.start_column, 7);
        assert_eq!(b.symbols[0].span.start_column, 8);
        assert_eq!(a.source_sha256, sgenaxis_spec::packet::source_sha256(plain));
        assert_eq!(b.source_sha256, sgenaxis_spec::packet::source_sha256(bom));
        assert_ne!(a.source_sha256, b.source_sha256);
    }

    #[test]
    fn nat04_invalid_utf8_is_rejected_before_parser_and_never_writes() {
        let fs = FakeFs::with_files(&[("/project/bad.rs", b"fn x(){\xFF}")]);
        let error = preview_selected(&fs, "/project", &req(&["bad.rs"])).unwrap_err();
        assert_eq!(error.code, "INVALID_UTF8");
        assert!(fs.writes.lock().unwrap().is_empty());
    }

    #[test]
    fn nat05_unsupported_or_escaping_paths_are_rejected_without_reading() {
        let fs =
            FakeFs::with_files(&[("/project/src/a.py", b"x"), ("/outside/a.rs", b"fn x() {}")]);
        for (path, code) in [
            ("src/a.py", "UNSUPPORTED_LANGUAGE"),
            ("../outside/a.rs", "UNBOUND_PROJECT"),
            ("/outside/a.rs", "UNBOUND_PROJECT"),
            ("C:/outside/a.rs", "UNBOUND_PROJECT"),
            ("src/bad\0name.rs", "UNBOUND_PROJECT"),
        ] {
            let error = preview_selected(&fs, "/project", &req(&[path])).unwrap_err();
            assert_eq!(error.code, code, "{path}");
        }
        assert!(fs.reads.lock().unwrap().is_empty());
    }

    #[test]
    fn nat10_empty_bound_root_is_rejected_before_read_even_for_empty_selection() {
        let fs = FakeFs::with_files(&[("src/a.rs", b"fn a() {}")]);
        for root in ["", "   "] {
            let error = preview_selected(&fs, root, &req(&[])).unwrap_err();
            assert_eq!(error.code, "UNBOUND_PROJECT");
        }
        assert!(fs.reads.lock().unwrap().is_empty());
    }

    #[test]
    fn nat06_file_and_aggregate_limits_reject_without_truncation() {
        let at_file = vec![b' '; MAX_FILE_BYTES];
        let over_file = vec![b' '; MAX_FILE_BYTES + 1];
        let fs = FakeFs::with_files(&[
            ("/project/at.rs", &at_file),
            ("/project/over.rs", &over_file),
        ]);
        assert!(preview_selected(&fs, "/project", &req(&["at.rs"])).is_ok());
        let err = preview_selected(&fs, "/project", &req(&["over.rs"])).unwrap_err();
        assert_eq!(err.code, "INPUT_LIMIT");

        let one_mib = vec![b' '; MAX_FILE_BYTES];
        let mut exact_files = Vec::new();
        let mut exact_paths = Vec::new();
        for i in 0..8 {
            let path = format!("/project/exact-{i}.rs");
            exact_files.push((path, one_mib.clone()));
            exact_paths.push(format!("exact-{i}.rs"));
        }
        let exact_refs: Vec<(&str, &[u8])> = exact_files
            .iter()
            .map(|(p, b)| (p.as_str(), b.as_slice()))
            .collect();
        let fs = FakeFs::with_files(&exact_refs);
        let exact_req = ImportPreviewRequest {
            relative_paths: exact_paths,
        };
        let exact = preview_selected(&fs, "/project", &exact_req).unwrap();
        assert_eq!(exact.files.len(), 8);

        let mut over_files = exact_files;
        over_files.push(("/project/ninth.rs".to_owned(), vec![b' ']));
        let over_refs: Vec<(&str, &[u8])> = over_files
            .iter()
            .map(|(p, b)| (p.as_str(), b.as_slice()))
            .collect();
        let fs = FakeFs::with_files(&over_refs);
        let mut over_paths: Vec<String> = (0..8).map(|i| format!("exact-{i}.rs")).collect();
        over_paths.push("ninth.rs".to_owned());
        let err = preview_selected(
            &fs,
            "/project",
            &ImportPreviewRequest {
                relative_paths: over_paths,
            },
        )
        .unwrap_err();
        assert_eq!(err.code, "INPUT_LIMIT");
    }

    #[test]
    fn nat07_exact_file_count_limit_is_accepted_and_over_limit_rejected_before_read() {
        let files: Vec<(String, Vec<u8>)> = (0..MAX_FILES)
            .map(|i| (format!("/project/{i}.rs"), b"fn x() {}".to_vec()))
            .collect();
        let exact_refs: Vec<(&str, &[u8])> = files
            .iter()
            .map(|(p, b)| (p.as_str(), b.as_slice()))
            .collect();
        let fs = FakeFs::with_files(&exact_refs);
        let exact_paths: Vec<String> = (0..MAX_FILES).map(|i| format!("{i}.rs")).collect();
        let exact = preview_selected(
            &fs,
            "/project",
            &ImportPreviewRequest {
                relative_paths: exact_paths,
            },
        )
        .unwrap();
        assert_eq!(exact.files.len(), MAX_FILES);

        let fs = FakeFs::default();
        let paths: Vec<String> = (0..=MAX_FILES).map(|i| format!("{i}.rs")).collect();
        let request = ImportPreviewRequest {
            relative_paths: paths,
        };
        let error = preview_selected(&fs, "/project", &request).unwrap_err();
        assert_eq!(error.code, "INPUT_LIMIT");
        assert!(fs.reads.lock().unwrap().is_empty());
    }

    #[test]
    fn nat08_empty_selection_returns_empty_read_only_preview_and_duplicates_preserve_request_order()
    {
        let fs = FakeFs::with_files(&[("/project/a.rs", b"pub fn a() {}")]);
        let empty = preview_selected(&fs, "/project", &req(&[])).unwrap();
        assert!(empty.files.is_empty());
        let repeated = preview_selected(&fs, "/project", &req(&["a.rs", "a.rs"])).unwrap();
        assert_eq!(repeated.files.len(), 2);
        assert!(repeated
            .files
            .iter()
            .all(|file| file.relative_path == "a.rs"));
        assert_eq!(
            *fs.reads.lock().unwrap(),
            vec!["/project/a.rs", "/project/a.rs"]
        );
        assert!(fs.writes.lock().unwrap().is_empty());
    }

    #[test]
    fn nat09_any_read_failure_rejects_whole_preview_without_authoritative_writes() {
        let fs = FakeFs::with_files(&[("/project/ok.rs", b"pub fn ok() {}")]);
        let error = preview_selected(&fs, "/project", &req(&["ok.rs", "missing.rs"])).unwrap_err();
        assert_eq!(error.code, "READ_FAILED");
        assert_eq!(error.relative_path.as_deref(), Some("missing.rs"));
        assert!(fs.writes.lock().unwrap().is_empty());
    }
}
