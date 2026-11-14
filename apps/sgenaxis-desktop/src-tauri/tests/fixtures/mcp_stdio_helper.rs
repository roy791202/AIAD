use std::fs::OpenOptions;
use std::io::{self, BufRead, Write};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    if mode == "hold_pipe_child" {
        thread::sleep(Duration::from_millis(350));
        return;
    }
    let _ = OpenOptions::new()
        .create(true)
        .append(true)
        .open("fixture-started.marker");
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(line) => line,
            Err(_) => return,
        };
        let event = if line.contains("\"method\":\"initialize\"") {
            "initialize"
        } else if line.contains("notifications/initialized") {
            "notifications/initialized"
        } else if line.contains("\"method\":\"tools/call\"") {
            "tools/call"
        } else {
            "other"
        };
        if let Ok(mut log) = OpenOptions::new()
            .create(true)
            .append(true)
            .open("fixture-transcript.txt")
        {
            let _ = writeln!(log, "{event}");
        }
        if line.contains("\"method\":\"initialize\"") {
            if mode == "hang_init" {
                continue; // no response; exit on client stdin close
            }
            let id = if mode == "wrong_id" { 99 } else { 1 };
            let version = if mode == "wrong_version" {
                "2099-01-01"
            } else {
                "2025-11-25"
            };
            let capabilities = if mode == "missing_tools" {
                "{}"
            } else {
                "{\"tools\":{}}"
            };
            let response = format!(
                "{{\"jsonrpc\":\"2.0\",\"id\":{id},\"result\":{{\"protocolVersion\":\"{version}\",\"capabilities\":{capabilities},\"serverInfo\":{{\"name\":\"owned-fixture\",\"version\":\"1\"}}}}}}"
            );
            write_response(&mut stdout, &response, mode == "fragmented");
        } else if mode == "no_read" && line.contains("notifications/initialized") {
            thread::sleep(Duration::from_secs(10));
            return;
        } else if line.contains("\"method\":\"tools/call\"") {
            if mode == "hang_tool" {
                thread::sleep(Duration::from_secs(10));
                continue;
            }
            let invalid_notification = match mode.as_str() {
                "notification_null" => Some("null"),
                "notification_array" => Some("[]"),
                "notification_wrong_version" => {
                    Some(r#"{"jsonrpc":"3.0","method":"notifications/progress"}"#)
                }
                "notification_missing_method" => {
                    Some(r#"{"jsonrpc":"2.0","params":{}}"#)
                }
                _ => None,
            };
            if let Some(message) = invalid_notification {
                writeln!(stdout, "{message}").unwrap();
                stdout.flush().unwrap();
            }
            if mode == "notifications_1000" || mode == "notifications_1001" {
                let count = if mode == "notifications_1000" {
                    1000
                } else {
                    1001
                };
                for sequence in 0..count {
                    writeln!(
                        stdout,
                        "{{\"jsonrpc\":\"2.0\",\"method\":\"notifications/progress\",\"params\":{{\"sequence\":{sequence}}}}}"
                    )
                    .unwrap();
                }
                stdout.flush().unwrap();
            }
            if mode == "stderr_large" {
                eprint!("{}", "s".repeat(70 * 1024));
            }
            if mode == "oversized_tool_response" {
                let response = format!(
                    "{{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{{\"content\":[{{\"type\":\"text\",\"text\":\"{}\"}}],\"isError\":false}}}}",
                    "x".repeat(1024 * 1024)
                );
                writeln!(stdout, "{response}").unwrap();
                stdout.flush().unwrap();
                continue;
            }
            match mode.as_str() {
                "eof_tool" => return,
                "malformed_tool" => {
                    stdout.write_all(b"not-json\n").unwrap();
                    stdout.flush().unwrap();
                    continue;
                }
                "invalid_utf8" => {
                    stdout.write_all(b"{\"invalid\":\xff}\n").unwrap();
                    stdout.flush().unwrap();
                    continue;
                }
                "stderr_log" => {
                    eprintln!("controlled fixture diagnostic");
                }
                _ => {}
            }
            let response = match mode.as_str() {
                "protocol_error" => "{\"jsonrpc\":\"2.0\",\"id\":2,\"error\":{\"code\":-32602,\"message\":\"fixture invalid\"}}".to_owned(),
                "tool_error" => "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"content\":[{\"type\":\"text\",\"text\":\"controlled failure\"}],\"isError\":true}}".to_owned(),
                "fragmented" => "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"content\":[{\"type\":\"text\",\"text\":\"café\"}],\"isError\":false}}".to_owned(),
                _ => "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"content\":[{\"type\":\"text\",\"text\":\"benign\"}],\"isError\":false}}".to_owned(),
            };
            write_response(&mut stdout, &response, mode == "fragmented");
        }
    }
    if mode == "hold_pipe" {
        let _ = Command::new(std::env::current_exe().unwrap())
            .arg("hold_pipe_child")
            .stdin(Stdio::null())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn();
    }
}

fn write_response(stdout: &mut impl Write, response: &str, fragmented: bool) {
    if !fragmented {
        writeln!(stdout, "{response}").unwrap();
        stdout.flush().unwrap();
        return;
    }
    let mut frame = response.as_bytes().to_vec();
    frame.push(b'\n');
    for chunk in frame.chunks(3) {
        stdout.write_all(chunk).unwrap();
        stdout.flush().unwrap();
        thread::sleep(Duration::from_millis(1));
    }
}
