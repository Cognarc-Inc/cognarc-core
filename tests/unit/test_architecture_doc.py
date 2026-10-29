"""架構文件涵蓋每個模組與 SQL 檔：新增模組或 SQL 檔時，要一併寫進對應層的架構文件。

只讀目前樹裡存在的文件（oss 樹只有 ARCHITECTURE.md；enterprise 另有 ENTERPRISE-ARCHITECTURE.md；
internal 另有 INTERNAL-ARCHITECTURE.md），所以每一層的匯出樹都能自己通過。
"""

from pathlib import Path

import cognarc_core

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(cognarc_core.__file__).resolve().parent
DOCS = ("ARCHITECTURE.md", "ENTERPRISE-ARCHITECTURE.md", "INTERNAL-ARCHITECTURE.md")


def _docs_text() -> str:
    return "\n".join(
        (ROOT / "docs" / name).read_text(encoding="utf-8") for name in DOCS if (ROOT / "docs" / name).exists()
    )


def _modules() -> list[str]:
    out: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        rel = path.relative_to(PACKAGE_DIR).with_suffix("")
        parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
        out.append(".".join(("cognarc_core", *parts)))
    return out


def test_core_architecture_doc_exists() -> None:
    assert (ROOT / "docs" / "ARCHITECTURE.md").exists()


def test_every_module_is_described() -> None:
    text = _docs_text()
    missing = [module for module in _modules() if f"`{module}" not in text]
    assert missing == [], f"架構文件沒有提到這些模組：{missing}"


def test_every_sql_file_is_described() -> None:
    text = _docs_text()
    sql_files = sorted((PACKAGE_DIR / "schema" / "sql").glob("*.sql"))
    missing = [path.name for path in sql_files if path.name not in text]
    assert missing == [], f"架構文件沒有提到這些 SQL 檔：{missing}"
