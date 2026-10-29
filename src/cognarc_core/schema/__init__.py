"""Core 的 Postgres schema：原生 SQL 檔依檔名順序套用；schema 的唯一來源是這些檔案，不在 Python 裡重複定義。

- 每個 `.sql` 檔第一行是 `-- tier: oss|enterprise|internal`；匯出較低層級時，較高層級的檔案不會存在。
- 檔案裡的 `{{owner_role}}`、`{{line_role}}`、`{{line}}` 由 `render()` 代入；角色名稱必須符合白名單格式。
- `apply()` 需要能建立角色、schema 並 `SET ROLE` 成 owner 的連線（migration 身分）；每個檔案各在一個交易內執行，
  已套用過的檔案記在 `core.schema_applied`，重跑會略過。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from sqlalchemy import Engine

from cognarc_core.db.engine import validate_role_name

TIER_ORDER: tuple[str, ...] = ("oss", "enterprise", "internal")
_PLACEHOLDER_OPEN = "{{"


@dataclass(frozen=True, slots=True)
class SchemaFile:
    name: str
    tier: str
    sql: str


class SchemaError(ValueError):
    pass


def _tier_of(name: str, first_line: str) -> str:
    prefix = "-- tier:"
    if not first_line.startswith(prefix):
        raise SchemaError(f"{name}: 第一行必須是 '-- tier: <oss|enterprise|internal>'")
    tier = first_line[len(prefix) :].strip()
    if tier not in TIER_ORDER:
        raise SchemaError(f"{name}: 未知的 tier {tier!r}")
    return tier


def load(max_tier: str = "internal") -> list[SchemaFile]:
    """套件內所有 SQL 檔（依檔名排序），只含 tier ≤ max_tier 的檔案。"""
    if max_tier not in TIER_ORDER:
        raise SchemaError(f"未知的 tier {max_tier!r}")
    limit = TIER_ORDER.index(max_tier)
    out: list[SchemaFile] = []
    for entry in sorted(files("cognarc_core.schema.sql").iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".sql"):
            continue
        sql = entry.read_text(encoding="utf-8")
        tier = _tier_of(entry.name, sql.splitlines()[0] if sql else "")
        if TIER_ORDER.index(tier) <= limit:
            out.append(SchemaFile(entry.name, tier, sql))
    return out


def render(sql: str, *, owner_role: str, line_role: str, line: str) -> str:
    """代入角色名稱與線別；剩下任何 `{{` 視為錯誤（避免把未代入的樣板送進資料庫）。"""
    validate_role_name(owner_role)
    validate_role_name(line_role)
    if not line.isidentifier() or not line.islower():
        raise SchemaError("line 必須是小寫識別字")
    rendered = (
        sql.replace("{{owner_role}}", owner_role)
        .replace("{{line_role}}", line_role)
        .replace("{{line}}", line)
    )
    if _PLACEHOLDER_OPEN in rendered:
        raise SchemaError("SQL 內有未代入的樣板變數")
    return rendered


def apply(
    engine: Engine,
    *,
    owner_role: str,
    line_role: str,
    line: str,
    max_tier: str = "internal",
    only: Sequence[str] | None = None,
) -> list[str]:
    """依序套用尚未套用的 SQL 檔；回傳這次套用的檔名。`only` 限定檔名（測試用）。"""
    applied: list[str] = []
    for item in load(max_tier):
        if only is not None and item.name not in only:
            continue
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS core")
            conn.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS core.schema_applied ("
                "file text PRIMARY KEY, tier text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = conn.exec_driver_sql(
                "SELECT 1 FROM core.schema_applied WHERE file = %(f)s", {"f": item.name}
            ).first()
            if done is not None:
                continue
            # 不經 SQLAlchemy／psycopg 的參數解析：SQL 裡的 format('%I') 會被誤認成佔位符。
            # 以 DBAPI cursor 不帶參數執行，多個敘述在同一交易內依序執行。
            cursor = conn.connection.cursor()
            try:
                cursor.execute(render(item.sql, owner_role=owner_role, line_role=line_role, line=line))
            finally:
                cursor.close()
            conn.exec_driver_sql(
                "INSERT INTO core.schema_applied (file, tier) VALUES (%(f)s, %(t)s)",
                {"f": item.name, "t": item.tier},
            )
            applied.append(item.name)
    return applied


def sql_dir() -> Path:
    return Path(str(files("cognarc_core.schema.sql")))
