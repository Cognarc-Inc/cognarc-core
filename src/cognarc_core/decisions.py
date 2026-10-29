"""寫入 DecisionRecord（SPEC-01 §4；SPEC-07 §6）。角色變更、核准、授權、控制動作、結案都經這裡。

時間語意（cognarc-decision-record）：決策發生即可用，event_time＝available_at＝decided_at；ingested_at 是寫入時刻。
"""

import json
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Connection, text


def record_decision(
    conn: Connection,
    *,
    workspace_id: uuid.UUID,
    subject_ref: str,
    actor: uuid.UUID,
    role: str,
    decision: str,
    at: datetime,
    policy_version: str | None = None,
    inputs_refs: Sequence[object] = (),
) -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO core.decision_record "
            "(tenant_id, workspace_id, subject_ref, actor, role, policy_version, inputs_refs, decision, decided_at, "
            "event_time, available_at, ingested_at) "
            "VALUES (core.current_tenant_id(), :w, :s, :a, :r, :pv, CAST(:refs AS jsonb), :d, :at, :at, :at, now()) "
            "RETURNING decision_id"
        ),
        {
            "w": workspace_id,
            "s": subject_ref,
            "a": actor,
            "r": role,
            "pv": policy_version,
            "refs": json.dumps(list(inputs_refs), ensure_ascii=False, default=str),
            "d": decision,
            "at": at,
        },
    ).scalar_one()
