"""CI-PR1-REPAIR: distinguish executable test disables from documentary text."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "added_test_disables", ROOT / "scripts/check_added_test_disables.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.mark.parametrize("path,source", [
    ("test_alias.py", "import pytest as p\np.skip('missing')\n"),
    ("test_case.py", "import pytest\npytest.skip('missing tool')\n"),
    ("test_case.py", "@pytest.mark.skipif(True, reason='missing')\ndef test_x(): pass\n"),
    ("test_case.py", "@unittest.skip('missing')\ndef test_x(): pass\n"),
    ("test_case.js", "test.skip('case', () => {});\n"),
    ("test_case.ts", "describe.only('suite', () => {});\n"),
    ("test_case.rs", "#[ignore]\n#[test]\nfn case() {}\n"),
    ("test_case.rs", "#[ignore = \"reason\"]\nfn case() {}\n"),
])
def test_ci_pr1_rejects_executable_disables(path, source):
    assert guard.disabled_lines(path, source)


@pytest.mark.parametrize("path,source", [
    ("review.py", "assert '#[ignore]' not in source\n"),
    ("review.py", "assert 'pytest.skip(\"reason\")' not in source\n"),
    ("review.py", "# pytest.skip('not executable')\nvalue = 1\n"),
    ("review.js", 'const evidence = "test.skip(\\\"case\\\")";\n'),
    ("review.rs", 'let evidence = "#[ignore]";\n'),
    ("module.feature", "Then the text contains test.skip()\n"),
])
def test_ci_pr1_accepts_quoted_or_documentary_evidence(path, source):
    assert guard.disabled_lines(path, source) == set()


def test_ci_pr1_rust_attribute_line_is_not_shifted_by_blank_lines():
    assert guard.disabled_lines("case.rs", "\n\n#[ignore]\nfn x() {}\n") == {3}


@pytest.mark.parametrize("source,expected", [
    ("import pytest\npytest.skip('missing')\n", 1),
    ("assert '#[ignore]' not in text\n", 0),
])
def test_ci_pr1_staged_source_is_checked_without_reading_worktree(tmp_path, source, expected):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "case.py").write_text("value = 1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "fixture")
    (tmp_path / "case.py").write_text(source, encoding="utf-8")
    git("add", ".")
    (tmp_path / "case.py").write_text("value = 2\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_added_test_disables.py")],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("path,source,expected", [
    ("case.rs", "#[test] #[ignore] fn case() {}", {1}),
    ("case.js", 'const result = `${test.skip("case", () => {})}`;', {1}),
    ("case.js", 'test\n .skip("case", () => {});', {1, 2}),
])
def test_ci_pr1_rejects_inline_interpolated_and_multiline_disables(path, source, expected):
    assert guard.disabled_lines(path, source) == expected


@pytest.mark.parametrize("source,expected", [
    ('const evidence = `test.skip("quoted", () => {})`;', set()),
    ('const evidence = `line one\n test.only("quoted")\n`;', set()),
    ('const result = `text ${test.skip("case", () => {})}`;', {1}),
    ('const result = `text ${`nested ${describe.only("suite", () => {})}`}`;', {1}),
    ('const result = `text ${({key: "}"}).key} ${test.skip("case", () => {})}`;', {1}),
    (r'const evidence = `escaped \${test.skip("quoted")}`;', set()),
    ('const result = `text ${/* } ignored */ test.skip("case", () => {})}`;', {1}),
    ('const result = `text ${"test.skip(quoted)"}`;', set()),
    ('const result = `text ${\n test\n .skip("case", () => {})}`;', {2, 3}),
])
def test_ci_pr1_template_text_and_executable_expressions(source, expected):
    assert guard.disabled_lines("case.js", source) == expected


@pytest.mark.parametrize("source,expected", [
    ('const regex = /id="(document-[^"]+)"/g;', set()),
    ('const result = `${/}/.test("}")} ${test.skip("case", () => {})}`;', {1}),
    ('const evidence = /test.skip("quoted")/;', set()),
])
def test_ci_pr1_javascript_regex_literals(source, expected):
    assert guard.disabled_lines("case.js", source) == expected


@pytest.mark.parametrize("source,expected", [
    ('const S: &str = r#"""#; #[ignore] fn test_x() {} // "', {1}),
    ('const S: &str = r##"text " #[ignore] fn fake() {} "##;', set()),
    ('const S: &[u8] = br#"text " #[ignore] fn fake() {} "#;', set()),
    ('const S: &str = r#"line one\n #[ignore]\n"#;\n#[ignore] fn real() {}', {4}),
    ('/* outer /* inner */ #[ignore] fn fake() {} */ #[ignore] fn real() {}', {1}),
    ('/* outer /* inner */ #[ignore] fn fake() {} */', set()),
    ("const C: char = '\"'; #[ignore] fn real() {}", {1}),
    ("fn borrow<'a>(x: &'a str) {} #[ignore] fn real() {}", {1}),
])
def test_ci_pr1_rust_raw_strings_characters_and_nested_comments(source, expected):
    assert guard.disabled_lines("case.rs", source) == expected


@pytest.mark.parametrize("source", [
    'const value = {} / test.skip("case", () => {}) / 2;',
    "const value = 'a' / test.skip('case', () => {}) / 2;",
    'const value = `a` / test.skip("case", () => {}) / 2;',
    'const value = /a/ / test.skip("case", () => {}) / 2;',
    'const value = `${{} / test.skip("case", () => {}) / 2}`;',
])
def test_ci_pr1_division_preserves_executable_test_disable(source):
    assert guard.disabled_lines("case.js", source) == {1}


@pytest.mark.parametrize("suffix,expected", [(".bin", 0), (".py", 2), (".PY", 2)])
def test_ci_pr1_base_mode_limits_diff_decoding_to_supported_sources(tmp_path, suffix, expected):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path).decode().strip()
    git("init")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "case.py").write_text("value = 1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "fixture")
    base = git("rev-parse", "HEAD")
    (tmp_path / ("legacy" + suffix)).write_bytes(b"legacy byte \xff\n")
    git("add", ".")
    git("commit", "-m", "fixture")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_added_test_disables.py"), "--base", base],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("property_name", ["return", "throw", "case", "yield", "await"])
def test_ci_pr1_keyword_properties_are_division_not_regex(property_name):
    source = f'const value = obj.{property_name} / test.skip("case", () => {{}}) / 2;'
    assert guard.disabled_lines("case.js", source) == {1}


@pytest.mark.parametrize("alias", ["context", "suite", "specify"])
def test_ci_pr1_preserves_generic_local_hook_skip_detection(alias):
    assert guard.disabled_lines("case.js", f"{alias}.skip('case', () => {{}});") == {1}


@pytest.mark.parametrize("path,source", [
    ("case.js", "factory().skip('case', () => {});"),
    ("case.py", "factory().skip('case')"),
])
def test_ci_pr1_preserves_original_hook_chained_receiver_detection(path, source):
    assert guard.disabled_lines(path, source) == {1}
