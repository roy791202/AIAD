//! Raw test-run capture saved with every evidence record.

/// One observed case line inside a runner result (optional).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CaseResult {
    pub test_id: String,
    pub passed: bool,
    pub message: String,
}

/// Immutable command capture for an evidence write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunCapture {
    pub command: String,
    pub cwd: String,
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
    pub case_results: Vec<CaseResult>,
    /// True when the test binary/fixture compiled and started (runner reported build OK).
    pub build_ok: bool,
}

impl RunCapture {
    pub fn new(
        command: impl Into<String>,
        cwd: impl Into<String>,
        exit_code: i32,
    ) -> Self {
        Self {
            command: command.into(),
            cwd: cwd.into(),
            exit_code,
            stdout: String::new(),
            stderr: String::new(),
            case_results: Vec::new(),
            build_ok: true,
        }
    }

    pub fn with_stdout(mut self, s: impl Into<String>) -> Self {
        self.stdout = s.into();
        self
    }

    pub fn with_stderr(mut self, s: impl Into<String>) -> Self {
        self.stderr = s.into();
        self
    }

    pub fn with_build_ok(mut self, ok: bool) -> Self {
        self.build_ok = ok;
        self
    }

    pub fn with_cases(mut self, cases: Vec<CaseResult>) -> Self {
        self.case_results = cases;
        self
    }

    pub fn combined_output(&self) -> String {
        let mut out = String::new();
        out.push_str(&self.stdout);
        if !self.stderr.is_empty() {
            if !out.is_empty() {
                out.push('\n');
            }
            out.push_str(&self.stderr);
        }
        out
    }

    pub fn is_output_empty(&self) -> bool {
        self.stdout.trim().is_empty()
            && self.stderr.trim().is_empty()
            && self.case_results.is_empty()
    }
}
