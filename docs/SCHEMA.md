# Schema 與角色模型

schema 的唯一來源是 `src/cognarc_core/schema/sql/*.sql`，依檔名順序套用；Python 只以反射取得資料表（`cognarc_core.db.reflect`），不重複定義。

## 套用

```python
from sqlalchemy import create_engine
from cognarc_core import schema

admin = create_engine(
    "postgresql+psycopg://admin@127.0.0.1:5432/myapp"
)  # 能建角色、schema 並 SET ROLE 成 owner
schema.apply(admin, owner_role="myapp_owner", line_role="myapp_line", line="invest")
```

- `{{owner_role}}`：NOLOGIN，擁有 `core` schema 與所有物件。
- `{{line_role}}`：NOLOGIN，一條產品線的權限集合。
- `{{line}}`：線別代碼；`core.current_tenant_id()` 只對該線別的租戶角色回傳租戶。
- 每個檔案各在一個交易內執行；已套用的檔案記在 `core.schema_applied`，重跑會略過。
- 已發行的 SQL 檔不改寫；要改就新增檔案（oss 用 0xx，enterprise 用 1xx，internal 用 2xx）。

## 租戶與連線

1. 每租戶每線一個 DB 角色（例如 `myapp_t_acme_invest`），`NOLOGIN INHERIT`，`GRANT <line_role> TO <tenant_role> WITH INHERIT TRUE, SET FALSE`。
2. 把租戶角色寫進 `core.tenant_role (role_name, tenant_id, line)`。
3. 行程的登入角色 `LOGIN NOINHERIT`，`GRANT <tenant_role> TO <svc_role> WITH INHERIT FALSE, SET TRUE`。
4. 應用程式用 `cognarc_core.db.engine.make_engine(url, set_role=<tenant_role>)` 建 engine：每條新連線先 `SET ROLE` 並提交。不 `SET ROLE` 就沒有任何資料權限。
5. 所有租戶資料表 `ENABLE` 並 `FORCE ROW LEVEL SECURITY`，policy 為 `tenant_id = core.current_tenant_id()`，讀寫都套用。未綁定租戶的角色得到 NULL，看不到也寫不進任何列。

## 檔案與物件

| 檔案 | tier | 物件 |
| --- | --- | --- |
| `000_bootstrap.sql` | oss | 角色、`core` schema、`core.schema_applied`、資料庫 timezone=UTC |
| `010_tenancy.sql` | oss | `core.tenant`、`core.tenant_role`（RLS：只看自己的對照列）、`core.current_tenant_id()` |
| `020_ledger.sql` | oss | `core.policy`、`core.decision_record`、`core.outcome_observation`（共通欄位、RLS、只授 SELECT/INSERT） |
| `030_audit_log.sql` | oss | `core.audit_log`（只增）、`core.forbid_audit_modification()`、DecisionRecord 不可改＋寫入即審計（`core.audit_decision()`） |
| `110_identity.sql` | enterprise | `core.principal`、`core.role_grant`、`core.role_grant_request`、`core.delegation`、`core.access_log`、`core.tenant.role_bootstrap_open`、`person_of`、`person_roles`、`check_role_combination`、`check_role_grant`、`check_delegation`、`forbid_reactivation`、`delegated_persons`、`acts_as_person`、`acts_as_person_at_or_now` |
| `120_audit_chain.sql` | enterprise | `core.audit_chain`、`core.audit_daily_seal`、`audit_row_hash`、`audit_seal`、`audit_verify`（含每日封存錨定） |

## 不可改的表

`core.audit_log`、`core.decision_record`、`core.access_log`、`core.audit_chain`、`core.audit_daily_seal`：
權限只有 SELECT、INSERT，而且 trigger 讓 UPDATE、DELETE、TRUNCATE 一律拋 `insufficient_privilege`，對 owner 與 superuser 也有效。

## 冪等寫入

`cognarc_core.db.idempotent.insert_idempotent(conn, table, values, conflict_cols)`：同一個 unique 鍵重複寫入時回傳既有的那一筆（`created=False`），不建新紀錄。冪等由 Postgres 的 unique 鍵保證，不靠應用層記憶或訊息佇列。
