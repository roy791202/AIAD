# Tag apply gate（PD-REMAIN-TAG-APPLY-01）

SemVer `git tag` 實打閘門說明。對齊 `BDD-PD-REMAIN-TAG-APPLY-01`。

腳本：[`tools/board/tag_prep.py`](../tools/board/tag_prep.py)

## 規則（硬）

| 規則 | 說明 |
|------|------|
| 預設 dry-run | 不加旗標 → 只印計畫；**不**執行 `git tag` |
| dry-run ≠ 已發布 | 輸出固定 `published=no`；不得把計畫當成已 tag／已發佈 |
| `--apply` 需雙旗標 | 必須同時有 `--apply` **與** `--owner-approved`（owner 閘） |
| 缺閘 → GATE_BLOCKED | 僅 `--apply` → `tag_status=GATE_BLOCKED`；不呼叫 tagger；exit `3` |
| 不做預設 push | 本工具**不實作** `git push`；傳 `--push` → 錯誤退出 |

## Owner 核准流程

1. Owner 書面／決策卡核准「允許實打 git tag」（例：對應 `PD-DEC-NEXT-SCOPE` tag 項另令）。
2. 先跑 dry-run 對照 CHANGELOG：

   ```text
   python tools/board/tag_prep.py --version 0.1.0
   ```

   預期：`mode=dry-run`、`planned_tag=v0.1.0`、`published=no`、`push=no`。

3. 核准後再顯式雙旗標（預設 stub 仍 **NOT RUN**，除非注入真 tagger）：

   ```text
   python tools/board/tag_prep.py --apply --owner-approved --version 0.1.0
   ```

4. **禁止**：把 dry-run 輸出、CHECKLIST 勾選、或 `GATE_BLOCKED` 寫成「已發布」。
5. **禁止**：預設／自動 `git push`；遠端推送另案人工處理。

## 狀態語意

| `tag_status` | 意義 |
|--------------|------|
| `PLANNED` | dry-run 計畫；非發布 |
| `GATE_BLOCKED` | `--apply` 缺 `--owner-approved` |
| `NOT RUN` | 閘已開但後端 stub／未真打 tag |
| `TAGGED` | 真 tagger 成功（預設路徑不產生） |

| `gate_status` | 意義 |
|---------------|------|
| `N/A` | dry-run |
| `BLOCKED` | 缺 owner 閘 |
| `OPEN` | `--apply` + `--owner-approved` |

## 驗收（本卡）

```text
cd tools/board
python test_tag_prep.py
python tag_prep.py --version 0.1.0
# mode=dry-run published=no

python tag_prep.py --apply --version 0.1.0
# tag_status=GATE_BLOCKED published=no；exit 3

python tag_prep.py --apply --owner-approved --version 0.1.0
# gate_status=OPEN tag_status=NOT RUN published=no push=no（預設 stub）
```
