"""冪等寫入：同一個 unique 鍵重複寫入時回傳原紀錄，不建立新紀錄（SPEC-01 §2.3；I-02～I-04）。

冪等由 Postgres 的 unique 鍵保證，不靠應用層的記憶或 Redis。
在 READ COMMITTED 下，並行的同鍵寫入會在 unique 索引上等待先到者提交，再走 DO NOTHING，
接著讀到先到者已提交的紀錄，所以每個呼叫端都拿到同一筆。

表上若還有另一個涵蓋同一鍵的 unique 索引（例如複合外鍵用的 (tenant_id, intent_id)），並行時衝突可能先在
那個索引上被偵測到；ON CONFLICT 只處理指定的索引，於是拋 UniqueViolation。所以 INSERT 放在 savepoint 裡，
遇到 UniqueViolation 時改讀既有紀錄；讀不到才往外拋（真的是別的鍵衝突）。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, Connection, RowMapping, Table, and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError


@dataclass(frozen=True, slots=True)
class IdempotentResult:
    row: RowMapping
    created: bool


def insert_idempotent(
    conn: Connection,
    table: Table,
    values: Mapping[str, Any],
    conflict_cols: Sequence[str],
    *,
    index_where: ColumnElement[bool] | None = None,
) -> IdempotentResult:
    """寫入一筆；若 `conflict_cols` 對應的 unique 鍵已存在，回傳既有的那一筆。

    `index_where` 用於部分唯一索引（例如只對 ACK 事件的 seq_no 唯一）。
    """
    missing = [c for c in conflict_cols if c not in values]
    if missing:
        raise ValueError(f"冪等鍵欄位缺值：{missing}")
    stmt = (
        pg_insert(table)
        .values(dict(values))
        .on_conflict_do_nothing(index_elements=list(conflict_cols), index_where=index_where)
        .returning(*table.c)
    )
    key = and_(*(table.c[c] == values[c] for c in conflict_cols))
    if index_where is not None:
        key = and_(key, index_where)
    try:
        with conn.begin_nested():
            inserted = conn.execute(stmt).mappings().first()
    except IntegrityError as exc:
        if not isinstance(exc.orig, UniqueViolation):
            raise
        existing = conn.execute(select(table).where(key)).mappings().first()
        if existing is None:
            raise
        return IdempotentResult(existing, False)
    if inserted is not None:
        return IdempotentResult(inserted, True)
    existing = conn.execute(select(table).where(key)).mappings().one()
    return IdempotentResult(existing, False)
