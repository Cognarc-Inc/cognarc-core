# Cognarc Core

**English summary.** Cognarc Core is the shared bottom layer of Cognarc's products: a decision-record contract (evidence → proposal → assessment → policy → authorization → decision → action → outcome → calibration, with four separate timestamps) and PostgreSQL ledger primitives that make it enforceable: per-tenant roles with forced row-level security, idempotent inserts backed by unique keys, and insert-only audit tables whose triggers reject updates even from the owner. This open-source distribution (`cognarc-core`, Apache-2.0) contains the contract, the primitives and the base schema. Identity governance (two-person role grants, delegation, segregation of duties) and the tamper-evident audit hash chain ship in the enterprise distribution. Documentation and docstrings are in Traditional Chinese; identifiers like SPEC-xx / I-xx refer to Cognarc's internal specification numbering and are kept for traceability.

Cognarc Core 是「要留下可稽核決策紀錄」的系統的共用底層。本 distribution（`cognarc-core`，Apache-2.0）包含：

- **決策紀錄契約**：`docs/CONTRACT.md`、`contracts/decision_record.schema.json`。鏈上每一段寫進哪個物件、哪些欄位必填、四個時間欄位分開、只追加不改寫。
- **Postgres 帳本原語**（`src/cognarc_core/`）：
  - `clock`：一律回傳帶時區的 UTC；測試可注入 `ManualClock`。
  - `db.engine.make_engine`：每條連線建立後 `SET ROLE` 成租戶角色；不 `SET ROLE` 就沒有任何資料權限。
  - `db.idempotent.insert_idempotent`：同一個 unique 鍵重複寫入時回傳原紀錄，不建新紀錄。
  - `db.reflect.reflect_table`：以反射取得資料表；schema 只在 SQL 裡定義一次。
  - `decisions.record_decision`：寫一筆 DecisionRecord（決策發生即可用：event_time＝available_at＝decided_at）。
  - `schema.apply`：依序套用 `schema/sql/*.sql`：租戶與租戶角色、`core.current_tenant_id()`、Policy／DecisionRecord／OutcomeObservation（強制 RLS）、只增的 `core.audit_log`，以及 DecisionRecord 寫入即審計。

## 安裝與套用 schema

```bash
pip install cognarc-core        # 或 uv add cognarc-core
```

```python
from sqlalchemy import create_engine
from cognarc_core import schema

admin = create_engine("postgresql+psycopg://admin@127.0.0.1:5432/myapp")
schema.apply(admin, owner_role="myapp_owner", line_role="myapp_line", line="main")
```

之後依 `docs/SCHEMA.md` 建租戶角色與登入角色，應用程式以 `make_engine(url, set_role=<tenant_role>)` 連線。

## 開發

```bash
uv sync
make lint
make test                     # 不需資料庫
make pg-up && make test-db    # 需要 initdb／pg_ctl（PostgreSQL 16+）
```

## 企業版

身分與角色治理（兩人授予、代理 ≤ 5 交易日、建單者≠核准者等互斥在 DB trigger 層執行、access_log）與審計雜湊鏈（封存、驗證、每日封存匯出到客戶持有的儲存）在 `cognarc-core-enterprise`，依企業授權合約提供。兩個 distribution 共用 import 路徑 `cognarc_core`，同一個環境只能安裝其中一個；以 `cognarc_core.tier()` 查詢。

## 授權

Apache License 2.0，見 `LICENSE`。
