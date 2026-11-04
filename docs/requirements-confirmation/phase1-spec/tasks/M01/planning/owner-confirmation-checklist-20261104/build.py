import json, hashlib, shutil, html, subprocess
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('D:/AIAD'); OUT=Path(__file__).resolve().parent
BASE='docs/requirements-confirmation/phase1-spec/tasks/'
sources={}
def read(path):
    p=ROOT/path; raw=p.read_bytes(); sources[path]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
def bind(path,pointer=''):
    obj=read(path)
    for key in pointer.strip('/').split('/') if pointer else []: obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return dict(path=path,sha256=sources[path],pointer=pointer,value=obj)
register_path=BASE+'M01/planning/exact-disposition-correction-20261103/register.json'
r=read(register_path); cards=r['cards'][:8]
for path in ['M01/planning/exact-disposition-correction-review-20261103/results.json','M01/planning/current-action-blockers-review-20261103/correction-results.json','M02/planning/golden14-lock-review-20261103/results.json','M03/planning/media-fixture-provenance-review-20261103/results.json']:
    read(BASE+path)
for i in range(1,5): read(BASE+f'decisions/G0{i}/decision-request.json')
items=[]
LIMIT=['不批准產品實作或新 Port/schema/Skeleton','不證明有效 RED、原生能力或獨立驗收','不改卡色/Done、不 commit/push/release']
def item(id,title,kind,module,question,options,recommend,refs,gate='只解鎖受影響規劃修訂；仍須 Skeleton、有效 RED 與獨立驗收',priority='P0'):
    items.append(dict(id=id,title=title,kind=kind,priority=priority,module=module,selected=None,question=question,options=options,recommendation=recommend,exact_candidates=refs,unlock=gate,cannot_authorize=LIMIT))
def candidate_objects(card):
    fs=card.get('exact_pending',{}).get('fields',[]); result=[]
    for f in fs:
        s=f['source']
        if s['pointer'].endswith('/id'):
            result.append(bind(s['path'],s['pointer'].rsplit('/',1)[0]))
    return result
def options_accept(): return ['逐項接受下列精確 candidate（各子項獨立勾選）','退回指定子項並寫替代語意','延後指定子項並寫原因']
item('SUP-IO-01','Win11 原生測試環境','供料/環境','IO → 全模組','由誰提供 Windows 11 x64 隔離環境與 reparse / 8.3 原生 fixtures？',['提供現有隔離機／VM 與窗口','安排工程角色建立可重現環境','暫無環境，維持 NOT RUN'],'建議安排工程角色建立；Owner 只指定窗口與可用時段，不需重採納既有 IO 設計。',[bind(register_path,'/cards/0')], '只解鎖獨立驗證者執行剩餘 native matrix；不新增 Owner adoption')
item('DEC-M01-01','副本 Ready：發布格式與證據責任','決策','M01 / F01','CR-D1 原生 lease、CR-D2 重啟後 Ready 證據、CR-D3 完整發布表示：哪些精確提案接受、退回或延後？',options_accept(),'建議先由工程角色補 CR-D1/2 真實 provider/schema/lifecycle 對照再逐項確認；CR-D3 必須看完整形狀與 migration，不能把文件 PASS 當批准。',candidate_objects(cards[1]))
item('DEC-M02-01','生成啟用中遇到來源變更','決策','M02 / F02–F03','鎖住來源時，來源更新要立即回 Busy，還是延後？請同時逐項處置 AF-OWNER-2 欄位映射及 AF-OWNER-3 不確定結果提案。',['Busy：本次不修改、使用者明確重試','Defer：本次不修改、待明確解除保留後再操作','先補使用者流程再選（AF-OWNER-2/3 可另行處置）'],'建議 Busy，避免未定義排程與自動重試；這是建議，沒有替 Owner 選。AF-OWNER-3 建議保留人工核對且不自動重試。',candidate_objects(cards[2]))
gold=cards[2]['golden14_provider_inputs']
item('SUP-M02-01','Golden14 實際模板與獨立工具鏈','供料/環境','M02 / F02–F03','14 個檔案的正式內容由誰提供與確認？',['工程角色提出每檔候選 → Owner 看輸出 → 獨立 reviewer 鎖定','Owner 提供既有正式模板與授權來源 → 工程角色製作證據','延後，維持 Golden14 未入場'],'建議第一種；不請 Owner 手寫 hash/schema，也不由本清單自選模板內容。',[bind(BASE+'M02/planning/golden14-lock-inventory-20261103/candidate.json','/rows')], '實際 bytes、輸入版本、預期輸出與獨立 lock tuple 審查後才可進 Golden admission')
items[-1]['golden14']=gold
items[-1]['common_missing']=['每檔實際 candidate bytes + SHA256','definition/design/input revisions','expected rendered output bytes + output hash','standalone manifest + Cargo.lock','resolver + toolchain versions','source/provider/provenance + 獨立 fixture review']
media=cards[3]['media_decisions']
item('DEC-M03-01','預覽支援能力：八維度分別決定','決策','M03 / F04','是否先做 renderer/decoder 能力調查，再逐維選擇精確支援子集？',['先調查能力與安全/限制，再逐維決定','現在逐維提供精確支援範圍，交工程角色驗證','明確排除或延後指定維度並註明原因'],'建議先做能力調查；八項全部 selected=null，PNG/JPEG、SVG、動畫、影音格式及限制均未代選。',[bind(m['source']['path'],m['source']['pointer']) for m in media], '只解鎖能力調查與精確支援提案；不解鎖 decoding/runtime/renderer 實作')
items[-1]['dimensions']=media
item('DEC-M04-01','儲存後 Held／檔案／root／ACK 的先後與回報','決策','M04 / F05、F10','請逐項確認 G1 capture、G2 Held證據、G3錯誤觀察、G4 ACK順序；哪些需修改？',options_accept(),'建議保留「證據缺失不推斷已釋放」與 root 成功後才 ACK；wire mapping 未決由工程角色補，不能一次批准整個 codec。',candidate_objects(cards[4]),priority='P1')
item('DEC-M05-01','保留資料：收據與不確定 CAS 如何核對','決策','M05 / F06','請逐項確認 H1–H4 的 request/proof/response/reconciliation 映射；無法證明提交時是否維持需人工核對？',options_accept(),'建議不自動重試、ACK 或釋放；真實 issuer/fence/inclusion 證據由工程角色準備。',candidate_objects(cards[5]),priority='P1')
mh=candidate_objects(cards[6])
item('DEC-M06-01','合併與 Undo 的責任橋接','決策','M06 / F07–F09','MH1–MH4、MH6 各提案是否符合預期？重點是一次 M04 commit、獨立 Undo context 與完整引用重寫。',options_accept(),'建議逐項審查，先補真實 mutation issuer、三種 root 註冊/fence、Undo-purpose Held 與 ESS projector；fixture 不是原生證據。',[x for x in mh if x['value']['id']!='MH5'],priority='P1')
item('DEC-M06-02','BDD-19：失敗完整回復，或明確新增提交後待修復狀態？','決策','M06 / F09','合併已提交但 root/retention 後續失敗時，是否仍要求完整回復原狀？',['保留 BDD-19 完整回復：所有屬失敗的結果完整恢復目標；重新規劃可證明的原子/補償 seam','明確 BEHAVIOR_CHANGE：提交後保留新 revision＋舊 Held/pins，回報 deferred retention；修訂 BDD/契約後重走 RED','暫緩此語意，維持受影響 slice REPLAN_REQUIRED'],'建議先保留完整回復，要求工程角色評估可行 seam；若產品接受提交後待修復，必須明確選第二項，不能悄悄縮成只回復文件內容。',[x for x in mh if x['value']['id']=='MH5']+[bind(BASE+'M06/planning/gap-matrix.json','/bdd_owned/10')],priority='P0')
ra=candidate_objects(cards[7])
item('DEC-M07-01','Recovery ACK 使用獨立協定，或正式版本化聯集？','決策','M07 / F11–F12','請在已有 RA-O1 / RA-O2 候選中選擇 recovery ACK 協定方向。',['RA-O1：獨立 protocol/ack-recovery role/body/receipt 與 atomic owner mutation','RA-O2：明確版本化 formal/recovery discriminated union，連同 role/hash migration 與相容分析','先由工程角色補完整方案比較，再決定'],'建議 RA-O1 可保持 formal-save 與 recovery 權限區隔；仍需具體 schema、replay/baseline 原子性與重啟證據。',[x for x in ra if x['value']['id'] in ['RA-O1','RA-O2']])
item('DEC-M07-02','Recovery operation ordinal 的既有兩個方向','決策','M07 / F11–F12','ordinal 要使用明定公式，或新 schema 固定字串 0？目前 illustrative /0 不是已批准公式。',['RA-C-O1：先提出可入場的 ordinal operation 公式再確認','RA-C-O2：明確 schema revision，固定 ordinal 字串 0','延後並要求工程角色補 replay/collision/baseline 範例'],'建議先補公式及 collision/replay 範例再決定；不把 illustrative /0 當 exact formula。',[x for x in ra if x['value']['id'] in ['RA-C-O1','RA-C-O2']])
item('SUP-CROSS-01','原生 provider 與精確 envelope：交工程角色準備','供料/環境','M01–M07 / F01–F12','各模組真實 issuer/fence/root/codec/ESS 與檔案範圍證據，是否按原 scope 交對應工程角色補齊？',['按原 scope 列 provider 對照與缺口，回來只問產品語意','提供已存在 provider 的位置與負責窗口','缺 provider，記 IMPLEMENTATION_BLOCKED 並保留已通過歷史'],'建議第一項；技術 hash、schema、request tuple、manifest 由工程角色產出，Owner 不需手填。',[bind(register_path,'/cards/'+str(i)+'/missing_conditions') for i in range(1,8)],'只解鎖原 scope 文件準備；精確 envelope＋可編譯 intended RED＋獨立接受前不啟動產品實作',priority='P1')
adopted=[]
for i,c in enumerate(cards[1:],1):
    a=c.get('exact_adopted',{})
    adopted.append(dict(module=f'M0{i}',meaning='已確認不再詢問：保留 current-state、既有 adoption 與歷史 PASS；缺 ledger 不等於歷史被否定。',facts=a,source=bind(register_path,f'/cards/{i}/exact_adopted')))
data=dict(author='/root/owner_checklist_author',status='DRAFT_FOR_INDEPENDENT_DOCUMENT_REVIEW',selected=None,generated_at=datetime.now(timezone.utc).isoformat(),live_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),historical_head=r['historical_head'],authority_count=796,authority=r['authority'],scope='八黃卡的 Owner 決策與供料確認；原 scope 可準備工作繼續；不覆寫歷史採納',items=items,already_confirmed=adopted,already_confirmed_summary='D1–D7、M02 DX1–DX7 與各 slice 既有採納不重新詢問；所有既有 PASS 維持原證據層級。',related_decision_packets=[bind(BASE+f'decisions/G0{i}/decision-request.json') for i in range(1,5)],limits=LIMIT,verification='作者自檢僅文件投影；產品/原生/build/package/RED/GREEN/驗收 NOT RUN')
def dump(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
dump(OUT/'checklist.json',data)
def esc(s): return html.escape(str(s))
def ref(x):
    relative=Path(__import__('os').path.relpath(ROOT/x['path'],OUT)).as_posix()
    return f'<details><summary><a href="{esc(relative)}">證據 {esc(x["path"].split("/")[-2])}</a> · {esc(x["pointer"])}</summary><p>SHA256 <code>{x["sha256"]}</code></p><pre>{esc(json.dumps(x["value"],ensure_ascii=False,indent=2))}</pre></details>'
sections=[]
for x in items:
    opts=''.join(f'<label><input type="radio" name="{x["id"]}" value="{i}">{esc(o)}</label>' for i,o in enumerate(x['options']))
    detail=''.join(ref(t) for t in x['exact_candidates'])
    extra=''
    if 'golden14' in x: extra='<p>14 個檔案（每列仍缺共同證據）：</p><ol>'+''.join('<li><code>'+esc(g['path'])+'</code></li>' for g in gold)+'</ol><p>'+esc('；'.join(x['common_missing']))+'</p>'
    if 'dimensions' in x: extra=''.join('<details><summary>□ '+esc(m['id']+' '+m['dimension'])+' — 未決</summary><p>'+esc(m['question'])+'</p><p>需供料：'+esc(m['fixture_input_required'])+'</p><p>選項：精確子集／明確排除／附理由延後。目前 null。</p></details>' for m in media)
    sections.append(f'<article id="{x["id"]}"><small>{x["priority"]} · {x["kind"]} · {x["module"]}</small><h3>□ {x["id"]} {esc(x["title"])}</h3><p>{esc(x["question"])}</p>{opts}<p class="rec">{esc(x["recommendation"])}</p><p>可解鎖：{esc(x["unlock"])}</p>{extra}<details><summary>精確 candidate：hash / pointer / 原值（逐子項確認，沒有整包採納）</summary>{detail}</details><label>指定子項、替代值／原因／窗口：<textarea></textarea></label></article>')
body='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>八黃卡｜Owner 逐項確認</title><style>body{font:16px/1.65 system-ui;background:#f4f5f8;color:#192b3b;max-width:1100px;margin:32px auto;padding:20px}article,header,section{background:white;padding:24px;margin:18px 0;border:1px solid #d7dee5;border-radius:12px}label{display:block;margin:10px 0}input{margin-right:9px}textarea{display:block;width:95%;height:65px}small{color:#626d79}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:12px;font-size:13px}code{overflow-wrap:anywhere}.rec{border-left:4px solid #4487a5;padding-left:12px}summary{cursor:pointer}a{color:#216b97}</style><header><h1>八黃卡：請決定什麼、請誰提供什麼</h1><p>先處理 P0，再處理 P1。每題可單獨回答「ID＋選項＋指定子項」。所有選項預設未選；勾選只作離線筆記，不會寫入採納 ledger、board 或產品。</p><p><b>已確認不再詢問：</b>D1–D7、M02 DX1–DX7、各 slice 既有採納與歷史 PASS。不因缺 adoption ledger 否定歷史。</p><p>本頁只做決策與供料導航；原 scope 的文件/證據準備繼續。產品實作仍需精確 envelope、Skeleton、有效 RED 及獨立驗收。</p></header>'''+''.join(sections)+f'<section><h2>既有採納／來源與邊界</h2><p>live HEAD {data["live_head"]}；歷史 inventory HEAD {data["historical_head"]}；796 來源權威。來源 cache 與 hash 可由 <a href="source-hashes.json">source-hashes.json</a> 核對。</p><p>G01–G04 集中包只作相關證據入口；本頁不再要求整包採納。<a href="checklist.json">完整機器資料</a>（包含各模組已確認記錄及 G01–G04 精確對照）。</p><p>{esc(data["verification"])}。不得據此批准產品、變更 schema/Port/Skeleton、改卡色或 commit/push/release。</p></section><script type="application/json" id="checklist-data">'+json.dumps(data,ensure_ascii=False).replace('</','<\/')+'</script></html>'
(OUT/'index.html').write_text(body,encoding='utf8')
cache=OUT/'sources'; cache.mkdir(exist_ok=True)
for n,(p,digest) in enumerate(sorted(sources.items())):
    shutil.copyfile(ROOT/p,cache/f'{n:03d}-{Path(p).name}')
dump(OUT/'source-hashes.json',[dict(path=p,sha256=h,cache=f'sources/{n:03d}-{Path(p).name}') for n,(p,h) in enumerate(sorted(sources.items()))])
dump(OUT/'seal.json',dict(author='/root/owner_checklist_author',status='AUTHOR_FROZEN_PENDING_INDEPENDENT_REVIEW',files={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='seal.json'},independent_acceptance='NOT RUN',product_tests_build_native_package='NOT RUN'))
