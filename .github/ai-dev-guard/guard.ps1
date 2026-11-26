<#
 CI Guard（第 3 層強制）：GitHub Actions 在 pull_request 時執行。PowerShell 7（ubuntu-latest 內建 pwsh）。
 檢查：board.json 規則、PR 對應的 Task 卡片（In Review + TDD Green + 涵蓋情境 Green；有 board-closeout 標籤時改為
       結案檢查：只改看板、該卡 In Review→Done、藍燈、tdd/ci Green、prUrl、completedAt、其他卡不變）、
       .feature 修改需 spec-change 標籤、強制機制檔案（含 .github/ai-dev-guard/）需 guard-change 標籤、
       不可新增略過的測試、版本與 CHANGELOG（有佈署或版本變更時）。測試本身在 workflow 的 tests job 跑。
 環境變數：BOARD_PATH（預設 docs/board.json）、BASE_SHA、PR_TITLE、HEAD_REF、PR_LABELS（逗號分隔）
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'validate-board.ps1') -Library
$errs = [Collections.Generic.List[string]]::new(); $warns = [Collections.Generic.List[string]]::new()
$board = if ($env:BOARD_PATH) { $env:BOARD_PATH } else { 'docs/board.json' }
$base = $env:BASE_SHA; $title = "$env:PR_TITLE"; $ref = "$env:HEAD_REF"
$labels = @("$env:PR_LABELS" -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
function G([string[]]$a) { $o = & git @a 2>$null; if ($LASTEXITCODE -ne 0) { return $null }; return ($o -join "`n") }
function Note($m) { Write-Host "::error::$m"; $errs.Add($m) }

# 1) board.json
$d = $null
if (-not (Test-Path -LiteralPath $board)) { Note "找不到 $board（可用 BOARD_PATH 指定）" }
else {
  try { $d = Read-BoardJson ([IO.File]::ReadAllText($board)) } catch { Note "$board 無法解析：$($_.Exception.Message)" }
  if ($d) { foreach ($x in @(Test-Board $d)) { Note "${board}：$x" }
    if ($base) { $ot = G @('show', "${base}:$board"); if ($ot) { try { foreach ($x in @(Test-BoardBookkeeping (Read-BoardJson $ot) $d)) { Note "${board}：$x" } } catch {} } } }
}
$changed = @(); if ($base) { $changed = @((G @('diff', '--name-only', "$base...HEAD")) -split "`n" | Where-Object { $_ }) }
$closeout = 'board-closeout' -cin $labels

# 結案 PR（board-closeout 標籤，由有寫入權限的 Owner 加上）：只把一張卡從 In Review 移到 Done。
function Get-RawParts([string]$text) {
  # 原始 JSON 片段比對：卡片 id → 原文，其他頂層欄位 → 原文（不經轉型，避免漏掉任何欄位變更）
  $doc = [System.Text.Json.JsonDocument]::Parse($text)
  try {
    $items = [ordered]@{}; $top = [ordered]@{}
    foreach ($p in $doc.RootElement.EnumerateObject()) {
      if ($p.Name -ceq 'items') { $n = 0; foreach ($it in $p.Value.EnumerateArray()) { $k = "index:$n"; $n++
          if ($it.ValueKind -eq 'Object') { foreach ($q in $it.EnumerateObject()) { if ($q.Name -ceq 'id') { $k = 'id:' + $q.Value.ToString() } } }
          $items[$k] = $it.GetRawText() -replace "`r`n", "`n" } }
      elseif ($p.Name -cne 'updatedAt') { $top[$p.Name] = $p.Value.GetRawText() -replace "`r`n", "`n" }
    }
    return @{ items = $items; top = $top }
  } finally { $doc.Dispose() }
}
function Test-Closeout($card, [string]$boardText) {
  $e = [Collections.Generic.List[string]]::new(); $id = [string]$card['id']; $p = "board-closeout：$id "
  $boardRel = $board -replace '\\', '/'
  $other = @($changed | Where-Object { $_ -cne $boardRel })
  if ($other.Count) { $e.Add("board-closeout PR 只能修改 ${boardRel}，但也改了：" + ($other -join ', ')) }
  if (-not $base) { $e.Add('board-closeout 需要 BASE_SHA 才能比對 base 的看板'); return @($e) }
  $ot = G @('show', "${base}:$board")
  if (-not $ot) { $e.Add("board-closeout 讀不到 base 的 $board"); return @($e) }
  $old = Read-BoardJson $ot
  $oc = @($old['items'] | Where-Object { (IsObj $_) -and $_['id'] -ceq $id }) | Select-Object -First 1
  if (-not $oc) { $e.Add($p + '在 base 不存在；結案 PR 不能新增卡片') }
  elseif ($oc['status'] -cne 'In Review') { $e.Add($p + "在 base 的狀態是 $($oc['status'])；只能把 In Review 的卡移到 Done") }
  if ($card['status'] -cne 'Done') { $e.Add($p + "狀態是 $($card['status'])，結案 PR 必須設成 Done") }
  if ($card['light'] -cne 'Blue') { $e.Add($p + 'light 必須是 Blue') }
  if ($card['tdd'] -cne 'Green') { $e.Add($p + 'tdd 必須是 Green') }
  if ($card['ci'] -cne 'Green') { $e.Add($p + 'ci 必須是 Green') }
  if (-not (Has $card 'prUrl')) { $e.Add($p + '必須有 prUrl（已合併的 PR）') }
  if (-not (Has $card 'completedAt')) { $e.Add($p + '必須有 completedAt') }
  $hs = Get-V $card 'history'; $last = if ((IsArr $hs) -and $hs.Count) { $hs[$hs.Count - 1] } else { $null }
  if (-not ((IsObj $last) -and $last['from'] -ceq 'In Review' -and $last['to'] -ceq 'Done')) { $e.Add($p + 'history 最後一筆必須是 In Review → Done') }
  try {
    $a = Get-RawParts $ot; $b = Get-RawParts $boardText; $key = "id:$id"
    $diffIds = @(@($a.items.Keys) + @($b.items.Keys) | Select-Object -Unique | Where-Object { $_ -cne $key -and $a.items[$_] -cne $b.items[$_] } | ForEach-Object { $_ -replace '^id:', '' })
    if ($diffIds.Count) { $e.Add('board-closeout 只能改一張卡，但也改了：' + ($diffIds -join ', ')) }
    $diffTop = @(@($a.top.Keys) + @($b.top.Keys) | Select-Object -Unique | Where-Object { $a.top[$_] -cne $b.top[$_] })
    if ($diffTop.Count) { $e.Add('board-closeout 只能改卡片與頂層 updatedAt，但也改了頂層：' + ($diffTop -join ', ')) }
  } catch { $e.Add("board-closeout 無法比對看板：$($_.Exception.Message)") }
  return @($e)
}

# 2) PR 對應的 Task 卡片
$isRelease = $ref -match '^(release|hotfix)/'
if ($d -and -not $isRelease) {
  $tasks = @($d['items'] | Where-Object { (IsObj $_) -and $_['level'] -ceq 'Task' })
  $card = $tasks | Where-Object { $ref -like "feature/$($_['id'])-*" } | Select-Object -First 1
  if (-not $card) { $card = $tasks | Where-Object { $title -match ('(^|[\s\[(])' + [regex]::Escape($_['id']) + '([\s\]):]|$)') } | Select-Object -First 1 }
  if (-not $card) { Note "PR 沒有對應的 Task 卡片：分支要叫 feature/<task-id>-<slug>，或 PR 標題要包含 Task ID（目前分支 $ref）" }
  else {
    $id = $card['id']
    if ($closeout) { foreach ($x in @(Test-Closeout $card ([IO.File]::ReadAllText($board)))) { Note $x } }
    else {
      if ($card['status'] -cne 'In Review') { Note "$id 的狀態是 $($card['status'])，PR 送審時必須是 In Review（結案 PR 需由 Owner 加 board-closeout 標籤）" }
      if ($card['tdd'] -cne 'Green') { Note "$id 的 TDD 不是 Green" }
    }
    $sc = @{}; foreach ($it in $d['items']) { if ((IsObj $it) -and (IsArr $it['bdd'])) { foreach ($s in $it['bdd']) { $sc[[string]$s['id']] = $s['status'] } } }
    foreach ($s in @($card['scenarioIds'])) { if ($s -and $sc[[string]$s] -cne 'Green') { Note "$id 涵蓋的 BDD 情境 $s 不是 Green" } }
    if (-not @($card['scenarioIds']).Count) { $warns.Add("$id 沒有列出 scenarioIds") }
    Write-Host "對應卡片：$id $($card['title'])"
  }
}
# 3) 變更檔案
$feat = @($changed | Where-Object { $_ -match '\.feature$' })
if ($feat.Count -and 'spec-change' -notin $labels) { Note ("修改了 BDD 情境（" + ($feat -join ', ') + "），需要核准者加上 spec-change 標籤，並經 CODEOWNERS 審查") }
$prot = @($changed | Where-Object { $_ -match '^(\.ai-hooks/|\.githooks/|\.github/workflows/|\.github/ai-dev-guard/|\.cursor/hooks\.json$|\.claude/settings)' })
if ($prot.Count -and 'guard-change' -notin $labels) { Note ("修改了強制機制檔案（" + ($prot -join ', ') + "），需要 guard-change 標籤與 CODEOWNERS 審查") }
# 4) 不可新增略過的測試；共用詞法檢查不把引號中的審查證據當可執行程式。
if ($base) {
  $disableOutput = & python scripts/check_added_test_disables.py --base $base 2>&1
  if ($LASTEXITCODE -ne 0) { Note ("測試停用檢查失敗：" + ($disableOutput -join ' ')) }
}
# 5) 版本與 CHANGELOG
$verFiles = @($changed | Where-Object { $_ -match '(^|/)(Cargo\.toml|package\.json|tauri\.conf\.json)$' })
$deployChanged = $false
if ($d -and $base) { $ot = G @('show', "${base}:$board"); $oldIds = @{}
  if ($ot) { try { $od = Read-BoardJson $ot; foreach ($it in $od['items']) { if ((IsObj $it) -and $it['level'] -ceq 'Deployment') { $oldIds[[string]$it['id']] = ($it | ConvertTo-Json -Depth 8 -Compress) } } } catch {} }
  foreach ($it in $d['items']) { if ((IsObj $it) -and $it['level'] -ceq 'Deployment' -and $oldIds[[string]$it['id']] -ne ($it | ConvertTo-Json -Depth 8 -Compress)) { $deployChanged = $true } } }
function Get-Versions([string]$rev) {
  $v = [ordered]@{}
  foreach ($c in 'src-tauri/Cargo.toml', 'Cargo.toml') { $t = if ($rev) { G @('show', "${rev}:$c") } elseif (Test-Path $c) { Get-Content $c -Raw } else { $null }; if ($t -and $t -match '(?ms)^\[package\][^\[]*?^version\s*=\s*"([^"]+)"') { $v[$c] = $Matches[1]; break } }
  $t = if ($rev) { G @('show', "${rev}:package.json") } elseif (Test-Path 'package.json') { Get-Content 'package.json' -Raw } else { $null }; if ($t -and $t -match '"version"\s*:\s*"([^"]+)"') { $v['package.json'] = $Matches[1] }
  foreach ($c in 'src-tauri/tauri.conf.json', 'tauri.conf.json') { $t = if ($rev) { G @('show', "${rev}:$c") } elseif (Test-Path $c) { Get-Content $c -Raw } else { $null }; if ($t -and $t -match '"version"\s*:\s*"([^"]+)"') { $v[$c] = $Matches[1]; break } }
  $v
}
$now = Get-Versions ''
if (@($now.Values | Select-Object -Unique).Count -gt 1) { Note ('版本號不一致：' + (($now.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '、')) }
if ($isRelease -or $deployChanged) {
  if (-not ($changed | Where-Object { $_ -match '(^|/)CHANGELOG\.md$' })) { Note '這是發版／佈署相關的 PR，必須更新 CHANGELOG.md' }
  if ($base -and $now.Count) { $was = Get-Versions $base; $a = @($was.Values)[0]; $b = @($now.Values)[0]
    if ($a -and $b -and $a -eq $b) { Note "發版 PR 必須升版號（目前仍是 $b）" } }
}
foreach ($w in $warns) { Write-Host "::warning::$w" }
if ($errs.Count) { Write-Host "AI Dev Guard 未通過：$($errs.Count) 項"; exit 1 }
Write-Host 'AI Dev Guard 通過'; exit 0
