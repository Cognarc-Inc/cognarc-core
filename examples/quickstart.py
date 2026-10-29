"""The four quick-start steps from README.md, end to end, against a real PostgreSQL 16.

Usage:
    CORE_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres python examples/quickstart.py

The URL must belong to a role that can create databases and roles (a superuser on a throwaway
instance; `make pg-up` prints one). The script creates a database named `cognarc_quickstart`,
drops it first if it exists, and leaves it in place afterwards so you can inspect it.
"""

import os
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from cognarc_core import schema
from cognarc_core.db.engine import make_engine
from cognarc_core.decisions import record_decision

DATABASE = "cognarc_quickstart"
OWNER, LINE, SVC = "myapp_owner", "myapp_line", "myapp_svc"
TENANTS = {"acme": "myapp_t_acme_main", "globex": "myapp_t_globex_main"}


def first_line(exc: DBAPIError) -> str:
    return str(exc.orig).strip().splitlines()[0]


def main() -> int:
    admin_url = os.environ.get("CORE_TEST_ADMIN_URL")
    if not admin_url:
        print(
            "set CORE_TEST_ADMIN_URL to a PostgreSQL URL that can create roles and databases", file=sys.stderr
        )
        return 2

    # Fresh database for the demo.
    maintenance = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with maintenance.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{DATABASE}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{DATABASE}"'))
    maintenance.dispose()
    admin = create_engine(make_url(admin_url).set(database=DATABASE))

    # Step 2: apply the schema (idempotent).
    print("applied:", schema.apply(admin, owner_role=OWNER, line_role=LINE, line="main"))
    print("re-apply:", schema.apply(admin, owner_role=OWNER, line_role=LINE, line="main"))

    # Step 3: provision two tenants and one service login role.
    tenant_ids = {slug: uuid.uuid4() for slug in TENANTS}
    with admin.begin() as conn:
        conn.exec_driver_sql(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{SVC}') "
            f"THEN CREATE ROLE {SVC} LOGIN NOINHERIT; END IF; END $$"
        )
        conn.exec_driver_sql(f'GRANT CONNECT ON DATABASE "{DATABASE}" TO {SVC}')
        for slug, role in TENANTS.items():
            conn.exec_driver_sql(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "
                f"THEN CREATE ROLE {role} NOLOGIN INHERIT; END IF; END $$"
            )
            conn.exec_driver_sql(f"GRANT {LINE} TO {role} WITH INHERIT TRUE, SET FALSE")
            conn.exec_driver_sql(f"GRANT {role} TO {SVC} WITH INHERIT FALSE, SET TRUE")
            conn.execute(
                text("INSERT INTO core.tenant (tenant_id, slug) VALUES (:t, :s)"),
                {"t": tenant_ids[slug], "s": slug},
            )
            conn.execute(
                text("INSERT INTO core.tenant_role (role_name, tenant_id, line) VALUES (:r, :t, 'main')"),
                {"r": role, "t": tenant_ids[slug]},
            )

    # Step 4: record a decision as tenant "acme".
    svc_url = make_url(admin_url).set(username=SVC, password=None, database=DATABASE)
    svc_dsn = svc_url.render_as_string(hide_password=False)
    acme = make_engine(svc_dsn, set_role=TENANTS["acme"])
    globex = make_engine(svc_dsn, set_role=TENANTS["globex"])
    with acme.begin() as conn:
        decision_id = record_decision(
            conn,
            workspace_id=uuid.uuid4(),
            subject_ref="release:2026.10.29",
            actor=uuid.uuid4(),  # a principal id, never a name
            role="release_manager",
            decision="release",
            at=datetime.now(UTC),
            policy_version="release-policy/v3",
            inputs_refs=["ci:run/8812", "pr:412"],
        )
    print("decision_id:", decision_id)

    # Isolation: the other tenant shares the table but sees nothing.
    with acme.connect() as conn:
        print("acme sees:", conn.execute(text("SELECT count(*) FROM core.decision_record")).scalar_one())
        print("audit rows:", conn.execute(text("SELECT action, subject_ref FROM core.audit_log")).all())
    with globex.connect() as conn:
        print("globex sees:", conn.execute(text("SELECT count(*) FROM core.decision_record")).scalar_one())

    # Append-only: neither the schema owner nor a tenant can change what was written.
    for label, engine in (("owner", admin), ("tenant", acme)):
        try:
            with engine.begin() as conn:
                conn.execute(text("UPDATE core.audit_log SET action = 'tampered'"))
            print(f"{label} UPDATE succeeded: this is a bug, please report it")
            return 1
        except DBAPIError as exc:
            print(f"{label} UPDATE rejected:", first_line(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
