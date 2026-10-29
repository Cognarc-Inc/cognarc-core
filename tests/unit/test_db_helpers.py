"""不需資料庫的 db/ 行為：角色名稱白名單、冪等鍵缺值。"""

import pytest
from sqlalchemy import Column, Integer, MetaData, Table

from cognarc_core.db.engine import RoleNameError, make_engine, validate_role_name
from cognarc_core.db.idempotent import insert_idempotent


@pytest.mark.parametrize("role", ["myapp_t_acme_main", "a", "x" * 63, "role_1"])
def test_valid_role_names(role: str) -> None:
    assert validate_role_name(role) == role


@pytest.mark.parametrize("role", ["", "Role", "1abc", 'x"; DROP ROLE y; --', "x" * 64, "a-b", "a b"])
def test_invalid_role_names_rejected(role: str) -> None:
    with pytest.raises(RoleNameError):
        validate_role_name(role)


def test_make_engine_validates_role_before_connecting() -> None:
    with pytest.raises(RoleNameError):
        make_engine("postgresql+psycopg://x@127.0.0.1:1/x", set_role="bad role")
    engine = make_engine("postgresql+psycopg://x@127.0.0.1:1/x", set_role=None)
    engine.dispose()


def test_insert_idempotent_requires_conflict_columns_in_values() -> None:
    table = Table("probe", MetaData(), Column("a", Integer), Column("b", Integer))
    with pytest.raises(ValueError, match="冪等鍵欄位缺值"):
        insert_idempotent(None, table, {"b": 1}, ["a"])  # type: ignore[arg-type]
