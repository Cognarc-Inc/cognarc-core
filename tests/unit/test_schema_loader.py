"""schema 載入與樣板代入（不連資料庫）。"""

import pytest

from cognarc_core import schema
from cognarc_core.db.engine import RoleNameError


def test_files_are_ordered_and_tier_tagged() -> None:
    items = schema.load()
    names = [i.name for i in items]
    assert names == sorted(names)
    assert names[0] == "000_bootstrap.sql"
    ranks = [schema.TIER_ORDER.index(i.tier) for i in items]
    assert ranks == sorted(ranks), "較高層級的 SQL 檔編號必須在較低層級之後"


def test_load_filters_by_tier() -> None:
    oss = {i.name for i in schema.load("oss")}
    assert oss == {i.name for i in schema.load() if i.tier == "oss"}
    assert all(i.tier in ("oss", "enterprise") for i in schema.load("enterprise"))
    with pytest.raises(schema.SchemaError):
        schema.load("premium")


def test_render_substitutes_and_validates() -> None:
    out = schema.render(
        "CREATE ROLE {{owner_role}}; GRANT x TO {{line_role}}; -- {{line}}",
        owner_role="o",
        line_role="l",
        line="invest",
    )
    assert out == "CREATE ROLE o; GRANT x TO l; -- invest"
    with pytest.raises(RoleNameError):
        schema.render("{{owner_role}}", owner_role="bad role", line_role="l", line="invest")
    with pytest.raises(schema.SchemaError):
        schema.render("{{owner_role}}", owner_role="o", line_role="l", line="Invest")
    with pytest.raises(schema.SchemaError, match="未代入"):
        schema.render("{{unknown}}", owner_role="o", line_role="l", line="invest")


def test_every_file_renders_without_leftover_placeholders() -> None:
    for item in schema.load():
        rendered = schema.render(item.sql, owner_role="o", line_role="l", line="test")
        assert "{{" not in rendered, item.name


def test_oss_sql_does_not_reference_enterprise_objects() -> None:
    enterprise_objects = (
        "core.principal",
        "core.role_grant",
        "core.delegation",
        "core.access_log",
        "core.audit_chain",
        "core.audit_daily_seal",
        "core.person_of",
        "core.audit_seal",
    )
    for item in schema.load("oss"):
        for obj in enterprise_objects:
            assert obj not in item.sql, f"{item.name} 參照了 enterprise 物件 {obj}"
