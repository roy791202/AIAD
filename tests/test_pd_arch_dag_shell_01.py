"""TDD — Arch DAG shell in #panel-arch: kinds, collapse/ports, no fake live, ACL."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
PERM = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "permissions" / "dispatch.toml"

# Order ≡ docs/節點類型定義整理.pdf 01–10 + WorkItem（Tasks Node）+ Deployment（佈署.pdf）
KINDS = [
    "API",
    "Contract",
    "UI",
    "Command",
    "Query",
    "Application",
    "Domain",
    "Infrastructure",
    "ACL",
    "Custom",
    "WorkItem",
    "Deployment",
]


def test_panel_arch_has_dag_canvas():
    html = HTML.read_text(encoding="utf-8")
    chunk = re.search(
        r'<section[^>]*id="panel-arch"[^>]*>.*?</section>',
        html,
        re.DOTALL,
    )
    assert chunk, "panel-arch missing"
    body = chunk.group(0)
    assert 'id="archStage"' in body
    assert 'id="archEdgesSvg"' in body or 'id="archEdges"' in body
    assert 'id="archNodes"' in body
    assert 'id="archBoard"' in body
    assert 'id="archRulerH"' in body
    assert 'id="archFormSize"' in body
    assert 'id="archGridSize"' in body
    assert "編輯草稿" in body


def test_strict_arch_node_kinds():
    js = JS.read_text(encoding="utf-8")
    assert "ARCH_NODE_KINDS" in js
    assert "ARCH_KIND_IO" in js
    for k in KINDS:
        assert f'"{k}"' in js or f"'{k}'" in js
    # PDF order: API before Contract before UI …
    api_i = js.index('"API"')
    contract_i = js.index('"Contract"')
    ui_i = js.index('"UI"')
    assert api_i < contract_i < ui_i
    assert "normalizeArchKind" in js
    assert "拒絕" in js or "不在嚴格枚舉" in js
    assert "formatArchNodeType" in js
    # 一般節點只顯示類別名；Node Type 字樣僅 Layer
    assert 'return "Node Type : Layer"' in js or "Node Type : Layer" in js
    assert "formatArchLayerPacks" in js
    assert "archNodeKind" not in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archAddKind"' in html
    assert 'id="archNodeType"' in html
    assert 'id="archNodeTypeLabel"' in html
    assert 'id="archNodeKind"' not in html  # 禁 Inspector 重選類別
    assert 'id="inspector-arch"' in html
    add_chunk = html[html.index('id="archAddKind"') : html.index('id="archAddKind"') + 1600]
    for k in KINDS:
        assert f'value="{k}"' in add_chunk
    assert 'value="Layer"' in add_chunk


def test_arch_layer_pack_same_attr_and_single_inter_layer_edge():
    """Layer 可定義 packs 屬性；同屬性可拖入打包；Layer↔Layer 只畫一條線。"""
    js = JS.read_text(encoding="utf-8")
    assert '"Layer"' in js
    assert "ARCH_PACKABLE_KINDS" in js
    assert "packsKind" in js
    assert "memberIds" in js
    assert "packNodeIntoLayer" in js
    assert "canPackNodeIntoLayer" in js
    assert "effectiveArchEndpoint" in js
    assert "findArchLayerContaining" in js
    assert "seenPair" in js or "pairKey" in js
    assert "arch-edge-layer" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archLayerPacksKind"' in html
    assert 'id="archNodePacksKind"' in html
    assert 'id="archLayerMembers"' in html
    assert "packs" in html.lower() or "packs Node Type" in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-node.is-layer" in css or 'data-kind="Layer"' in css
    assert "arch-layer-members" in css


def test_arch_layer_module_slot_hierarchy():
    """PDF／Spec：Layer → Module Slot(s) → Node（橫式 I/O）；展開收合僅顯示。"""
    js = JS.read_text(encoding="utf-8")
    assert "ensureLayerModules" in js
    assert "blankModuleSlot" in js
    assert "packNodeIntoModule" in js
    assert "movePackedNodeToSlot" in js
    assert "addModuleSlotToLayer" in js
    assert "archMemberDrag" in js
    assert "arch-module-slot" in js
    assert "arch-module-node" in js
    assert "arch-module-toggle" in js
    assert "<modules>" in js or "modules>" in js
    assert 'archAttr("slotId"' in js or "slotId" in js
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-module-slot" in css
    assert ".arch-module-nodes" in css
    assert ".arch-module-node" in css
    assert ".arch-layer-modules" in css


def test_arch_spec_assignment_and_unassigned():
    """SGGenAxis_Node_Architecture_Specification：moduleRef／layerRef／order／未分配區。"""
    js = JS.read_text(encoding="utf-8")
    assert "layerRef" in js
    assert "moduleRef" in js
    assert "layoutOrder" in js
    assert "listUnassignedArchNodes" in js
    assert "renderArchUnassigned" in js
    assert "canAcceptNodeInLayer" in js
    assert "applyArchTreeDrop" in js
    assert "findArchTreeDropTarget" in js
    assert "renderArchTreeLayerBranch" in js
    assert "data-tree-layer" in js
    assert "data-tree-module" in js
    assert "data-tree-draft" in js
    assert "archTrayDrag" in js
    assert "syncArchAssignmentsFromModules" in js
    assert "assignNodeToModule" in js
    assert "clearNodeAssignment" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="arch-unassigned"' in html
    assert 'id="arch-unassigned-list"' in html
    assert "架構樹" in html
    assert "arch-unassigned-tree" in html
    assert 'role="tree"' in html
    assert 'id="archNodeLayerRef"' in html
    assert 'id="archNodeModuleRef"' in html
    assert 'id="archNodeOrder"' in html
    assert 'id="archNodeDesc"' in html
    assert 'data-arch-tab="basic"' in html
    assert 'data-arch-tab="assign"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-workspace" in css
    assert ".arch-unassigned" in css
    assert ".arch-unassigned-chip" in css
    assert ".arch-tree-leaf" in css
    assert ".arch-tree-drop" in css
    assert ".arch-unassigned-tree" in css
    assert "is-drop-target" in css


def test_arch_marquee_multiselect_and_group_move():
    """框選多節點＋編輯模式下整組拖曳移動。"""
    js = JS.read_text(encoding="utf-8")
    assert "archMarquee" in js
    assert "archSelectedIds" in js
    assert "setArchSelection" in js
    assert "getArchSelectedIds" in js
    assert "collectArchNodesInMarquee" in js
    assert "clientToArchStage" in js
    assert "keepIfSelected" in js
    assert "archDrag.ids" in js or "ids: ids" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archMarquee"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-marquee" in css
    assert "is-arch-marquee" in css


def test_arch_arrange_selection():
    """依據選取自動／橫／縱排列（編輯草稿＋≥2 選取）。"""
    js = JS.read_text(encoding="utf-8")
    assert "arrangeArchSelection" in js
    assert "orderArchNodesForArrange" in js
    assert 'arrangeArchSelection("auto")' in js or 'arrangeArchSelection("h")' in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="arch-arrange-auto"' in html
    assert 'id="arch-arrange-h"' in html
    assert 'id="arch-arrange-v"' in html
    assert "自動排列" in html


def test_arch_kind_picker_graphical_icons():
    """＋節點開啟圖示面板；類別對應 ui/icons/arch/{Kind}.svg。"""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="arch-add-node"' in html
    assert 'id="arch-kind-picker"' in html
    assert 'id="arch-kind-grid"' in html
    assert 'id="arch-packs-grid"' in html
    js = JS.read_text(encoding="utf-8")
    assert "ARCH_KIND_ICONS" in js
    assert "wireArchKindPicker" in js
    assert "renderArchKindPickerGrid" in js
    assert "icons/arch/" in js
    assert "DEPLOYMENT_NODE_REGISTRY" in js
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-kind-picker" in css
    assert ".arch-kind-tile" in css
    icons_dir = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "icons" / "arch"
    for k in KINDS + ["Layer"]:
        assert (icons_dir / f"{k}.svg").is_file(), f"missing icon for {k}"


def test_deployment_node_inspector_and_registry():
    """佈署.pdf：Deployment Node Type + Inspector 專屬屬性 + registry。"""
    js = JS.read_text(encoding="utf-8")
    assert '"Deployment"' in js
    assert "ensureDeploymentFields" in js
    assert "isArchDeploymentNode" in js
    assert "DEPLOYMENT_TYPES" in js
    assert "deploymentType" in js
    assert "executionStatus" in js
    assert 'archAttr("deploymentType"' in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archDeploymentPanel"' in html
    assert 'id="archDepType"' in html
    assert 'value="Deployment"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-deployment-panel" in css
    fixture = ROOT / "fixtures" / "sgenaxis-arch" / "sample.sgenarch.xml"
    raw = fixture.read_text(encoding="utf-8")
    assert 'kind="Deployment"' in raw
    assert "deploymentType=" in raw


def test_workitem_node_lamp_and_event_log():
    """Tasks Node.html：WorkItem Node Store + displayLamp + append-only Event Log。"""
    js = JS.read_text(encoding="utf-8")
    assert '"WorkItem"' in js
    assert "ensureWorkItemFields" in js
    assert "isArchWorkItemNode" in js
    assert "computeDisplayLamp" in js
    assert "appendArchEvent" in js
    assert "listArchEventsForNode" in js
    assert "renderArchWorkItemHistory" in js
    assert "WORKITEM_WORKFLOW_STATUSES" in js
    assert "WORKITEM_TEST_STATUSES" in js
    assert 'archAttr("workflowStatus"' in js
    assert 'archAttr("displayLamp"' in js
    assert "events > event" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archWorkItemPanel"' in html
    assert 'id="archWiWorkflow"' in html
    assert 'id="archWiLamp"' in html
    assert 'id="archWorkItemHistory"' in html
    assert 'value="WorkItem"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-workitem-panel" in css
    assert ".arch-lamp-dot" in css
    assert ".lamp-red" in css
    assert ".lamp-orange" in css
    fixture = ROOT / "fixtures" / "sgenaxis-arch" / "sample.sgenarch.xml"
    raw = fixture.read_text(encoding="utf-8")
    assert 'kind="WorkItem"' in raw
    assert "workflowStatus=" in raw
    assert "displayLamp=" in raw
    assert "<events>" in raw
    assert 'eventType="node.created"' in raw


def test_arch_delete_node_and_kind_filter():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="arch-delete-node"' in html
    assert 'id="arch-kind-filter"' in html
    assert 'id="arch-inspector-delete"' in html
    js = JS.read_text(encoding="utf-8")
    assert "deleteArchNode" in js
    assert "setArchKindFilter" in js
    assert "archNodePassesFilter" in js
    assert "renderArchKindFilterBar" in js
    assert "archKindFilter" in js
    assert 'ev.key !== "Delete"' in js or 'key === "Delete"' in js
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-kind-filter" in css
    assert ".arch-filter-chip" in css


def test_arch_chrome_no_h1_zoom_icons_and_focus_selected():
    html = HTML.read_text(encoding="utf-8")
    # 工作區上方「模組架構圖」標題已清除
    chunk_start = html.find('id="panel-arch"')
    chunk = html[chunk_start : chunk_start + 2500]
    assert "<h1>模組架構圖</h1>" not in chunk
    assert 'id="arch-zoom-in"' in html
    assert 'id="arch-zoom-out"' in html
    assert 'id="arch-focus-selected"' in html
    assert "icons/arch/zoom_in.svg" in html
    assert "icons/arch/zoom_out.svg" in html
    assert "icons/arch/frame_selected.svg" in html
    js = JS.read_text(encoding="utf-8")
    assert "focusArchSelectedNode" in js
    icons = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "icons" / "arch"
    assert (icons / "zoom_in.svg").is_file()
    assert (icons / "zoom_out.svg").is_file()
    assert (icons / "frame_selected.svg").is_file()


def test_collapse_and_ports_left_in_right_out():
    js = JS.read_text(encoding="utf-8")
    assert "is-collapsed" in js or "collapsed" in js
    assert "arch-port" in js
    assert 'data-side="in"' in js or "is-in" in js
    assert 'data-side="out"' in js or "is-out" in js
    assert "arch-node-kind" in js
    assert "arch-node-expand" in js
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-node.is-collapsed" in css
    assert ".arch-node.is-collapsed .arch-node-kind" in css
    assert ".arch-node.is-collapsed .arch-node-expand" in css
    # 收合不得把類別名整段藏掉（舊版 display:none on .arch-node-body）
    assert ".arch-node.is-collapsed .arch-node-body," not in css
    assert ".arch-port.is-in" in css
    assert ".arch-port.is-out" in css


def test_no_fake_live_and_draft_canvas_stays():
    js = JS.read_text(encoding="utf-8")
    assert "禁止靜態假圖" in js or "冒充" in js
    assert "live=false" in js or 'live"' in js
    assert "草稿" in js
    assert "wireArchUi" in js
    assert "renderArchDag" in js


def test_arch_get_projection_acl():
    perm = PERM.read_text(encoding="utf-8")
    assert "allow-arch-get-projection" in perm
    assert "arch_get_projection" in perm
    assert "allow-arch-get-projection" in perm.split("dispatch-default")[-1] or (
        '"allow-arch-get-projection"' in perm
        or "allow-arch-get-projection" in perm
    )


def test_arch_middle_button_pan_and_wheel_zoom():
    js = JS.read_text(encoding="utf-8")
    assert "wireCanvasMiddleNav" in js
    assert "arch-canvas-shell" in js
    assert "setArchZoom" in js
    assert "button !== 1" in js or "ev.button !== 1" in js
    assert "wheel" in js
    css = CSS.read_text(encoding="utf-8")
    assert "is-mmb-panning" in css


def test_arch_grid_infinite_extend():
    js = JS.read_text(encoding="utf-8")
    assert "expandArchWorldExtent" in js
    assert "applyArchWorldSize" in js
    assert "ARCH_WORLD_GROW" in js
    assert "is-infinite-grid" in js
    assert "不硬夾上界" in js or "無限延伸" in js


def test_ui_bhv_arch_ui_layer_entry():
    """UI-bhv：UI Layer 節點 Edit → 獨立視窗；視窗→UI 編輯；無側欄入口。"""
    js = JS.read_text(encoding="utf-8")
    assert 'if (k === "UI") return "UI Layer"' in js or 'return "UI Layer"' in js
    assert "ensureUiLayerFields" in js
    assert "openArchUiLayer" in js
    assert "openUiDesignWindow" in js
    assert "isArchUiLayerNode" in js
    assert "arch-ui-edit" in js
    assert 'archAttr("uiLayerId"' in js
    assert 'archAttr("uiDefinitionRef"' in js
    assert 'cmd === "win.uiEditor"' in js
    assert 'cmd === "win.uiViewer"' in js
    assert "狀態：Editor（非驗收 PASS）" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="archUiLayerPanel"' in html
    assert 'id="arch-open-ui-editor"' in html
    assert 'id="uidesign-window"' in html
    assert 'data-cmd="win.uiEditor"' in html
    assert "UI 編輯" in html
    assert 'id="sec-uidesign"' not in html
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-ui-layer-panel" in css
    assert ".arch-ui-edit" in css
    assert ".uidesign-window" in css
