"""Five-light board surface contract; backend tests prove persistence rules."""
from pathlib import Path
import re

BOARD = Path(__file__).resolve().parents[1] / "docs" / "PROJECT-BOARD.html"

def shell():
    text = BOARD.read_text(encoding="utf-8")
    return re.sub(r'(<script type="application/json" id="board-snapshot">).*?(</script>)', r'\1{}\2', text, flags=re.S)

def test_exactly_five_task_light_tabs_and_panels():
    text = shell()
    zones = {"gray", "yellow", "red", "orange", "green"}
    tabs = set(re.findall(r'id="tab-(gray|yellow|red|orange|green)"', text))
    panels = set(re.findall(r'id="zone-(gray|yellow|red|orange|green)"', text))
    assert tabs == panels == zones
    assert "橘燈・待決策" in text

def test_orange_has_required_short_decision_form_and_searchable_card_summary():
    text = shell()
    assert "f-decision-" in text
    assert "decision.required = z === 'orange'" in text
    assert "decision.maxLength = 200" in text
    assert "editable(task, 'decision', '待決策內容')" in text
    assert "t.note, t.decision, t.ref" in text

def test_orange_is_counted_and_zone_update_carries_decision_together():
    text = shell()
    assert "id=\"nOrange\"" in text
    assert "counts.orange" in text
    assert "orange: 0" in text
    assert "'decision'" in text
    assert "if ('zone' in data) fields.zone = data.zone" in text
    assert "data-view=\"orange\"" in text

def test_owner_action_has_confirmation_dialog_and_versioned_request():
    text = shell()
    assert 'id="ownerActionDialog"' in text
    assert "Owner 批准／指示" in text
    assert "'/owner-action'" in text
    assert "expected_version: task.version" in text
    assert "ownerActions" in text
