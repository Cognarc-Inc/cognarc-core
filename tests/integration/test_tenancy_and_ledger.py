"""oss 層的資料庫行為：RLS 租戶隔離、DecisionRecord 寫入即審計且不可改、冪等寫入、schema 重跑略過。"""

import uuid
from datetime import UTC, datetime

import psycopg.errors
import pytest
from sqlalchemy import Column, Engine, Integer, MetaData, Table, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from cognarc_core import schema
from cognarc_core.db.idempotent import insert_idempotent
from cognarc_core.db.reflect import reflect_table
from cognarc_core.decisions import record_decision
from tests.conftest import LINE, LINE_ROLE, OWNER_ROLE, TENANT_A, TENANT_B, WORKSPACE, SvcEngineFactory

pytestmark = pytest.mark.db


def _decide(engine: Engine, marker: str) -> uuid.UUID:
    with engine.begin() as conn:
        return record_decision(
            conn,
            workspace_id=WORKSPACE,
            subject_ref=f"probe:{marker}",
            actor=uuid.uuid4(),
            role="approver",
            decision="approve",
            at=datetime.now(UTC),
            policy_version="p1",
            inputs_refs=["evidence:x"],
        )


def test_schema_apply_is_idempotent(admin_engine: Engine) -> None:
    assert schema.apply(admin_engine, owner_role=OWNER_ROLE, line_role=LINE_ROLE, line=LINE) == []
    with admin_engine.connect() as conn:
        applied = {r[0] for r in conn.execute(text("SELECT file FROM core.schema_applied"))}
    assert applied == {i.name for i in schema.load()}


def test_decision_is_tenant_isolated(svc_engine: SvcEngineFactory) -> None:
    marker = uuid.uuid4().hex
    decision_id = _decide(svc_engine(TENANT_A), marker)
    with svc_engine(TENANT_A).connect() as conn:
        row = conn.execute(
            text("SELECT tenant_id FROM core.decision_record WHERE decision_id = :d"), {"d": decision_id}
        ).one()
        assert row.tenant_id == TENANT_A
    with svc_engine(TENANT_B).connect() as conn:
        assert (
            conn.execute(
                text("SELECT 1 FROM core.decision_record WHERE decision_id = :d"), {"d": decision_id}
            ).first()
            is None
        )


def test_unbound_role_sees_and_writes_nothing(admin_engine: Engine) -> None:
    """owner 也受 FORCE RLS 約束；沒有綁定租戶 → current_tenant_id() 為 NULL → 看不到、寫不進。"""
    with admin_engine.connect() as conn, conn.begin():
        conn.execute(text(f"SET LOCAL ROLE {OWNER_ROLE}"))
        assert conn.execute(text("SELECT count(*) FROM core.decision_record")).scalar_one() == 0
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    "INSERT INTO core.decision_record (tenant_id, workspace_id, subject_ref, actor, role, decision, decided_at) "
                    "VALUES (:t, :w, 'probe:x', gen_random_uuid(), 'r', 'd', now())"
                ),
                {"t": TENANT_A, "w": WORKSPACE},
            )


def test_decision_is_audited_and_immutable(svc_engine: SvcEngineFactory, admin_engine: Engine) -> None:
    marker = uuid.uuid4().hex
    decision_id = _decide(svc_engine(TENANT_A), marker)
    with svc_engine(TENANT_A).connect() as conn:
        audit = conn.execute(
            text("SELECT actor, action, payload FROM core.audit_log WHERE subject_ref = :s"),
            {"s": f"decision:{decision_id}"},
        ).one()
        assert (audit.actor, audit.action) == ("db:decision_record", "decision_recorded")
        assert audit.payload["subject_ref"] == f"probe:{marker}" and len(audit.payload["sha256"]) == 64
    for engine, label in ((svc_engine(TENANT_A), "tenant"), (admin_engine, "admin")):
        with engine.connect() as conn, pytest.raises(DBAPIError) as info:
            conn.execute(
                text("UPDATE core.decision_record SET decision = 'x' WHERE decision_id = :d"),
                {"d": decision_id},
            )
        assert isinstance(info.value.orig, psycopg.errors.InsufficientPrivilege), label
    with admin_engine.connect() as conn, pytest.raises(DBAPIError) as info:
        conn.execute(
            text("DELETE FROM core.audit_log WHERE subject_ref = :s"), {"s": f"decision:{decision_id}"}
        )
    assert isinstance(info.value.orig, psycopg.errors.InsufficientPrivilege)


def test_four_time_fields_are_separate_columns(admin_engine: Engine) -> None:
    with admin_engine.connect() as conn:
        table = reflect_table(conn, "core.decision_record")
    assert {"event_time", "published_at", "available_at", "ingested_at"} <= set(table.c.keys())


def test_insert_idempotent_returns_existing_row(admin_engine: Engine) -> None:
    with admin_engine.connect() as conn, conn.begin():
        conn.execute(text("CREATE TEMP TABLE idem_probe (a integer UNIQUE, b integer UNIQUE)"))
        table = Table("idem_probe", MetaData(), Column("a", Integer), Column("b", Integer))
        first = insert_idempotent(conn, table, {"a": 1, "b": 1}, ["a"])
        again = insert_idempotent(conn, table, {"a": 1, "b": 7}, ["a"])
        assert first.created and not again.created and again.row["b"] == 1
        # 另一個 unique 索引先衝突、而且同鍵紀錄不存在 → 真正的衝突，不得吞掉
        with pytest.raises(IntegrityError):
            insert_idempotent(conn, table, {"a": 2, "b": 1}, ["a"])
        # savepoint 讓交易仍可繼續使用
        assert insert_idempotent(conn, table, {"a": 3, "b": 3}, ["a"]).created
