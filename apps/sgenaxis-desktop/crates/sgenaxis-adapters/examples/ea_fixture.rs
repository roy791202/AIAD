#![forbid(unsafe_code)]

use std::io::{self, BufRead, Write};

fn run_fixture<R: BufRead, W: Write>(mut input: R, mut output: W) -> io::Result<()> {
    writeln!(output, "EA_FIXTURE_READY")?;
    output.flush()?;
    let mut line = String::new();
    loop {
        line.clear();
        if input.read_line(&mut line)? == 0 {
            return Ok(());
        }
        if line.trim_end_matches(['\r', '\n']) == "STOP" {
            return Ok(());
        }
        write!(output, "EA_ECHO:{line}")?;
        output.flush()?;
    }
}

fn main() -> io::Result<()> {
    run_fixture(io::stdin().lock(), io::stdout().lock())
}

#[cfg(test)]
mod tests {
    use super::run_fixture;
    use std::io::{self, BufRead, Cursor, ErrorKind, Read, Write};

    const READY: &str = "EA_FIXTURE_READY\n";

    #[test]
    fn startup_then_eof_emits_ready_marker() {
        let mut output = Vec::new();
        assert!(run_fixture(Cursor::new(b""), &mut output).is_ok());
        assert_eq!(output, READY.as_bytes());
    }

    #[test]
    fn utf8_line_with_space_is_echoed() {
        let mut output = Vec::new();
        assert!(run_fixture(Cursor::new("héllo wide world\n".as_bytes()), &mut output).is_ok());
        assert_eq!(output, "EA_FIXTURE_READY\nEA_ECHO:héllo wide world\n".as_bytes());
    }

    #[test]
    fn crlf_line_is_echoed() {
        let mut output = Vec::new();
        assert!(run_fixture(Cursor::new(b"line\r\n"), &mut output).is_ok());
        assert_eq!(output, b"EA_FIXTURE_READY\nEA_ECHO:line\r\n");
    }

    #[test]
    fn final_unterminated_line_is_echoed_at_eof() {
        let mut output = Vec::new();
        assert!(run_fixture(Cursor::new(b"last"), &mut output).is_ok());
        assert_eq!(output, b"EA_FIXTURE_READY\nEA_ECHO:last");
    }

    #[test]
    fn stop_terminates_before_later_input_without_asserting_stop_echo() {
        let mut output = Vec::new();
        assert!(run_fixture(Cursor::new(b"STOP\nafter-stop\n"), &mut output).is_ok());
        assert!(!output.windows(b"after-stop".len()).any(|part| part == b"after-stop"));
    }

    struct FailingReader;

    impl Read for FailingReader {
        fn read(&mut self, _buffer: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::new(ErrorKind::PermissionDenied, "injected read error"))
        }
    }

    impl BufRead for FailingReader {
        fn fill_buf(&mut self) -> io::Result<&[u8]> {
            Err(io::Error::new(ErrorKind::PermissionDenied, "injected read error"))
        }

        fn consume(&mut self, _amount: usize) {}
    }

    struct FailingWriter;

    impl Write for FailingWriter {
        fn write(&mut self, _buffer: &[u8]) -> io::Result<usize> {
            Err(io::Error::new(ErrorKind::BrokenPipe, "injected write error"))
        }

        fn flush(&mut self) -> io::Result<()> {
            Err(io::Error::new(ErrorKind::BrokenPipe, "injected flush error"))
        }
    }

    #[test]
    fn read_and_write_errors_preserve_their_io_kinds() {
        let mut sink = Vec::new();
        let read_kind = run_fixture(FailingReader, &mut sink).unwrap_err().kind();
        let write_kind = run_fixture(Cursor::new(b""), FailingWriter)
            .unwrap_err()
            .kind();
        assert_eq!(
            [read_kind, write_kind],
            [ErrorKind::PermissionDenied, ErrorKind::BrokenPipe]
        );
    }
}
