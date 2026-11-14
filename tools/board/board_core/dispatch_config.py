"""Driven adapter: tools/board/dispatch-agents.json loading, argv expansion and the agent prompt.

INV-BD-15 argv = configured list + placeholders {repo} {python} {prompt_file} {prompt_pointer}; card text never.
INV-BD-16 argv[1:] must match SAFE_ARG_RE (Windows .cmd shims are parsed by cmd.exe).
INV-BD-17 permission-bypass flags are rejected at load time.
INV-BD-39 "detached": true marks a GUI window agent (Antigravity): prompt via an ASCII pointer argument only;
          command[0] may use %VAR% (expanded); a .cmd/.bat executable path must pass SAFE_ARG_RE as well.
INV-BD-47 the prompt's report section puts the report file first (exact path + JSON filled with the real card
          and run), the output marker second (captured-output agents only, shown with a placeholder), and
          `board.py report` last as optional — the agent's shell may refuse to run it.
"""
import json
import os
import re

from . import dispatch, report_channels

SCHEMA = "hb-board-dispatch/1"
PLACEHOLDERS = ("{repo}", "{python}", "{prompt_file}", "{prompt_pointer}")
PROMPT_VIA = ("stdin", "arg")
SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_\-.:\\/=+,@ ]*$")
AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,31}$")
FORBIDDEN_SUBSTRINGS = ("bypasspermissions", "dangerously", "skip-permissions", "--yolo", "full-auto",
                        "danger-full-access")
FORBIDDEN_EXACT = ("--force", "-f")
DEFAULTS = {
    "timeout_minutes": 60,
    "report_grace_seconds": 120,
    "max_cards_default": 5,
    "max_cards_limit": 50,
    "skip_kinds": list(dispatch.DEFAULT_SKIP_KINDS),
    "max_lanes": 3,
    "fast_fail_seconds": 60,
    "fast_fail_limit": 3,
    "exit_report_grace_seconds": 20,
}
LANES_HARD_CAP = 6


class ConfigError(ValueError):
    """dispatch-agents.json is invalid or an argv would be unsafe."""


def _check_forbidden(agent_id, args):
    for a in args:
        low = a.lower()
        if low in FORBIDDEN_EXACT or any(s in low for s in FORBIDDEN_SUBSTRINGS):
            raise ConfigError("agent %s: permission-bypass flag %r is not allowed (INV-BD-17)" % (agent_id, a))


def _check_placeholders(agent_id, args):
    for a in args:
        for m in re.findall(r"\{[^}]*\}", a):
            if m not in PLACEHOLDERS:
                raise ConfigError("agent %s: unknown placeholder %s (allowed: %s)" % (agent_id, m, ", ".join(PLACEHOLDERS)))


def _positive_int(doc, key):
    v = doc.get(key, DEFAULTS[key])
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise ConfigError("%s must be a positive integer" % key)
    return v


def _validate_agent(a, seen):
    if not isinstance(a, dict):
        raise ConfigError("each agent must be an object")
    aid = a.get("id")
    if not isinstance(aid, str) or not AGENT_ID_RE.match(aid):
        raise ConfigError("illegal agent id %r" % (aid,))
    if aid in seen:
        raise ConfigError("duplicate agent id %s" % aid)
    cmd = a.get("command")
    if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
        raise ConfigError("agent %s: command must be a non-empty list of strings" % aid)
    _check_forbidden(aid, cmd)
    _check_placeholders(aid, cmd)
    via = a.get("prompt_via", "stdin")
    if via not in PROMPT_VIA:
        raise ConfigError("agent %s: prompt_via must be stdin or arg" % aid)
    if via == "arg" and not any("{prompt_pointer}" in x for x in cmd):
        raise ConfigError("agent %s: prompt_via=arg needs {prompt_pointer} in command" % aid)
    detached = a.get("detached", False)
    if not isinstance(detached, bool):
        raise ConfigError("agent %s: detached must be true or false" % aid)
    if detached and via != "arg":
        raise ConfigError("agent %s: a detached (window) agent needs prompt_via=arg" % aid)
    lists = {}
    for key in ("auth_error_patterns", "limit_error_patterns"):
        patterns = a.get(key, [])
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise ConfigError("agent %s: %s must be a list of strings" % (aid, key))
        lists[key] = list(patterns)
    out = dict(lists, id=aid, label=str(a.get("label") or aid), command=list(cmd), prompt_via=via,
               login_hint=str(a.get("login_hint") or ""), detached=detached)
    if "timeout_minutes" in a:
        out["timeout_minutes"] = _positive_int(a, "timeout_minutes")
    return out


def parse_config(doc):
    if not isinstance(doc, dict):
        raise ConfigError("config must be a JSON object")
    agents = doc.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ConfigError("config needs a non-empty agents list")
    seen, parsed = set(), []
    for a in agents:
        v = _validate_agent(a, seen)
        seen.add(v["id"])
        parsed.append(v)
    skip = doc.get("skip_kinds", DEFAULTS["skip_kinds"])
    if not isinstance(skip, list) or not all(isinstance(k, str) for k in skip):
        raise ConfigError("skip_kinds must be a list of strings")
    cfg = {k: _positive_int(doc, k) for k in ("timeout_minutes", "report_grace_seconds",
                                               "max_cards_default", "max_cards_limit",
                                               "fast_fail_seconds", "fast_fail_limit")}
    if cfg["max_cards_default"] > cfg["max_cards_limit"]:
        raise ConfigError("max_cards_default exceeds max_cards_limit")
    grace = doc.get("exit_report_grace_seconds", DEFAULTS["exit_report_grace_seconds"])
    if not isinstance(grace, int) or isinstance(grace, bool) or grace < 0:
        raise ConfigError("exit_report_grace_seconds must be a non-negative integer")
    cfg["exit_report_grace_seconds"] = grace
    cfg["max_lanes"] = _positive_int(doc, "max_lanes")
    if cfg["max_lanes"] > LANES_HARD_CAP:
        raise ConfigError("max_lanes must be at most %d (INV-BD-26)" % LANES_HARD_CAP)
    cfg["skip_kinds"] = list(skip)
    cfg["agents"] = parsed
    return cfg


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as e:
        raise ConfigError("cannot read %s: %s" % (path, e))
    except ValueError as e:
        raise ConfigError("cannot parse %s: %s" % (path, e))
    return parse_config(doc)


def prompt_pointer(prompt_file, repo=None):
    lead = "Your working folder is %s. " % repo if repo else ""
    return lead + ("Read the UTF-8 file %s and follow every instruction in it exactly. It assigns you one board card."
                   % prompt_file)


def executable(agent):
    """command[0] with %VAR% / $VAR expanded (INV-BD-39); availability = this resolves to a program."""
    return os.path.expandvars(agent["command"][0])


def resolve_argv(agent, repo, python, prompt_file):
    pointer = prompt_pointer(prompt_file, repo if agent.get("detached") else None)
    values = {"{repo}": repo, "{python}": python, "{prompt_file}": prompt_file, "{prompt_pointer}": pointer}
    argv = []
    for a in agent["command"]:
        for k, v in values.items():
            a = a.replace(k, v)
        argv.append(a)
    argv[0] = os.path.expandvars(argv[0])
    checked = argv if argv[0].lower().endswith((".cmd", ".bat")) else argv[1:]
    for a in checked:
        if not SAFE_ARG_RE.match(a):
            raise ConfigError("unsafe argument for agent %s: %r (INV-BD-16)" % (agent["id"], a))
    return argv


def report_command(card_id, outcome, run_id, tasks_path, state_path, default_tasks_path, default_state_path,
                   board_cli="tools/board/board.py"):
    parts = ["python %s" % board_cli]
    if tasks_path and tasks_path != default_tasks_path:
        parts.append("--tasks %s" % tasks_path)
    if state_path and state_path != default_state_path:
        parts.append("--dispatch-state %s" % state_path)
    parts.append("report %s %s --run %s --note \"<one line>\"" % (card_id, outcome, run_id))
    return " ".join(parts)


def parallel_section(lane_id, others):
    """INV-BD-29: other lanes edit the same checkout at the same time."""
    if not others:
        return []
    lines = ["## 0. Parallel lanes — other agents are working in this same folder right now",
             "You are lane %s. These lanes are running other cards at the same time:" % (lane_id or "?")]
    for o in others:
        lines.append("- lane %s (%s): %s — %s" % (o.get("laneId"), o.get("agent"), o.get("cardId"),
                                                  (o.get("title") or "").strip() or "(no title)"))
    lines += [
        "Rules while sharing the checkout:",
        "- Stay inside your own card. Do not edit files that clearly belong to another lane's card.",
        "- Always re-read a file immediately before you edit it; never write from a copy you read earlier.",
        "- Keep edits minimal and local (small targeted replacements, no whole-file rewrites of shared files).",
        "- Shared docs (CHANGELOG, PROJECT-BOARD snapshot): re-read immediately before editing; append or",
        "  make the smallest replacement; never rewrite the whole file from an earlier copy.",
        "- If another lane's change breaks your build or tests and you cannot proceed, report blocked with the reason.",
        "",
    ]
    return lines


def window_section(repo, agent_label):
    """INV-BD-39: a GUI agent opens in an empty IDE window, and its terminal commands may wait for approval."""
    return [
        "## 0. You are running inside a %s IDE window" % agent_label,
        "- The window has no folder open. Your working folder is %s: use absolute paths under it, and run" % repo,
        "  terminal commands with that folder as the current directory.",
        "- The IDE may ask the human to click Allow before a terminal command runs. You do not need the",
        "  terminal to report: writing the report file in section 3 is enough.",
        "- Nothing watches this window's output. The board only learns the result from the report file (or the",
        "  report command); without it the card times out and is marked needs-human.",
        "",
    ]


def report_section(card_id, run_id, report_file, detached, done_cmd, blocked_cmd):
    """INV-BD-47: file first, marker second (not for window agents), CLI optional."""
    example = json.dumps({"card": card_id, "run": run_id, "outcome": "done", "note": "<one line>"}, ensure_ascii=False)
    lines = [
        "- Then REPORT to the board — without a report the card is marked needs-human. Any ONE channel is",
        "  enough; do A first:",
        "",
        "  A. With your file-editing tool (no terminal needed), create this UTF-8 JSON file:",
        "",
        "       %s" % report_file,
        "",
        "     content (outcome \"done\" or \"blocked\", a one-line note):",
        "",
        "       %s" % example,
        "",
    ]
    if not detached:
        lines += [
            "  B. Make the LAST line of your final answer the marker below, on its own line, with",
            "     <done-or-blocked> replaced by done or blocked (no quotes, no code block):",
            "",
            "       %s" % report_channels.marker_template(run_id),
            "",
        ]
    lines += [
        "  %s. Optionally also run one of these commands (your shell may refuse it; that is fine once A is done):"
        % ("C" if not detached else "B"),
        "",
        "       %s" % done_cmd,
        "       %s" % blocked_cmd,
        "",
        "  Use done only when the card's acceptance is met; otherwise blocked with the reason.",
        "  done turns the card green; blocked turns it red and parks it for the owner.",
    ]
    return lines


def build_prompt(card, run_id, repo, tasks_path, state_path, default_tasks_path, default_state_path,
                 others=None, lane_id=None, detached=False, agent_label="Antigravity", report_file=None):
    cid = card.get("id", "")
    report_file = report_file or os.path.join(repo, "tools", "board", "report-inbox", run_id + ".json")
    board_cli = os.path.join(repo, "tools", "board", "board.py") if detached else "tools/board/board.py"
    done_cmd = report_command(cid, "done", run_id, tasks_path, state_path, default_tasks_path, default_state_path,
                              board_cli)
    blocked_cmd = report_command(cid, "blocked", run_id, tasks_path, state_path, default_tasks_path,
                                 default_state_path, board_cli)

    def field(name):
        return (card.get(name) or "").strip() or "(empty)"

    return "\n".join([
        "# SGenAxis board dispatch — run %s" % run_id,
        "",
        "You were started by the local SGenAxis board dispatcher on 127.0.0.1:28789 in %s." % repo,
        "Work on exactly ONE board card — the one below — then report and exit.",
        "",
        "## 0b. Read scope (hard · save tokens) — PRODUCT-DEVELOPMENT §7.2",
        "- Your SSOT for this job is **this prompt's card excerpt** plus files inside this card's allow-scope.",
        "- **Do not** open or Grep the whole `docs/PROJECT-BOARD.html` to discover other cards.",
        "- **Do not** read other `PD-*` reports under `reports/dispatch-pd/` (only `%s` / related)." % cid,
        "- **Do not** dump all of PRODUCT-DEVELOPMENT into context; open a section only if this card AC requires it.",
        "- Board writes (PD-BOARD-SAFE-01): append a short note on **this card only**, or use `board.py report` /",
        "  `board_core.snapshot_safe.mutate_snapshot_file`. Only replace `#board-snapshot` JSON; never rewrite the",
        "  whole PROJECT-BOARD.html (must keep DOCTYPE + nav). See tools/board/SNAPSHOT-SAFE.md.",
        "",
    ] + (window_section(repo, agent_label) if detached else []) + parallel_section(lane_id, others) + [
        "## 1. Read the rules first",
        "- Obey PRODUCT-DEVELOPMENT §7.1 (no self-green) and §7.2 (read only this card).",
        "- New ports / schema / ownership / transaction / lifecycle outside this card: stop and report",
        "  blocked with REPLAN_REQUIRED.",
        "- Do not invent tasks outside this card. Do not delete files (trash/archive instead).",
        "- Do not start any agent CLI (claude, cursor-agent, codex, cursor, antigravity / antigravity-ide).",
        "  Only the board dispatcher on port 28789 may launch agents. Never bind or use port 8788.",
        "- If you are stuck for 30 minutes, or the card is ambiguous, stop and report blocked with the reason.",
        "",
        "## 2. Your card",
        "- id: %s" % cid,
        "- ref: %s" % field("ref"),
        "- title: %s" % field("title"),
        "- zone: %s   kind: %s" % (field("zone"), field("kind")),
        "- BDD: %s" % field("bdd"),
        "- TDD: %s" % field("tdd"),
        "- note:",
        field("note"),
        "",
        "## 3. When you finish",
    ] + report_section(cid, run_id, report_file, detached, done_cmd, blocked_cmd) + [
        "- After reporting, stop working (a window agent leaves the window open for the human)." if detached
        else "- After reporting, exit.",
        "",
    ])
