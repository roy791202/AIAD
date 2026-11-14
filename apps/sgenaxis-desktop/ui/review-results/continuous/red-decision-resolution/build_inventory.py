"""Bind prewritten administrative conclusions to the already fetched API snapshot."""
import hashlib
import json
from pathlib import Path
b=Path(__file__).resolve().parent
root=b.parents[3]
snapshot=b/'api-tasks-snapshot.json'
tasks=json.loads(snapshot.read_text(encoding='utf-8'))['tasks']
by_id={x['id']:x for x in tasks}
old=json.loads((root/'reports/dispatch-pd/MCP-DECISION-REVIEW-SUMMARY.json').read_text(encoding='utf-8'))
old_by={x['id']:x for x in old['cards']}
rows=[]
def add(id,kind,block,down,missing,question,resolution,proposal,approval=None):
    task=by_id[id]
    rows.append({'id':id,'classification':kind,'actual_block':block,'downstream':down,'missing':missing,'minimal_question':question,'resolution':resolution,'proposal':proposal,'approval_evidence':approval or [],'api_observed_zone':task['zone'],'api_card_updated_at':task.get('updatedAt'),'api_card_version':task.get('version'),'api_note_sha256':hashlib.sha256(task.get('note','').encode('utf-8')).hexdigest()})
def notes(id,term): return [x for x in by_id[id].get('note','').splitlines() if term in x]

add('PD-RUST-PROC-INTEGRATION-DEC-01','已明確批准／行政核正','否：PM 轉紅未撤回原 owner 批准。',
 ['PD-RUST-PROC-IMPL-01','PD-RUST-PROC-TDD-01','PD-RUST-PROC-REVIEW-01'],[],
 '無須重問相同整合。Parent 記錄原批准仍有效；是否改燈色依 PM 流程處理，不代表重新批准或自升綠。',
 '00:44:20 owner 明確核准必要整合，範圍含 HOST 不吞事件、UI 空 poll 與 cancel 持續輪詢、七既有檔。01:51:22 PM gray→red 只是流程移區；未見 owner 撤銷。已完成的獨立證據不應被此色彩變更抹除。',
 'reports/rust-improvements/continuous/process-lifecycle/module.html',notes('PD-RUST-PROC-INTEGRATION-DEC-01','OWNER APPROVED')+notes('PD-RUST-PROC-INTEGRATION-DEC-01','PM: gray decision'))
add('PD-RUST-EXEC-DEC-01','舊總卡／行政拆卡收斂','不獨立阻塞已批准的 MCP NOT RUN、FS、PROC；Guard／真 transport 由各專卡阻塞。',
 ['PD-RUST-GUARD-DEC-01','PD-RUST-MCP-TRANSPORT-DEC-01'],[],
 '無新架構選擇；parent 可註記「已拆卡導航」，只保留子卡未決事項，不重問既有 FS／PROC 核准。',
 '總卡舊文字仍說 process/filesystem 未核准，與專卡記錄不符。建議行政標示 superseded/navigation-only，保留歷史；不授予 Guard 或 transport 新權限。',
 'reports/rust-improvements/architecture-review/module.html',
 notes('PD-RUST-FS-DEC-01','OWNER APPROVED')+notes('PD-RUST-PROC-DEC-01','OWNER APPROVED')+['MCP NOT RUN 授權是限定 unavailable slice；真實 transport 仍未核准，不能用總卡替代。'])
add('PD-RUST-DISPATCH-MODES-DEC-01','真正路線選擇；真 provider 另缺 target','是：首片範圍需選；只做 benign fixture 不等於真 Agent 放行。',
 ['PD-RUST-CLI-ENTRY-IMPL-01','PD-RUST-INBOUND-MCP-IMPL-01','PD-RUST-CLAUDE-COMPAT-01','PD-RUST-CODEX-COMPAT-01'],
 ['首片 benign fixture executable/argv/input/cwd 範圍尚未核准','真 Claude Code/Codex 各自 version/path/argv/auth-ready/目標未提供'],
 '是否只先核准現有 HOST/EXEC 的非互動 benign fixture envelope？真 Claude／Codex 安裝與 argv 等逐項提供後各別核准，入站／內嵌不包含。',
 '使用者確認 CLI、入站與兩種內嵌需求，及 Claude Code/Codex 相容目標；未見選定這個首片骨架的明確批准。已完成 cli-first 具體方案，不需再重寫平台。',
 'reports/rust-improvements/continuous/cli-first-envelope/module.html',
 ['使用者原話「cluad code 也要可以」及「另一種是像 VS code 可內坎這些Agent」：需求納入，非入口/骨架批准；此處無可核實精確訊息時間。']+notes('PD-RUST-DISPATCH-MODES-DEC-01','[2026-10-25T23:13:34')+notes('PD-RUST-DISPATCH-MODES-DEC-01','[2026-10-25T23:14:47'))
add('PD-RUST-GUARD-DEC-01','需 owner 選擇＋缺可信 provenance／capability','是：approve A 也不能直接宣告 READY。',
 ['PD-RUST-GUARD-IMPL-01','PD-RUST-GUARD-TDD-01','PD-RUST-XML-READINESS-01'],
 ['local trust boundary 與 one-shot/revoke 語義未核准','可信 current fingerprint 與 qualified RED producer 尚未指定','native confirmation/caller 工具權限分離尚未實證'],
 '是否選 session-only／受限 owner confirmation／one-shot 方案，並指定可信 fingerprint 與 RED producer？能力分離證據齊備後才另核准 Skeleton。',
 '既有 Guard 只核對 caller DTO，authorize(name) 沒有 actor；補充報告已提供 matrix/comparator。通用「持續派工」或選 A 不能補出尚不存在的信任來源。',
 'reports/rust-improvements/continuous/guard-authority-planning/module.html')
add('PD-RUST-DOCUMENT-DEC-01','真正文件契約選擇；既有 .ess A 授權狹窄','是：新增相容性／editable schema 或 migration 不能沿用 readonly A 放行。',
 ['PD-RUST-UI-OWNERSHIP-DEC-01','PD-RUST-UI-OWNERSHIP-IMPL-01','PD-RUST-UI-BEHAVIOR-LOOP-01','PD-RUST-XML-READINESS-01'],
 ['現況 characterization-only 與改 schema/migration 範圍尚待選擇'],
 '是否選保留各格式、不改 schema／不 migration，只先鎖實際 codec 相容性與 characterization 測試？',
 '原 .ess 唯讀封包批准仍有效，但不覆蓋 split 輸入、可編輯格式、未知欄位保真或多檔 transaction。當前產品契約報告已完成，剩下的是範圍選擇。',
 'reports/rust-improvements/continuous/product-documents/module.html',
 ['使用者原話「核准 A：先做 .ess 唯讀封包」：只覆蓋已交付 readonly A。']+notes('PD-RUST-XML-PACKET-DEC-01','OWNER APPROVED'))
add('PD-RUST-UI-OWNERSHIP-DEC-01','真正歸屬表示與權威來源選擇','是：不可憑 hints/文件名推導 ownership 或 READY。',
 ['PD-RUST-UI-OWNERSHIP-IMPL-01','PD-RUST-UI-BEHAVIOR-LOOP-01','PD-RUST-XML-READINESS-01'],
 ['explicit mapping input 或產品 schema 版本化選擇未核准','實際 document-ref/moduleId/design-node-ID 清單未指定'],
 '是否先選明確唯讀 mapping input，原產品檔不改、缺漏／衝突仍 NOT_READY？若要寫回產品檔則另選 schema 版本化方案。',
 '既有決策報告已列最小 A 與替代 B；尚無具體批准。UI 模組歸屬缺資料不是 parser code FAIL，不能用自動猜測關卡。',
 'reports/dispatch-pd/PD-RUST-UI-OWNERSHIP-DEC-01-TDD-REVIEW.md')
add('PD-RUST-MCP-TRANSPORT-DEC-01','需 transport 選擇＋缺實際 server/tool target','是：實際實作／smoke 被未選契約與目標阻塞；不是現有 code FAIL。',
 ['PD-RUST-MCP-TRANSPORT-IMPL-01','PD-RUST-MCP-TRANSPORT-SMOKE-01'],
 ['stdio 或明確 loopback HTTP 未核准','server executable/argv 或明確 endpoint/tool 未指定','初始化/呼叫/取消/關閉上限仍只是原提案值'],
 '首片是否選 local stdio？請指定 server executable/argv/tool 並確認原提案 timeout/cancel 政策；未指定前不得探測未知端點。',
 'NOT RUN 修正只讓未接 transport 誠實失敗，不代表已有 MCP transport。缺 target 應標準確 NOT_READY／NOT RUN；:8787/:8788／空目標禁用維持。',
 'reports/dispatch-pd/PD-RUST-MCP-TRANSPORT-DEC-01-TDD-REVIEW.md')
add('PD-RUST-EMBEDDED-AGENT-DEC-01','真正 interactive 模式／session 範圍選擇','是：選 PTY/native panel 與具體 seam 前不得實作。',
 ['PD-RUST-EMBEDDED-AGENT-IMPL-01'],
 ['PTY benign fixture feasibility 或 native provider panel 尚待選擇','interactive session 生命週期／權限模式未核准'],
 '是否先選 PTY benign fixture 可行性（輸入/resize/interrupt/close、關閉即結束、不保存、不自動准權），真 Agent 接入另核准？',
 '使用者已確認像 IDE 內嵌 Agent 的產品需求，未批准 PTY 或 native session 架構。既有 ProcessPort stdin=null 不能被當作既有互動能力。',
 'reports/rust-improvements/embedded-agents/module.html',
 ['使用者原話「另一種是像 VS code 可內坎這些Agent」及後續「沒錯」：需求方向確認，非指定 PTY/native 方案批准。']+notes('PD-RUST-DISPATCH-MODES-DEC-01','[2026-10-25T23:14:47'))
add('PD-RUST-MCP-NOTRUN-ACCEPT-01','owner 驗收；不等同 commit 授權','不阻塞既有修正的技術完成；只阻塞 owner 驗收／另行提交選擇。',
 [],
 ['未找到 owner 明確接受本 MCP unavailable 交付的文字','本卡沒有 commit/push/release 新授權'],
 '是否驗收 bounded NOT RUN／無假成功／憑證不回顯？驗收與 commit 分開，本次不推論任何提交／push/release。',
 '先前 focused5 與技術 review PASS 已有新證據，這張是 acceptance decision 而非再造 RED 的實作卡。原 baseline/.ess commit 同意不能移用至 MCP slice。',
 'reports/dispatch-pd/PD-RUST-MCP-NOTRUN-ACCEPT-01-TDD-REVIEW.md')

red={x['id'] for x in tasks if x.get('zone')=='red' and x.get('kind')=='decision'}
assert {x['id'] for x in rows}==red, (red-{x['id'] for x in rows})
for row in rows:
    assert (root/row['proposal']).is_file(),row['proposal']
    row['proposal_sha256']=hashlib.sha256((root/row['proposal']).read_bytes()).hexdigest()
    row['downstream_current_status']={x:by_id[x]['zone'] for x in row['downstream'] if x in by_id}
    row['downstream_dependency_evidence']={x:[line for line in by_id[x].get('note','').splitlines() if 'Dependencies:' in line or '依賴:' in line] for x in row['downstream'] if x in by_id}
    row['direct_declared_downstream']=[x for x,lines in row['downstream_dependency_evidence'].items() if any(row['id'] in line for line in lines)]
    row['other_affected_or_indirect']=[x for x in row['downstream'] if x not in row['direct_declared_downstream']]
    if row['id']=='PD-RUST-DOCUMENT-DEC-01':
        row['not_blocked_by_this_decision']='PD-RUST-DOCUMENT-CONTRACT-01 is prior audit/upstream proposal, not blocked new implementation; do not retroactively mark its existing evidence blocked.'
    if row['id']=='PD-RUST-EMBEDDED-AGENT-DEC-01':
        row['not_blocked_by_this_decision']='PD-RUST-AGENT-HOSTED-UI-01 depends on DISPATCH-MODES-DEC + INBOUND-MCP, a distinct direction; not a direct dependency of this PTY/native choice.'
    if row['id']=='PD-RUST-MCP-NOTRUN-ACCEPT-01':
        row['related_delivery_not_new_blocker']='PD-RUST-MCP-NOTRUN-IMPL-01 is already delivered; ACCEPT does not block its technical completion or reopen implementation.'
s={'module':'red-decision-resolution','date':'2026-10-26 Asia/Taipei','status':'READ_ONLY_APPROVAL_RECONCILIATION','summary':'API 快照共9張 red decision：1張已批准行政核正、1張舊總卡行政拆卡、6張架構/範圍待選（其中 Guard缺provenance、MCP缺target、CLI真provider亦缺target）、1張owner驗收。卡色不是批准或撤銷本身。','decisions':rows,'administrative_actions_for_parent':['PROC-INTEGRATION 註明00:44:20批准仍有效，01:51:22 PM轉紅不構成撤銷；不再標等待同一架構批准。','EXEC總卡註明已拆卡導航；不可重複擋已核准FS/PROC/MCPNOTRUN，也不可藉總卡放行Guard/真transport。'],'still_human_choices':[x['id'] for x in rows if x['id'] not in ['PD-RUST-PROC-INTEGRATION-DEC-01','PD-RUST-EXEC-DEC-01']],'limits':'Snapshot-specific, not a live approval database. Owner quotes without timestamp are explicitly marked session quotes; board OWNER APPROVED timestamps are board-recorded times, not independently authenticated message timestamps. Existing approved plans are reused; no new architecture or approvals invented. No tests rerun/source/test/board writes/commit/push. Missing target/provenance is not executable TDD failure.','source_binding':{'api':'GET http://127.0.0.1:28789/api/tasks','snapshot':'api-tasks-snapshot.json','snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'task_count':len(tasks),'red_decision_count':len(red),'note':'Each card includes exact API note hash and updatedAt; sources/proposals may change after snapshot. Parent should apply administrative updates against current board.'}}
(b/'module.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Wrote all9 current-red decision resolutions; no board mutation.')
