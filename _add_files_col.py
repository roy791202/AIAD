from pathlib import Path
import re

path = Path(r"D:\AIAD\git_workbench_interactive.html")
text = path.read_text(encoding="utf-8")
files = {
    "TASK-G1": ["viewport/walkthrough.py"],
    "TASK-G2": ["scripts/package-portable.ps1"],
    "TASK-Y1": ["tools/test/runner.py"],
    "TASK-Y2": ["docs/spec/module-spec.md"],
    "TASK-01": ["regiove.eak", "presentation.diff"],
    "TASK-02": ["regiove.ppp"],
    "TASK-03": ["presentation"],
    "TASK-04": ["worker.pon"],
    "TASK-05": ["hetadel.jog"],
    "TASK-06": ["presentation.diff"],
    "TASK-08": ["worker.clif"],
    "TASK-07": ["regiove.eak", "docs/board/tasks.json"],
}

def repl(match):
    row = match.group(0)
    task_id = match.group(1)
    names = files.get(task_id)
    if not names or "col-files" in row:
        return row
    chips = "".join(f'<span class="file-name">{name}</span>' for name in names)
    cell = f'<td class="col-files">{chips}</td>\n              '
    return row.replace("<td class=\"col-bdd\">", cell + "<td class=\"col-bdd\">", 1)

updated, count = re.subn(
    r'<tr[^>]*data-id="(TASK-[^"]+)"[\s\S]*?</tr>',
    repl,
    text,
)
path.write_text(updated, encoding="utf-8")
print(count)
