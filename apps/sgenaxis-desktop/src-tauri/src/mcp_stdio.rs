//! Test-only synchronous MCP stdio fixture client.
//!
//! Compiled only for unit tests and never composed into DispatchHost. The
//! helper executable is built from the fixed source under `tests/fixtures`.
//! It enforces the owner-approved v20 fixture limits and accepts only that
//! owned fixture; it is not a general-purpose or production transport.

use std::io::{BufRead, BufReader, Read, Write};
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use crate::exec::{ExecError, McpAgentSettings, McpClientPort, McpSessionId, McpTransportKind};

const INITIALIZE_TIMEOUT: Duration = Duration::from_millis(10_000);
const TOOL_TIMEOUT: Duration = Duration::from_millis(10_000);
const CLOSE_TIMEOUT: Duration = Duration::from_millis(2_000);
const OWNED_FIXTURE_ENDPOINT: &str = "stdio://test-owned-fixture";
const MAX_FRAME_BYTES: usize = 1024 * 1024;
const MAX_RETAINED_STDERR_BYTES: usize = 64 * 1024;
const MAX_NON_RESPONSE_MESSAGES_PER_REQUEST: usize = 1000;

#[derive(Debug, Clone)]
struct StdioTarget {
    program: std::path::PathBuf,
    argv: Vec<String>,
    cwd: std::path::PathBuf,
    server_name: String,
    tool: String,
    protocol_version: String,
    initialize_timeout: Duration,
    tool_timeout: Duration,
    close_timeout: Duration,
}

enum WriterMessage {
    Frame(Vec<u8>, Sender<Result<(), String>>),
}

enum ReaderMessage {
    Line(String),
    Eof,
    Error,
}

struct Session {
    id: McpSessionId,
    approved_tool: String,
    child: Child,
    writer: Option<Sender<WriterMessage>>,
    responses: Option<Receiver<ReaderMessage>>,
    writer_thread: Option<JoinHandle<()>>,
    stdout_thread: Option<JoinHandle<()>>,
    stderr_thread: Option<JoinHandle<()>>,
    // Bounded stderr capture is asserted by the fixture tests; it is intentionally
    // not projected into product/UI state.
    stderr_retained: Arc<Mutex<Vec<u8>>>,
}

struct StdioMcpClient {
    target: StdioTarget,
    next_session: u64,
    session: Option<Session>,
}

impl StdioMcpClient {
    fn new(target: StdioTarget) -> Self {
        Self {
            target,
            next_session: 1,
            session: None,
        }
    }

    fn start_session(&mut self) -> Result<Session, ExecError> {
        if self.session.is_some() {
            return Err(ExecError::Busy(
                "one fixture session is already open".into(),
            ));
        }
        let mut child = Command::new(&self.target.program)
            .args(&self.target.argv)
            .current_dir(&self.target.cwd)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|_| ExecError::Mcp("owned fixture spawn failed".into()))?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| ExecError::Mcp("fixture stdin unavailable".into()))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| ExecError::Mcp("fixture stdout unavailable".into()))?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| ExecError::Mcp("fixture stderr unavailable".into()))?;

        let (writer_tx, writer_rx) = mpsc::channel::<WriterMessage>();
        let writer_thread = thread::spawn(move || writer_loop(stdin, writer_rx));
        // Backpressure keeps queued frames bounded while exchange applies the
        // per-request non-response limit.
        let (response_tx, responses) = mpsc::sync_channel::<ReaderMessage>(2);
        let stdout_thread = thread::spawn(move || stdout_loop(stdout, response_tx));
        let stderr_retained = Arc::new(Mutex::new(Vec::new()));
        let stderr_capture = Arc::clone(&stderr_retained);
        let stderr_thread = thread::spawn(move || stderr_loop(stderr, stderr_capture));

        Ok(Session {
            id: McpSessionId(self.next_session),
            approved_tool: self.target.tool.clone(),
            child,
            writer: Some(writer_tx),
            responses: Some(responses),
            writer_thread: Some(writer_thread),
            stdout_thread: Some(stdout_thread),
            stderr_thread: Some(stderr_thread),
            stderr_retained,
        })
    }

    fn exchange(
        session: &Session,
        request: serde_json::Value,
        expected_id: u64,
        deadline: Instant,
    ) -> Result<serde_json::Value, ExecError> {
        let mut frame = serde_json::to_vec(&request)
            .map_err(|_| ExecError::Mcp("fixture request serialization failed".into()))?;
        if frame.len() > MAX_FRAME_BYTES {
            return Err(ExecError::Mcp(
                "fixture request exceeds 1 MiB frame limit".into(),
            ));
        }
        frame.push(b'\n');
        let (write_tx, write_rx) = mpsc::channel();
        session
            .writer
            .as_ref()
            .ok_or_else(|| ExecError::Mcp("fixture writer closed".into()))?
            .send(WriterMessage::Frame(frame, write_tx))
            .map_err(|_| ExecError::Mcp("fixture writer stopped".into()))?;

        let write_remaining = deadline.saturating_duration_since(Instant::now());
        match write_rx.recv_timeout(write_remaining) {
            Ok(Ok(())) => {}
            Ok(Err(_)) => return Err(ExecError::Mcp("fixture request write failed".into())),
            Err(RecvTimeoutError::Timeout) => {
                return Err(ExecError::Mcp("fixture request write timed out".into()))
            }
            Err(RecvTimeoutError::Disconnected) => {
                return Err(ExecError::Mcp("fixture writer stopped".into()))
            }
        }

        let mut non_response_messages = 0usize;
        let response = loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            let responses = session
                .responses
                .as_ref()
                .ok_or_else(|| ExecError::Mcp("fixture response receiver closed".into()))?;
            let line = match responses.recv_timeout(remaining) {
                Ok(ReaderMessage::Line(line)) => line,
                Ok(ReaderMessage::Eof) => {
                    return Err(ExecError::Mcp("fixture closed stdout".into()))
                }
                Ok(ReaderMessage::Error) => {
                    return Err(ExecError::Mcp("fixture stdout read failed".into()))
                }
                Err(RecvTimeoutError::Timeout) => {
                    return Err(ExecError::Mcp("fixture response timed out".into()))
                }
                Err(RecvTimeoutError::Disconnected) => {
                    return Err(ExecError::Mcp("fixture response channel closed".into()))
                }
            };
            let message: serde_json::Value = serde_json::from_str(&line)
                .map_err(|_| ExecError::Mcp("fixture returned invalid JSON".into()))?;
            let object = message
                .as_object()
                .ok_or_else(|| ExecError::Mcp("fixture returned non-object JSON-RPC message".into()))?;
            if object.get("jsonrpc").and_then(|v| v.as_str()) != Some("2.0") {
                return Err(ExecError::Mcp(
                    "fixture returned unsupported JSON-RPC version".into(),
                ));
            }
            if !object.contains_key("id") {
                if object
                    .get("method")
                    .and_then(|v| v.as_str())
                    .is_none_or(|method| method.is_empty())
                {
                    return Err(ExecError::Mcp(
                        "fixture returned invalid JSON-RPC notification".into(),
                    ));
                }
                non_response_messages += 1;
                if non_response_messages > MAX_NON_RESPONSE_MESSAGES_PER_REQUEST {
                    return Err(ExecError::Mcp(
                        "fixture exceeded 1000 non-response messages for one request".into(),
                    ));
                }
                continue;
            }
            if object.get("id").and_then(|v| v.as_u64()) != Some(expected_id)
            {
                return Err(ExecError::Mcp("fixture response identity mismatch".into()));
            }
            break message;
        };
        if response.get("error").is_some() {
            return Err(ExecError::Mcp("fixture returned a JSON-RPC error".into()));
        }
        let result = response
            .get("result")
            .cloned()
            .ok_or_else(|| ExecError::Mcp("fixture response omitted result".into()))?;
        if result.get("isError").and_then(|v| v.as_bool()) == Some(true) {
            return Err(ExecError::Mcp("fixture tool reported an error".into()));
        }
        Ok(result)
    }

    fn send_notification(
        session: &Session,
        method: &str,
        deadline: Instant,
    ) -> Result<(), ExecError> {
        let mut frame = serde_json::to_vec(&serde_json::json!({
            "jsonrpc": "2.0",
            "method": method
        }))
        .map_err(|_| ExecError::Mcp("fixture notification serialization failed".into()))?;
        if frame.len() > MAX_FRAME_BYTES {
            return Err(ExecError::Mcp(
                "fixture notification exceeds 1 MiB frame limit".into(),
            ));
        }
        frame.push(b'\n');
        let (write_tx, write_rx) = mpsc::channel();
        session
            .writer
            .as_ref()
            .ok_or_else(|| ExecError::Mcp("fixture writer closed".into()))?
            .send(WriterMessage::Frame(frame, write_tx))
            .map_err(|_| ExecError::Mcp("fixture writer stopped".into()))?;
        match write_rx.recv_timeout(deadline.saturating_duration_since(Instant::now())) {
            Ok(Ok(())) => Ok(()),
            _ => Err(ExecError::Mcp("fixture notification write failed".into())),
        }
    }

    fn close_session(session: &mut Session, close_timeout: Duration) -> Result<(), ExecError> {
        drop(session.writer.take()); // closes child stdin once queued writes finish
                                     // Wake a stdout worker blocked by the bounded response queue. The
                                     // session is already closing and no further response can be consumed.
        drop(session.responses.take());
        let started = Instant::now();
        let deadline = started + close_timeout;
        let terminate_at = started + close_timeout.mul_f32(0.75);
        let mut killed = false;
        loop {
            match session.child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) if Instant::now() < terminate_at => {
                    thread::sleep(
                        Duration::from_millis(5)
                            .min(terminate_at.saturating_duration_since(Instant::now())),
                    );
                }
                Ok(None) => {
                    if !killed {
                        session.child.kill().map_err(|_| {
                            ExecError::Mcp("owned fixture termination failed".into())
                        })?;
                        killed = true;
                    }
                    if Instant::now() >= deadline {
                        return Err(ExecError::Mcp(
                            "owned fixture did not exit before close deadline; ownership retained"
                                .into(),
                        ));
                    }
                    thread::sleep(
                        Duration::from_millis(5)
                            .min(deadline.saturating_duration_since(Instant::now())),
                    );
                }
                Err(_) => return Err(ExecError::Mcp("owned fixture status unavailable".into())),
            }
        }
        let workers = [
            &mut session.writer_thread,
            &mut session.stdout_thread,
            &mut session.stderr_thread,
        ];
        while workers
            .iter()
            .any(|worker| worker.as_ref().is_some_and(|h| !h.is_finished()))
        {
            if Instant::now() >= deadline {
                return Err(ExecError::Mcp(
                    "fixture IO workers did not settle before close deadline; ownership retained"
                        .into(),
                ));
            }
            thread::sleep(
                Duration::from_millis(5).min(deadline.saturating_duration_since(Instant::now())),
            );
        }
        for worker in workers {
            if let Some(worker) = worker.take() {
                worker
                    .join()
                    .map_err(|_| ExecError::Mcp("fixture IO worker failed".into()))?;
            }
        }
        let _ = killed; // termination is successful cleanup once exit/workers are observed
        Ok(())
    }
}

impl McpClientPort for StdioMcpClient {
    fn connect(&mut self, settings: &McpAgentSettings) -> Result<McpSessionId, ExecError> {
        if settings.transport != McpTransportKind::Stdio
            || settings.server_name != self.target.server_name
            || settings.endpoint != OWNED_FIXTURE_ENDPOINT
            || !settings.is_tool_approved(&self.target.tool)
        {
            return Err(ExecError::EndpointNotApproved(
                "test-owned stdio fixture target mismatch".into(),
            ));
        }
        let mut session = self.start_session()?;
        let request = serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": self.target.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "eluslot-fixture", "version": "0.1.0"}
            }
        });
        let initialize_deadline = Instant::now() + self.target.initialize_timeout;
        let initialized = Self::exchange(&session, request, 1, initialize_deadline);
        let result = match initialized {
            Ok(result)
                if result.get("protocolVersion").and_then(|v| v.as_str())
                    == Some(self.target.protocol_version.as_str())
                    && result
                        .get("capabilities")
                        .and_then(|v| v.get("tools"))
                        .is_some()
                    && result
                        .get("serverInfo")
                        .and_then(|v| v.get("name"))
                        .and_then(|v| v.as_str())
                        == Some(self.target.server_name.as_str()) =>
            {
                Self::send_notification(&session, "notifications/initialized", initialize_deadline)
            }
            Ok(_) => Err(ExecError::Mcp(
                "fixture initialize contract mismatch".into(),
            )),
            Err(error) => Err(error),
        };
        if let Err(error) = result {
            if Self::close_session(&mut session, self.target.close_timeout).is_err() {
                self.session = Some(session);
            }
            return Err(error);
        }
        let id = session.id;
        self.next_session = self.next_session.saturating_add(1);
        self.session = Some(session);
        Ok(id)
    }

    fn call_tool(
        &mut self,
        session_id: McpSessionId,
        tool: &str,
        args_json: &str,
    ) -> Result<String, ExecError> {
        let session = self
            .session
            .as_ref()
            .filter(|session| session.id == session_id)
            .ok_or_else(|| ExecError::Mcp("unknown fixture session".into()))?;
        if tool != session.approved_tool {
            return Err(ExecError::ToolNotApproved(tool.to_owned()));
        }
        let arguments: serde_json::Value = serde_json::from_str(args_json)
            .map_err(|_| ExecError::Mcp("fixture tool arguments are not JSON".into()))?;
        let result = Self::exchange(
            session,
            serde_json::json!({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments}
            }),
            2,
            Instant::now() + self.target.tool_timeout,
        )
        .and_then(|result| {
            serde_json::to_string(&result)
                .map_err(|_| ExecError::Mcp("fixture result serialization failed".into()))
        });
        if result.is_err() {
            if let Some(session) = self.session.as_mut() {
                if Self::close_session(session, self.target.close_timeout).is_ok() {
                    self.session.take();
                }
            }
        }
        result
    }

    fn disconnect(&mut self, session_id: McpSessionId) -> Result<(), ExecError> {
        if !self
            .session
            .as_ref()
            .is_some_and(|session| session.id == session_id)
        {
            return Err(ExecError::Mcp("unknown fixture session".into()));
        }
        let result = Self::close_session(
            self.session.as_mut().expect("checked session"),
            self.target.close_timeout,
        );
        if result.is_ok() {
            self.session.take();
        }
        result
    }
}

impl Drop for StdioMcpClient {
    fn drop(&mut self) {
        if let Some(session) = self.session.as_mut() {
            if Self::close_session(session, CLOSE_TIMEOUT).is_err() {
                // No unbounded Drop wait: keep unresolved child/worker handles alive.
                if let Some(session) = self.session.take() {
                    std::mem::forget(session);
                }
            }
        }
    }
}

fn writer_loop(mut stdin: ChildStdin, receiver: Receiver<WriterMessage>) {
    while let Ok(WriterMessage::Frame(frame, reply)) = receiver.recv() {
        let result = stdin
            .write_all(&frame)
            .and_then(|_| stdin.flush())
            .map_err(|_| "write failed".to_owned());
        let _ = reply.send(result);
    }
}

fn stdout_loop(stdout: ChildStdout, sender: mpsc::SyncSender<ReaderMessage>) {
    let mut reader = BufReader::new(stdout);
    loop {
        let mut bytes = Vec::with_capacity(4096);
        let read_result = reader
            .by_ref()
            .take((MAX_FRAME_BYTES + 2) as u64)
            .read_until(b'\n', &mut bytes);
        match read_result {
            Ok(0) => {
                let _ = sender.send(ReaderMessage::Eof);
                return;
            }
            Ok(_) if bytes.len() > MAX_FRAME_BYTES + 1 || bytes.last() != Some(&b'\n') => {
                let _ = sender.send(ReaderMessage::Error);
                return;
            }
            Ok(_) => {
                bytes.pop(); // newline delimiter is not part of the JSON frame
                match String::from_utf8(bytes) {
                    Ok(line) => {
                        if sender.send(ReaderMessage::Line(line)).is_err() {
                            return;
                        }
                    }
                    Err(_) => {
                        let _ = sender.send(ReaderMessage::Error);
                        return;
                    }
                }
            }
            Err(_) => {
                let _ = sender.send(ReaderMessage::Error);
                return;
            }
        }
    }
}

fn stderr_loop(mut stderr: ChildStderr, retained: Arc<Mutex<Vec<u8>>>) {
    let mut chunk = [0u8; 4096];
    loop {
        match stderr.read(&mut chunk) {
            Ok(0) | Err(_) => return,
            Ok(read) => {
                if let Ok(mut retained) = retained.lock() {
                    let available = MAX_RETAINED_STDERR_BYTES.saturating_sub(retained.len());
                    let keep = available.min(read);
                    retained.extend_from_slice(&chunk[..keep]);
                }
                // Continue draining after the retention cap so the child cannot
                // block on stderr; bytes beyond the cap are intentionally dropped.
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::process::Command;
    use std::sync::atomic::{AtomicU64, Ordering};

    static NEXT_TEMP: AtomicU64 = AtomicU64::new(1);

    struct TestTemp(PathBuf);

    impl TestTemp {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "elu-mcp-stdio-{}-{}",
                std::process::id(),
                NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).expect("create isolated fixture directory");
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TestTemp {
        fn drop(&mut self) {
            let temp = std::env::temp_dir();
            if self.0.starts_with(&temp)
                && self
                    .0
                    .file_name()
                    .is_some_and(|n| n.to_string_lossy().starts_with("elu-mcp-stdio-"))
            {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
    }

    fn fixture(mode: &str) -> (TestTemp, StdioTarget) {
        let temp = TestTemp::new();
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let source = root.join("tests/fixtures/mcp_stdio_helper.rs");
        let program = temp.path().join(if cfg!(windows) {
            "mcp_stdio_helper.exe"
        } else {
            "mcp_stdio_helper"
        });
        let output = Command::new("rustc")
            .arg("--edition=2021")
            .arg(&source)
            .arg("-o")
            .arg(&program)
            .output()
            .expect("compile test-owned stdio helper");
        assert!(
            output.status.success(),
            "rustc helper failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let target = StdioTarget {
            program,
            argv: vec![mode.to_owned()],
            cwd: temp.path().to_path_buf(),
            server_name: "owned-fixture".into(),
            tool: "fixture_echo".into(),
            protocol_version: "2025-11-25".into(),
            initialize_timeout: INITIALIZE_TIMEOUT,
            tool_timeout: TOOL_TIMEOUT,
            close_timeout: CLOSE_TIMEOUT,
        };
        (temp, target)
    }

    fn settings() -> McpAgentSettings {
        let mut settings = McpAgentSettings::defaults();
        settings.transport = McpTransportKind::Stdio;
        settings.server_name = "owned-fixture".into();
        settings.endpoint = OWNED_FIXTURE_ENDPOINT.into();
        settings.approved_tools = vec!["fixture_echo".into()];
        settings
    }

    #[test]
    fn initialize_then_one_approved_tool_preserves_json_result() {
        let (_temp, target) = fixture("success");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        let result = client
            .call_tool(session, "fixture_echo", r#"{"text":"benign"}"#)
            .expect("call one benign fixture tool");
        let value: serde_json::Value = serde_json::from_str(&result).expect("JSON result");
        assert_eq!(value["content"][0]["text"], "benign");
        assert_eq!(value["isError"], false);
        client.disconnect(session).expect("close fixture");
    }

    #[test]
    fn initialize_tool_transcript_has_exact_order_and_one_call() {
        let (temp, target) = fixture("success");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        client
            .call_tool(session, "fixture_echo", "{}")
            .expect("call approved tool once");
        client.disconnect(session).expect("close fixture");
        let transcript = fs::read_to_string(temp.path().join("fixture-transcript.txt"))
            .expect("read controlled transcript");
        assert_eq!(
            transcript.lines().collect::<Vec<_>>(),
            ["initialize", "notifications/initialized", "tools/call"]
        );
    }

    #[test]
    fn fragmented_utf8_responses_decode_as_two_newline_frames() {
        let (_temp, target) = fixture("fragmented");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("fragmented initialize");
        let result = client
            .call_tool(session, "fixture_echo", "{}")
            .expect("fragmented response");
        let value: serde_json::Value = serde_json::from_str(&result).expect("valid JSON result");
        assert_eq!(value["content"][0]["text"], "café");
        client.disconnect(session).expect("close fixture");
    }

    #[test]
    fn unsupported_version_and_missing_tool_capability_are_rejected() {
        for mode in ["wrong_version", "missing_tools"] {
            let (_temp, target) = fixture(mode);
            let mut client = StdioMcpClient::new(target);
            assert!(matches!(
                client.connect(&settings()),
                Err(ExecError::Mcp(_))
            ));
            assert!(client.session.is_none());
        }
    }

    #[test]
    fn initialize_no_response_hits_its_deadline_and_closes_child() {
        let (_temp, target) = fixture_with_all_timeouts(
            "hang_init",
            Duration::from_millis(60),
            Duration::from_millis(500),
            Duration::from_millis(500),
        );
        let mut client = StdioMcpClient::new(target);
        let started = Instant::now();
        assert!(matches!(
            client.connect(&settings()),
            Err(ExecError::Mcp(_))
        ));
        assert!(started.elapsed() < Duration::from_secs(1));
        assert!(
            client.session.is_none(),
            "timed-out initialization closes child"
        );
    }

    #[test]
    fn eof_malformed_json_and_invalid_utf8_fail_closed() {
        for mode in ["eof_tool", "malformed_tool", "invalid_utf8"] {
            let (_temp, target) = fixture(mode);
            let mut client = StdioMcpClient::new(target);
            let session = client.connect(&settings()).expect("initialize fixture");
            assert!(matches!(
                client.call_tool(session, "fixture_echo", "{}"),
                Err(ExecError::Mcp(_))
            ));
            assert!(
                client.session.is_none(),
                "failed protocol session is closed"
            );
        }
    }

    #[test]
    fn stderr_diagnostic_does_not_turn_a_valid_response_into_failure() {
        let (_temp, target) = fixture("stderr_log");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(client.call_tool(session, "fixture_echo", "{}").is_ok());
        client.disconnect(session).expect("close fixture");
    }

    #[test]
    fn one_session_unknown_ids_and_after_close_calls_are_handled() {
        let (_temp, target) = fixture("success");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.connect(&settings()),
            Err(ExecError::Busy(_))
        ));
        assert!(matches!(
            client.call_tool(McpSessionId(session.0 + 1), "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        client.disconnect(session).expect("close fixture");
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(matches!(client.disconnect(session), Err(ExecError::Mcp(_))));
    }

    #[test]
    fn invalid_target_and_tool_gates_do_not_spawn_fixture() {
        let (temp, target) = fixture("success");
        let marker = temp.path().join("fixture-started.marker");
        let mut client = StdioMcpClient::new(target);

        let mut invalid_transport = settings();
        invalid_transport.transport = McpTransportKind::LocalHttpSse;
        assert!(matches!(
            client.connect(&invalid_transport),
            Err(ExecError::EndpointNotApproved(_))
        ));

        let mut wrong_server = settings();
        wrong_server.server_name = "different-server".into();
        assert!(matches!(
            client.connect(&wrong_server),
            Err(ExecError::EndpointNotApproved(_))
        ));

        let mut unapproved_tool = settings();
        unapproved_tool.approved_tools.clear();
        assert!(matches!(
            client.connect(&unapproved_tool),
            Err(ExecError::EndpointNotApproved(_))
        ));

        for endpoint in [
            "",
            "http://127.0.0.1:8787",
            "http://127.0.0.1:8788",
            "stdio://local-agent",
            "stdio://different-fixture",
        ] {
            let mut invalid_endpoint = settings();
            invalid_endpoint.endpoint = endpoint.into();
            assert!(
                matches!(
                    client.connect(&invalid_endpoint),
                    Err(ExecError::EndpointNotApproved(_))
                ),
                "endpoint must be rejected before spawn: {endpoint}"
            );
        }
        assert!(!marker.exists(), "rejected settings must not spawn fixture");
    }

    #[test]
    fn json_rpc_and_tool_errors_are_not_reported_as_success() {
        let (_temp, target) = fixture("protocol_error");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(
            client.session.is_none(),
            "protocol error closes the failed session"
        );

        let (_temp, target) = fixture("tool_error");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(
            client.session.is_none(),
            "tool error closes the failed session"
        );
    }

    #[test]
    fn mismatched_response_id_fails_closed() {
        let (_temp, target) = fixture("wrong_id");
        let mut client = StdioMcpClient::new(target);
        assert!(matches!(
            client.connect(&settings()),
            Err(ExecError::Mcp(_))
        ));
    }

    #[test]
    fn disconnect_with_wrong_id_preserves_the_live_session() {
        let (_temp, target) = fixture("success");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.disconnect(McpSessionId(session.0 + 1)),
            Err(ExecError::Mcp(_))
        ));
        assert!(client.session.is_some(), "wrong id must not drop ownership");
        assert!(client
            .call_tool(session, "fixture_echo", r#"{"text":"still-owned"}"#)
            .is_ok());
        client.disconnect(session).expect("close original session");
    }

    #[test]
    fn timed_out_tool_closes_or_retains_child_without_blocking_or_reconnecting() {
        let (_temp, target) = fixture_with_timeouts(
            "hang_tool",
            Duration::from_millis(60),
            Duration::from_millis(60),
        );
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        let started = Instant::now();
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(started.elapsed() < Duration::from_millis(500));
        assert!(client.session.is_none(), "timed-out child must be closed");
    }

    #[test]
    fn blocked_stdin_write_is_deadline_bounded_and_closes_the_child() {
        let (_temp, target) = fixture_with_timeouts(
            "no_read",
            Duration::from_millis(60),
            Duration::from_millis(500),
        );
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        // Keep the complete JSON-RPC frame within the approved 1 MiB cap while
        // still exceeding the OS pipe buffer so the writer must hit its deadline.
        let args = format!(r#"{{"payload":"{}"}}"#, "x".repeat(700 * 1024));
        let started = Instant::now();
        assert!(matches!(
            client.call_tool(session, "fixture_echo", &args),
            Err(ExecError::Mcp(_))
        ));
        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(
            client.session.is_none(),
            "blocked write cleanup closes child"
        );
    }

    #[test]
    fn outgoing_frame_over_one_mib_is_rejected_and_closes_owned_session() {
        let (_temp, target) = fixture("success");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        let args = format!(r#"{{"text":"{}"}}"#, "x".repeat(1024 * 1024));
        assert!(matches!(
            client.call_tool(session, "fixture_echo", &args),
            Err(ExecError::Mcp(_))
        ));
        assert!(
            client.session.is_none(),
            "oversized request closes owned session"
        );
    }

    #[test]
    fn incoming_frame_over_one_mib_is_rejected_and_closes_owned_session() {
        let (_temp, target) = fixture("oversized_tool_response");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(
            client.session.is_none(),
            "oversized response closes owned session"
        );
    }

    #[test]
    fn exactly_one_thousand_non_response_messages_are_allowed_per_request() {
        let (_temp, target) = fixture("notifications_1000");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(client.call_tool(session, "fixture_echo", "{}").is_ok());
        client.disconnect(session).expect("close fixture");
    }

    #[test]
    fn more_than_one_thousand_non_response_messages_reject_and_close_session() {
        let (_temp, target) = fixture("notifications_1001");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        assert!(matches!(
            client.call_tool(session, "fixture_echo", "{}"),
            Err(ExecError::Mcp(_))
        ));
        assert!(
            client.session.is_none(),
            "message overflow closes owned session"
        );
    }

    #[test]
    fn invalid_notification_shapes_fail_closed_before_accepting_response() {
        for mode in [
            "notification_null",
            "notification_array",
            "notification_wrong_version",
            "notification_missing_method",
        ] {
            let (_temp, target) = fixture(mode);
            let mut client = StdioMcpClient::new(target);
            let session = client.connect(&settings()).expect("initialize fixture");
            assert!(matches!(
                client.call_tool(session, "fixture_echo", "{}"),
                Err(ExecError::Mcp(_))
            ), "invalid JSON-RPC notification must reject: {mode}");
            assert!(
                client.session.is_none(),
                "invalid protocol message closes owned session: {mode}"
            );
        }
    }

    #[test]
    fn stderr_retains_at_most_sixty_four_kibibytes_and_drains_overflow() {
        let (_temp, target) = fixture("stderr_large");
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        let retained = client.session.as_ref().unwrap().stderr_retained.clone();
        assert!(client.call_tool(session, "fixture_echo", "{}").is_ok());
        client.disconnect(session).expect("close fixture");
        let retained = retained.lock().unwrap();
        assert_eq!(retained.len(), 64 * 1024);
        assert!(retained.iter().all(|byte| *byte == b's'));
    }

    #[test]
    fn close_deadline_retains_unsettled_io_workers_without_joining_them() {
        let (_temp, target) = fixture_with_timeouts(
            "hold_pipe",
            Duration::from_millis(500),
            Duration::from_millis(60),
        );
        let mut client = StdioMcpClient::new(target);
        let session = client.connect(&settings()).expect("initialize fixture");
        client
            .call_tool(session, "fixture_echo", "{}")
            .expect("call fixture");
        let started = Instant::now();
        assert!(matches!(client.disconnect(session), Err(ExecError::Mcp(_))));
        assert!(started.elapsed() < Duration::from_millis(400));
        assert!(client.session.is_some(), "unsettled workers remain owned");
        assert!(matches!(
            client.connect(&settings()),
            Err(ExecError::Busy(_))
        ));
        thread::sleep(Duration::from_millis(400));
        client.disconnect(session).expect("workers have settled");
    }

    fn fixture_with_timeouts(
        mode: &str,
        tool_timeout: Duration,
        close_timeout: Duration,
    ) -> (TestTemp, StdioTarget) {
        fixture_with_all_timeouts(mode, INITIALIZE_TIMEOUT, tool_timeout, close_timeout)
    }

    fn fixture_with_all_timeouts(
        mode: &str,
        initialize_timeout: Duration,
        tool_timeout: Duration,
        close_timeout: Duration,
    ) -> (TestTemp, StdioTarget) {
        let (temp, mut target) = fixture(mode);
        target.initialize_timeout = initialize_timeout;
        target.tool_timeout = tool_timeout;
        target.close_timeout = close_timeout;
        (temp, target)
    }
}
