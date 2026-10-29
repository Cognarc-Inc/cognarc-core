"""測試共用裝置。

- 不需資料庫的測試直接跑。
- 標 `db` 的測試需要 Postgres：設 CORE_TEST_ADMIN_URL（能建角色、建庫的身分；scripts/dev_pg.sh up 會印出來）。
  未設時整組 skip。每次測試 session 重建 `cognarc_core_test` 資料庫並套用全部 schema。
- 兩個租戶（A、B）各一個租戶角色；一個登入角色 `core_test_svc` 可以 SET ROLE 成任一租戶角色。
  各測試用 uuid 產生自己的鍵，不清表（審計表禁止 TRUNCATE）。
"""

import os
import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from cognarc_core import schema
from cognarc_core.db.engine import make_engine

ADMIN_URL = os.environ.get("CORE_TEST_ADMIN_URL")
TEST_DB = os.environ.get("CORE_TEST_DB", "cognarc_core_test")
OWNER_ROLE = "core_test_owner"
LINE_ROLE = "core_test_line"
LINE = "test"
SVC_ROLE = "core_test_svc"
TENANT_A = uuid.UUID("0000000a-0000-4000-8000-000000000001")
TENANT_B = uuid.UUID("0000000b-0000-4000-8000-000000000001")
TENANT_ROLES = {TENANT_A: "core_test_t_a", TENANT_B: "core_test_t_b"}
WORKSPACE = uuid.UUID("0000000d-0000-4000-8000-0000000000aa")

SvcEngineFactory = Callable[[uuid.UUID], Engine]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if ADMIN_URL:
        return
    skip = pytest.mark.skip(reason="CORE_TEST_ADMIN_URL 未設定；scripts/dev_pg.sh up 可起臨時 Postgres")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    assert ADMIN_URL
    maintenance = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with maintenance.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    maintenance.dispose()
    url = make_url(ADMIN_URL).set(database=TEST_DB)
    engine = create_engine(url)
    schema.apply(engine, owner_role=OWNER_ROLE, line_role=LINE_ROLE, line=LINE)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{SVC_ROLE}') THEN
                    CREATE ROLE {SVC_ROLE} LOGIN NOINHERIT;
                END IF;
            END $$
            """
        )
        conn.exec_driver_sql(f'GRANT CONNECT ON DATABASE "{TEST_DB}" TO {SVC_ROLE}')
        for tenant_id, role in TENANT_ROLES.items():
            conn.exec_driver_sql(
                f"""
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                        CREATE ROLE {role} NOLOGIN INHERIT;
                    END IF;
                END $$
                """
            )
            conn.exec_driver_sql(f"GRANT {LINE_ROLE} TO {role} WITH INHERIT TRUE, SET FALSE")
            conn.exec_driver_sql(f"GRANT {role} TO {SVC_ROLE} WITH INHERIT FALSE, SET TRUE")
            conn.execute(
                text("INSERT INTO core.tenant (tenant_id, slug) VALUES (:t, :s) ON CONFLICT DO NOTHING"),
                {"t": tenant_id, "s": role.replace("core_test_t_", "tenant")},
            )
            conn.execute(
                text(
                    "INSERT INTO core.tenant_role (role_name, tenant_id, line) VALUES (:r, :t, :l) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"r": role, "t": tenant_id, "l": LINE},
            )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def svc_engine(admin_engine: Engine) -> Iterator[SvcEngineFactory]:
    """以行程登入角色連線並 SET ROLE 成指定租戶的角色（RLS 生效）。"""
    engines: dict[uuid.UUID, Engine] = {}
    base = make_url(ADMIN_URL or "").set(username=SVC_ROLE, password=None, database=TEST_DB)

    def factory(tenant_id: uuid.UUID) -> Engine:
        if tenant_id not in engines:
            engines[tenant_id] = make_engine(
                base.render_as_string(hide_password=False), set_role=TENANT_ROLES[tenant_id]
            )
        return engines[tenant_id]

    yield factory
    for engine in engines.values():
        engine.dispose()
