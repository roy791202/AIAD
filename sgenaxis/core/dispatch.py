"""Pure dispatch rules from the Beta board (spec-BOARD-DISPATCH-01 §3.1–3.4, §3.10–3.11, §4–5)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sgenaxis.core import report_channels, timefmt
from sgenaxis.core.board import WorkItem

PRIORITY = ("red", "yellow", "gray")
SKIP_KINDS = frozenset({"note", "epic", "milestone", "release"})
REPORT_OUTCOMES = report_channels.OUTCOMES
NEEDS_HUMAN = ("no-report", "timeout", "terminated", "server-shutdown", "orphaned")
LANE_ERRORS = ("auth-error", "launch-error", "quota-error", "fast-fail")
LANE_STATES = ("idle", "running", "stopping", "error")
STOP_MODES = ("after-current", "now")
PLACEHOLDERS = ("{repo}", "{python}", "{prompt_file}", "{prompt_pointer}")
SAFE_ARG = re.compile(r"^[A-Za-z0-9_\-.:\\/=+,@ ]*$")
BANNED_SUBSTRINGS = ("bypasspermissions", "dangerously", "skip-permissions", "--yolo", "full-auto", "danger-full-access")
BANNED_EXACT = ("--force", "-f")


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    label: str
    command: tuple[str, ...]
    prompt_via: str = "stdin"
    detached: bool = False
    auth_patterns: tuple[str, ...] = ()
    limit_patterns: tuple[str, ...] = ()
    login_hint: str = ""


AGENTS = {
    spec.agent_id: spec
    for spec in (
        AgentSpec(
            "claude",
            "Claude Code",
            ("claude", "-p", "--permission-mode", "acceptEdits", "--output-format", "text"),
            auth_patterns=("Not logged in", "Please run /login", "Invalid API key", "authentication_error", "OAuth token has expired"),
            limit_patterns=("hit your session limit", "hit your usage limit", "usage limit reached", "rate_limit_error", "overloaded_error"),
            login_hint="Claude Code 未登入：在另一個 PowerShell 執行 claude，輸入 /login 完成授權後 /exit，再按「開始」。",
        ),
        AgentSpec(
            "cursor-agent",
            "Cursor Agent",
            ("cursor-agent", "-p", "--trust", "--workspace", "{repo}", "--output-format", "text", "{prompt_pointer}"),
            prompt_via="arg",
            auth_patterns=("Authentication required", "Not authenticated", "not logged in", "cursor-agent login", "agent login"),
            limit_patterns=("usage limit", "rate limit", "quota exceeded"),
            login_hint="cursor-agent 未登入：在 PowerShell 執行 cursor-agent login 完成授權，再按「開始」。",
        ),
        AgentSpec(
            "codex",
            "Codex",
            ("codex", "exec", "--sandbox", "workspace-write", "--cd", "{repo}", "--color", "never", "-"),
            auth_patterns=("Not logged in", "codex login", "401 Unauthorized", "Missing OpenAI API key"),
            limit_patterns=("usage limit", "rate limit", "insufficient_quota", "429 Too Many Requests"),
            login_hint="Codex 未登入：在 PowerShell 執行 codex login 完成授權，再按「開始」。",
        ),
        AgentSpec(
            "antigravity",
            "Antigravity（視窗）",
            (
                r"%LOCALAPPDATA%\Programs\Antigravity IDE\bin\antigravity-ide.cmd",
                "chat",
                "--mode",
                "agent",
                "--new-window",
                "--add-file",
                "{prompt_file}",
                "{prompt_pointer}",
            ),
            prompt_via="arg",
            detached=True,
        ),
    )
}
AGENT_LABELS = {agent_id: spec.label for agent_id, spec in AGENTS.items()}


def check_agent_spec(spec: AgentSpec) -> None:
    """Load-time checks (INV-BD-17, INV-BD-39): no permission bypass, known placeholders, pointer for arg mode."""
    for arg in spec.command:
        lowered = arg.lower()
        if lowered in BANNED_EXACT or any(word in lowered for word in BANNED_SUBSTRINGS):
            raise ValueError(f"{spec.agent_id} 的命令列含禁止的權限繞過旗標：{arg}")
        for token in re.findall(r"\{[^}]*\}", arg):
            if token not in PLACEHOLDERS:
                raise ValueError(f"{spec.agent_id} 的命令列有未知的佔位符：{token}")
    if spec.prompt_via not in ("stdin", "arg"):
        raise ValueError(f"{spec.agent_id} 的 prompt_via 只能是 stdin 或 arg")
    if spec.prompt_via == "arg" and not any("{prompt_pointer}" in arg for arg in spec.command):
        raise ValueError(f"{spec.agent_id} 以參數傳 prompt 時命令列必須有 {{prompt_pointer}}")
    if spec.detached and spec.prompt_via != "arg":
        raise ValueError(f"{spec.agent_id} 是視窗模式，prompt 必須以參數指標傳入")


def select_next(items: list[WorkItem], busy: set[str], skipped: set[str]) -> WorkItem | None:
    candidates = [
        item
        for item in items
        if item.zone in PRIORITY
        and item.kind not in SKIP_KINDS
        and item.item_id not in busy
        and item.item_id not in skipped
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (PRIORITY.index(item.zone), timefmt.sort_key(item.updated), item.item_id))


def dispatch_zone(zone: str) -> str:
    return "yellow" if zone == "gray" else zone


def report_zone(outcome: str) -> str:
    if outcome not in REPORT_OUTCOMES:
        raise ValueError(f"回報只能是 done 或 blocked：{outcome}")
    return "green" if outcome == "done" else "red"


def report_note(at: str, outcome: str, note: str) -> str:
    return f"[派工回報 {at} {outcome}] {report_channels.one_line(note)}"


def needs_human_note(at: str, reason: str) -> str:
    return f"[派工 needs-human {at}] {reason}"


def classify_exit(agent: str, output: str) -> str | None:
    """Only for a run that ended without any report (INV-BD-9, INV-BD-33)."""
    spec = AGENTS[agent]
    lowered = (output or "").lower()
    if any(pattern.lower() in lowered for pattern in spec.limit_patterns):
        return "quota-error"
    if any(pattern.lower() in lowered for pattern in spec.auth_patterns):
        return "auth-error"
    return None


def prompt_pointer(prompt_file: str, repo: str | None = None) -> str:
    lead = f"Your working folder is {repo}. " if repo else ""
    return lead + f"Read the UTF-8 file {prompt_file} and follow every instruction in it exactly. It assigns you one board card."


def resolve_argv(agent: str, repo: str, prompt_file: str) -> tuple[str, ...]:
    """INV-BD-15/16: argv only from the agent spec and placeholders; every argument after argv[0] must be cmd-safe."""
    spec = AGENTS[agent]
    check_agent_spec(spec)
    values = {
        "{repo}": repo,
        "{python}": "python",
        "{prompt_file}": prompt_file,
        "{prompt_pointer}": prompt_pointer(prompt_file, repo if spec.detached else None),
    }
    argv = []
    for arg in spec.command:
        for token, value in values.items():
            arg = arg.replace(token, value)
        argv.append(arg)
    for arg in argv[1:]:
        if not SAFE_ARG.match(arg):
            raise ValueError(f"命令列參數含不安全的字元：{arg}")
    return tuple(argv)


def run_env(tasks_path: str, run_id: str, card_id: str, report_file: str) -> dict[str, str]:
    """INV-BD-18 environment for the agent process."""
    return {
        "HB_BOARD_TASKS": tasks_path,
        "HB_DISPATCH_RUN_ID": run_id,
        "HB_DISPATCH_CARD": card_id,
        "HB_DISPATCH_REPORT_FILE": report_file,
        "PYTHONIOENCODING": "utf-8",
    }


@dataclass(frozen=True)
class OtherRun:
    lane_id: str
    agent: str
    card_id: str
    title: str


def build_prompt(
    card: WorkItem,
    run_id: str,
    repo: str,
    *,
    tasks_path: str = "",
    report_file: str = "",
    lane_id: str = "",
    others: tuple[OtherRun, ...] = (),
    detached: bool = False,
    agent_label: str = "",
    report_command: str = "",
) -> str:
    lines = [
        f"# SGenAxis 派工 — run {run_id}",
        "",
        f"你由 SGenAxis 工作台的派工器啟動，工作目錄：{repo}",
        "只做下面這一張卡，做完回報後結束。",
        "",
    ]
    if detached:
        lines += _window_section(repo, agent_label)
    if others:
        lines += _parallel_section(lane_id, others)
    lines += [
        "## 1. 規則",
        "- 先讀工作目錄裡的 AGENTS.md（若有），遵守其中所有安全規則。",
        "- 不得執行任何 git 指令（status / diff / add / commit / push 都不行）。",
        "- 不得呼叫任何 Agent CLI（claude、cursor-agent、codex、cursor、antigravity / antigravity-ide）；只有派工器可以啟動 Agent。",
        "- 不刪檔；不發明這張卡以外的任務；卡關 30 分鐘或卡片不清楚就回報 blocked 並寫原因。",
        "",
        "## 2. 你的卡",
        f"- id：{card.item_id}",
        f"- ref：{card.code or '(空)'}",
        f"- 標題：{card.title or '(空)'}",
        f"- 燈號：{card.zone}　類型：{card.kind}",
        f"- BDD：{card.bdd or '(空)'}",
        f"- TDD：{card.tdd or '(空)'}",
        "- 備註：",
        card.note or "(空)",
        "",
        "## 3. 看板 JSON（必須更新）",
        f"- 這個專案的看板是 {tasks_path or '(未存檔的示範資料)'}。",
        "- 所有執行的 Agent 都必須讓看板 JSON 反映這張卡的結果：照下面的方式回報，SGenAxis 會帶版本檢查寫入 tasks.json。",
        "- 不要直接手改 tasks.json（直接改會略過版本檢查，可能蓋掉別人的修改）。",
        "",
        "## 4. 回報（沒有回報，這張卡會被標成需人工）",
        "  A. 用編輯檔案的工具（不需要終端機）建立這個 UTF-8 JSON 檔：",
        "",
        f"       {report_file}",
        "",
        "     內容（outcome 只能是 done 或 blocked，note 一行）：",
        "",
        f"       {json.dumps({'card': card.item_id, 'run': run_id, 'outcome': 'done', 'note': '<one line>'}, ensure_ascii=False)}",
        "",
    ]
    if not detached:
        lines += [
            "  B. 也可以把最後回答的最後一行寫成下面的標記（把 <done-or-blocked> 換成 done 或 blocked，不要加引號或程式碼區塊）：",
            "",
            f"       {report_channels.marker_template(run_id)}",
            "",
        ]
    if report_command:
        lines += [
            "  C. 或在終端機執行回報指令（它會寫入同一個回報檔；已有回報時會拒絕）：",
            "",
            f'       {report_command} --card {card.item_id} --run {run_id} --file "{report_file}"'
            ' --outcome <done-or-blocked> --note "<one-line note>"',
            "",
        ]
    lines += [
        "  只有驗收條件達成才用 done；否則用 blocked 並寫原因。done 會變綠燈，blocked 會變紅燈並暫停派這張。",
        "- 回報後停止工作（視窗模式請保留視窗給使用者）。" if detached else "- 回報後結束。",
        "",
    ]
    return "\n".join(lines)


def _window_section(repo: str, agent_label: str) -> list[str]:
    return [
        f"## 0. 你在 {agent_label or 'IDE'} 視窗中執行",
        f"- 視窗沒有開資料夾；工作目錄是 {repo}，請用其下的絕對路徑。",
        "- 終端指令可能需要使用者在 IDE 按允許；回報不需要終端機，寫回報檔就夠了。",
        "- 沒有人看這個視窗的輸出；看板只從回報檔得知結果，沒有回報會逾時並標成需人工。",
        "",
    ]


def _parallel_section(lane_id: str, others: tuple[OtherRun, ...]) -> list[str]:
    lines = ["## 0. 平行派工 — 其他 Agent 正在同一個資料夾工作", f"你是 {lane_id}。同時執行中的其他條："]
    lines += [f"- {other.lane_id}（{other.agent}）：{other.card_id} — {other.title or '(無標題)'}" for other in others]
    lines += [
        "- 只做自己的卡；明顯屬於別條的檔案不要動。",
        "- 每次編輯前都重新讀檔，不要用先前讀到的舊內容覆寫。",
        "- 修改要小而局部，共用檔案不要整份重寫；紀錄類檔案只能附加。",
        "- 被別條的修改弄壞而無法繼續時，回報 blocked 並寫原因。",
        "",
    ]
    return lines
