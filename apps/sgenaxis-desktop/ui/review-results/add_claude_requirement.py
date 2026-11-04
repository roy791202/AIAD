"""Record the owner's Claude Code compatibility requirement in planning artifacts."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, re, sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/board'))
from board_core import snapshot_safe

requirement = {
    'id': 'REQ-AGENT-CLAUDE-01',
    'client': 'Claude Code',
    'status': 'REQUIRED_NOT_IMPLEMENTED',
    'cli_dispatch': 'Required; claude -p noninteractive execution, structured output, cancel and exit classification; real integration NOT RUN.',
    'mcp_tools': 'Required; inbound tools for task query/claim/report through shared application ports; stdio and HTTP transport choices require compatibility verification.',
    'reporting': 'Same ReportRun contract, identity/lease/idempotency/evidence gates as other clients; no automatic acceptance.',
    'embedded_ui': 'Host capability dependent; Claude Code MCP tool support does not establish interactive UI support. Capability detection and text/tool fallback required; current host NOT VERIFIED.',
    'acceptance': ['CLI target version recorded and tested', 'MCP tool discovery/query/claim/report verified', 'Missing configuration/auth rejected readably', 'Cancel/disconnect/duplicate/stale reports tested', 'No embedded-UI support means tools remain usable'],
    'sources': ['https://code.claude.com/docs/en/headless', 'https://code.claude.com/docs/en/mcp'],
    'verification': 'Official documentation read; no Claude login, configuration change, service launch or live run performed.',
}
for name in ['dispatch-modes', 'report-ingress']:
    path = ROOT / 'reports/rust-improvements' / name / 'module.html'
    text = path.read_text(encoding='utf-8')
    pattern = r'(<script\b[^>]*type=["\x27]application/json["\x27][^>]*>)(.*?)(</script>)'
    def update(match):
        spec = json.loads(match.group(2))
        spec['claude_code_requirement'] = requirement
        return match.group(1) + json.dumps(spec, ensure_ascii=False).replace('<', '\\u003c') + match.group(3)
    text, count = re.subn(pattern, update, text, count=1, flags=re.S)
    assert count == 1
    section = '<section id="claude-code-requirement"><h2>Claude Code compatibility — REQUIRED / NOT IMPLEMENTED</h2><p>Owner requirement REQ-AGENT-CLAUDE-01: support CLI launch plus inbound MCP task query, claim and reporting, using the same Rust application contracts. Real integration tests: NOT RUN.</p><p>Embedded Web UI is host-capability dependent. MCP tools must remain usable without UI; current Claude Code UI support is NOT VERIFIED.</p><p>Acceptance: record tested version; test CLI output/cancel/exit, MCP discovery/claim/report, missing auth, disconnect, duplicate and stale reports. Agent completion cannot self-approve acceptance.</p><p>Official sources: <a href="https://code.claude.com/docs/en/headless">Claude Code CLI automation</a> · <a href="https://code.claude.com/docs/en/mcp">Claude Code MCP</a>.</p></section>'
    text = re.sub(r'<section id="claude-code-requirement">.*?</section>', '', text, flags=re.S)
    if '</body>' in text:
        text = text.replace('</body>', section + '</body>')
    elif '</html>' in text:
        text = text.replace('</html>', section + '</html>')
    else:
        text += '\n' + section
    path.write_text(text, encoding='utf-8')

now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
def mutate(data):
    for task in data['tasks']:
        if task['id'] in {'PD-RUST-DISPATCH-MODES-PLAN-01','PD-RUST-REPORT-INGRESS-PLAN-01','PD-RUST-DISPATCH-MODES-DEC-01'}:
            task['note'] += '\n[' + now + '] Owner added REQ-AGENT-CLAUDE-01: Claude Code required for CLI and inbound MCP query/claim/report. Shared ReportRun and evidence gates. UI capability dependent, current host NOT VERIFIED; real compatibility NOT RUN. Official sources recorded in module HTML. Requirement inclusion is confirmed; detailed architecture remains proposed.'
            task['updatedAt'] = now
            task['updatedBy'] = 'agent'
            task['version'] = int(task.get('version', 1)) + 1
    data['asOf'] = now
snapshot_safe.mutate_snapshot_file(ROOT / 'docs/PROJECT-BOARD.html', mutate)
print('Recorded Claude Code requirement in both structured module specs and board')
