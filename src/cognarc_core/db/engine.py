"""建立 SQLAlchemy engine，並在每條連線建立後 `SET ROLE`。

出處：SPEC-01 §2.2、SPEC-07 §3：每租戶每線獨立 DB role，應用連線後 `SET ROLE`。
行程的登入角色是 NOINHERIT，不 `SET ROLE` 就沒有任何資料權限。
"""

import re
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry

ROLE_NAME_PATTERN = re.compile(r"[a-z_][a-z0-9_]{0,62}")


class RoleNameError(ValueError):
    """角色名稱不在白名單格式內（防止 SQL 注入）。"""


def validate_role_name(role: str) -> str:
    if not ROLE_NAME_PATTERN.fullmatch(role):
        raise RoleNameError("role name not allowed")
    return role


def make_engine(url: str, *, set_role: str | None, **kwargs: Any) -> Engine:
    """建立 engine；`set_role` 不為 None 時，每條新連線都先 `SET ROLE` 並提交。

    提交是必要的：psycopg 預設在交易中執行，未提交的 `SET ROLE` 會在連線池 rollback 時被還原。
    """
    role = validate_role_name(set_role) if set_role is not None else None
    engine = create_engine(url, **kwargs)
    if role is not None:

        def _set_role(dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(f'SET ROLE "{role}"')
            finally:
                cursor.close()
            dbapi_connection.commit()

        event.listen(engine, "connect", _set_role)
    return engine
