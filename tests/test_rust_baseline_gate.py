import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/rust-baseline/acceptance.json'

class RustBaselineGate(unittest.TestCase):
    def test_cargo_artifacts_hidden_sources_and_locks_visible(self):
        spec = json.loads(FIXTURE.read_text(encoding='utf-8'))
        for path, expected in spec['ignored_paths'].items():
            with self.subTest(path=path):
                result = subprocess.run(['git', 'check-ignore', '--no-index', '--', path], cwd=ROOT, capture_output=True)
                self.assertIn(result.returncode, (0, 1), result.stderr.decode())
                self.assertEqual(result.returncode == 0, expected, path)

    def test_windows_workflow_is_fail_closed_and_runs_each_rust_gate(self):
        path = ROOT / '.github/workflows/rust-gate.yml'
        self.assertTrue(path.is_file(), 'independent Rust workflow missing')
        source = path.read_text(encoding='utf-8')
        # PyYAML is optional: do not add a runtime dependency just for this audit.
        try:
            import yaml
        except ImportError:
            yaml = None
        if yaml:
            workflow = yaml.safe_load(source)
            triggers = workflow.get('on', workflow.get(True, {}))
            self.assertTrue({'pull_request', 'workflow_dispatch'} <= set(triggers))
            self.assertTrue(any('windows' in str(job.get('runs-on', '')).lower() for job in workflow['jobs'].values()))
        else:
            self.assertRegex(source, r'(?m)^\s+pull_request\s*:')
            self.assertRegex(source, r'(?m)^\s+workflow_dispatch\s*:')
            self.assertRegex(source, r'(?im)^\s+runs-on:\s*[\"\x27]?windows')
        self.assertRegex(source, r'uses:\s*actions/checkout@')
        self.assertRegex(source, r'uses:\s*actions/setup-python@')
        self.assertNotRegex(source, r'(?im)^\s*continue-on-error:\s*(?!false\b|False\b)\S+')
        # Evaluate run scripts with their job/step working directory, or manifest-path.
        expected = json.loads(FIXTURE.read_text(encoding='utf-8'))['cargo_gates']
        for gate in expected:
            flags = gate['flags']
            lines = [line for line in source.splitlines() if re.search(r'\bcargo(?:\.exe)?\s+test\b', line)]
            matches = [line for line in lines if all(flag in line.split() for flag in flags)]
            self.assertTrue(matches, f'missing cargo test flags {flags}')
        self.assertIn('apps/sgenaxis-desktop', source)
        self.assertIn('src-tauri', source, 'Tauri host is an independent Cargo boundary')
        steps = re.split(r'(?m)^\s+-\s+(?=name:|run:|uses:)', source)
        workspace_steps = []
        host_steps = []
        for step in steps:
            if not re.search(r'\bcargo(?:\.exe)?\s+test\b', step):
                continue
            if re.search(r'working-directory:\s*[\"\x27]?apps/sgenaxis-desktop/src-tauri\b', step) or re.search(r'--manifest-path\s+[\"\x27]?apps/sgenaxis-desktop/src-tauri/Cargo.toml', step):
                host_steps.append(step)
            elif re.search(r'working-directory:\s*[\"\x27]?apps/sgenaxis-desktop\s*[\"\x27]?\s*$', step, re.M) or re.search(r'--manifest-path\s+[\"\x27]?apps/sgenaxis-desktop/Cargo.toml', step):
                workspace_steps.append(step)
        self.assertTrue(any('--workspace' in step and '--locked' in step for step in workspace_steps), 'workspace test must resolve formal workspace')
        self.assertTrue(any('--all-features' in step and '--lib' in step and '--locked' in step for step in workspace_steps), 'EXEC test must resolve formal workspace')
        self.assertTrue(any('--lib' in step and '--locked' in step for step in host_steps), 'Tauri test must resolve independent host')

if __name__ == '__main__':
    unittest.main()
