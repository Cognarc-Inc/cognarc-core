# Cognarc 決策紀錄契約

> 本文是 Cognarc Core 的共用契約。產品線（投資線 Jarvis、軟體交付線 Praxon，或任何第三方系統）實作時對齊的是這裡的語意；程式可以共用（本套件），資料不共用。

## 目的

任何會產生「決策、授權、行動或結果」的功能，都要先回答：它在 **證據 → 提案 → 評估 → 政策 → 授權 → 決策 → 行動 → 結果 → 校準** 這條鏈的哪一段，寫進哪個物件，哪些欄位必填。回答不出來的功能只是一個終端功能，無法稽核，也無法在事後回溯「誰、何時、依什麼、結果如何」。

## 共用鏈與物件

| 環節 | 共用物件（Core） | 投資線特化（例） | 軟體交付特化（例） |
| --- | --- | --- | --- |
| 證據 | EvidenceArtifact、Claim、SignalObservation | 行情快照、公開事件、策略輸出 | PR、CI、發布紀錄 |
| 提案 | DecisionProposal | ExecutionIntent | ReleaseCandidate |
| 評估 | RiskAssessment（關卡結果） | 限額、權限、名單、報價容差 | 測試、相容性、風險 |
| 政策 | Policy（有版本） | 限額、核准路由、限制名單 | 發布政策 |
| 授權 | Authorization | 逐筆核准或預先授權 | 核准發布 |
| 決策 | DecisionRecord | 核准、不交易、修改數量、結案 | 發布、延後、回滾 |
| 行動 | ActionRecord | OrderEvent、Fill | Deploy |
| 結果 | OutcomeObservation | ReconciliationRecord | 事故、指標 |
| 校準 | CalibrationNote | 限額與參數調整（由人決定） | 政策調整 |

「不交易」與「不發布」都是 DecisionRecord，不是沒有紀錄。

本套件目前以 DDL 落實的物件：Policy、DecisionRecord、OutcomeObservation（oss）；Principal、RoleGrant、Delegation、AccessLog、AuditChain（enterprise）。Authorization、Proposal、Evidence 等物件的欄位在各產品線差異大，本層只定語意，由產品線建表。

## 每個物件的必填欄位

- **識別**：`tenant_id`、`workspace_id`（投資線另有 portfolio_id、account_id、instrument_id）。
- **時間**（四個分開，缺一不可，一律 UTC）：
  - `event_time`：事情發生。
  - `published_at`：對外公開。
  - `available_at`：我們能用。
  - `ingested_at`：進系統。
  - 有效期用 `valid_from`／`valid_to`。
- **版本**：`source_version`、`model_version`、`policy_version`、`strategy_version`（依物件而定）。
- **來源**：`evidence_refs`／`inputs_refs`、`lineage`。
- **治理**：`usage_scope`、`confidentiality`、`approval_state`。
- **人**：`created_by`、`approved_by`、`acked_by` 存角色與身分代碼（principal_id），不存姓名。

決策的時間語意：決策發生即可用，`event_time`＝`available_at`＝`decided_at`；`ingested_at` 是寫入時刻（見 `cognarc_core.decisions.record_decision`）。

## 分層規則

| 層 | 放什麼 | 不放什麼 |
| --- | --- | --- |
| 正式帳本（Postgres） | 觀測數值、決策、授權、委託、成交、持倉、帳務、政策版本 | 摘要、推論 |
| Hot Track（近期記憶） | 近期脈絡、偏好、非權威檢索 | 任何會被當成事實的數字 |
| Cold Track（跨文件關係） | 跨文件關係、歷史主張 | 帳務、持倉、授權 |

摘要不覆寫帳本；記憶命中不等於事實已驗證；研究重跑不得觸發行動。

## 事件紀錄規則

- 只追加，不改寫；更正另留一筆。
- 一筆行動能從結果回溯到授權、決策、評估、提案、證據，每一步都有 `policy_version`。
- 政策版本變動時，標示哪些尚未執行的授權失效。
- `unknown` 不是 `pass`：無法確認的結果只能查詢，不能重送，也不能被當成通過。

## 互斥（治理層最小集合）

- 建單者 ≠ 核准者；授權者 ≠ 策略管理者；結案者 ≠ 建單者。
- 以 `natural_person_ref`（自然人）判定，不以帳號判定；代理期間，代理人與原持有人視為同一人。
- 在 API、服務層、DB trigger 三層各自執行。enterprise 層的 `identity.py` 與 `110_identity.sql` 實作其中的角色授予、代理與角色組合規則。

## 機器可讀版本

`contracts/decision_record.schema.json` 是 DecisionRecord 的 JSON Schema（v1）。其他物件的 schema 隨產品線需要補上，`$id` 一律用 `urn:cognarc:core:contracts:<object>:v<n>`。

## 新功能的檢查表

對每個新增或修改的功能寫一張表：環節 · 物件 · 新增欄位 · 四個時間各是什麼 · 版本欄位 · 層（帳本／Hot／Cold）· 誰建、誰核、誰結案。缺任一格就是設計缺口，不是略過。
