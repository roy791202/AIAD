# 產品測試索引

> 先讀主索引 [ai-dev-pipeline](../.agents/skills/ai-dev-pipeline/SKILL.md)。本檔只放共用規則與對照表；規則細節在 `references/`，一次只讀當下模組那一份。

## 一、共用規則

1. **四類都要有**：每條已核准規則都要有正常、邊界、無效輸入、失敗四類測試。
2. **角色隔離**：寫測試或程式的代理，不可以是執行「6. 驗證段」的代理。
3. **待決策不斷言**：牽涉 G01（檔案與身分契約）、G02（交易／Undo）、G03（快照與清理）、G04（模板支援矩陣）未決部分的規則，只列在「待決策」，不寫成會驗收的斷言；需要佔位時用 `#[ignore = "待 G0x"]` 並寫明原因。
4. **核准依據**：已核准表的「核准依據」欄寫 `正式核准` 或 `模組採納：<出處>`。模組採納的規則可以斷言，但不得延伸到上層決策還沒批准的內容。
5. **待確認不算 PASS**：UI/UX 參數表標「待確認」的參數，不能拿來判 TDD_PASS。
6. **已知衝突暫不斷言**：「7. 已知衝突」列出的規格與實作衝突，相關測試先不寫斷言，等看板上的決策卡拍板。
7. **規格只連結**：規則只寫一句話加出處，不抄規格內容；規格以 `docs/requirements-confirmation/phase1-spec/` 為準。
8. **真的跑過才算**：判 PASS 前要在輸出確認測試真的執行；遇到 skip 或 `NOT RUN` 一律判 NOT RUN，不能只看 exit code。

## 二、命名與證據

- 規則 ID：`R-<模組>-<兩位流水號>`（UI/UX 參數用 `R-UI-NN`）。工單卡仍用 `PD-<模組>-<名稱>-NN`，兩者互相引用。
- 測試名稱：Rust 用 `should_<行為>_when_<條件>`；Node 用 `test('should … when …')`。
- 重跑指令：`cargo test -p <crate> --test <檔名>` 或 `node --test ui/<x>.test.cjs`。
- 證據：截圖錄影放 `reports/dispatch-pd/<卡ID>-evidence/`（不進 git）；驗收報告 `reports/dispatch-pd/<卡ID>-TDD-REVIEW.md`，結論只有 `TDD_PASS`／`TDD_FAIL`。M08 的驗收結論另寫 `tasks/M08/verification/`。
- 每條規則一筆證據：規則、指令、Exit code、輸出末段、介面證據、判定。

## 三、對照表

| 模組 | 功能 | 參考檔 |
|---|---|---|
| M01 專案定義與新建 | F01 | [m01-project-definition.md](../.agents/skills/ai-dev-product-tests/references/m01-project-definition.md) |
| M02 模板與雙骨架 | F02、F03 | [m02-templates-skeletons.md](../.agents/skills/ai-dev-product-tests/references/m02-templates-skeletons.md) |
| M03 架構與 UI 設計 | F04 | [m03-architecture-ui-design.md](../.agents/skills/ai-dev-product-tests/references/m03-architecture-ui-design.md) |
| M04 文件與單文件歷史 | F05、F10 | [m04-documents-history.md](../.agents/skills/ai-dev-product-tests/references/m04-documents-history.md) |
| M05 素材 | F06 | [m05-assets.md](../.agents/skills/ai-dev-product-tests/references/m05-assets.md) |
| M06 交換與合併 | F07、F08、F09 | [m06-exchange-merge.md](../.agents/skills/ai-dev-product-tests/references/m06-exchange-merge.md) |
| M07 復原與歷史入口 | F11、F12 | [m07-recovery-history.md](../.agents/skills/ai-dev-product-tests/references/m07-recovery-history.md) |
| M08 Windows 驗收整合 | M08-VERIFY | [m08-windows-acceptance.md](../.agents/skills/ai-dev-product-tests/references/m08-windows-acceptance.md) |
| UI/UX 參數（偏好、tokens、Designer 屬性、架構圖 Inspector） | F02、F04 | [ui-parameters.md](../.agents/skills/ai-dev-product-tests/references/ui-parameters.md) |

## 四、每份參考檔的固定段落

`1. 範圍與來源`、`2. 業務規則`、`3. 已有測試對照`、`4. 測試矩陣`、`5. 開發段（RED）`、`6. 驗證段`、`7. 已知衝突`。
`python tools/skills/sync_skills.py --check` 會檢查段落齊全；確認 manifest 的每個交付功能都出現在某份參考檔的「1. 範圍與來源」，且在上面對照表有指定的參考檔；對照表與 `references/` 的檔案一一對應。
