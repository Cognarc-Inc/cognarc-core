"""套件內的 import 閉包：每個 `cognarc_core.*` 的 import 都要在目前安裝的套件裡找得到，而且 Core 不得 import 產品線。

匯出較低層級時較高層級的模組不存在；這個測試在每一層的匯出樹都要過。
"""

import ast
from pathlib import Path

import cognarc_core

PACKAGE_DIR = Path(cognarc_core.__file__).resolve().parent
PRODUCT_PACKAGES = {"jarvis", "jarvis_app", "jarvis_bridge", "praxon", "cognarc_foundry", "cognarc_praxon"}


def _modules() -> set[str]:
    out: set[str] = set()
    for path in PACKAGE_DIR.rglob("*.py"):
        rel = path.relative_to(PACKAGE_DIR).with_suffix("")
        parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
        out.add(".".join(("cognarc_core", *parts)))
    return out


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def test_internal_imports_resolve_within_installed_tier() -> None:
    modules = _modules()
    for path in PACKAGE_DIR.rglob("*.py"):
        for name in _imports(path):
            if name == "cognarc_core" or name.startswith("cognarc_core."):
                assert name in modules, f"{path.relative_to(PACKAGE_DIR)} import 了不存在的 {name}"


def test_core_never_imports_product_lines() -> None:
    for path in PACKAGE_DIR.rglob("*.py"):
        top = {name.split(".")[0] for name in _imports(path)}
        assert not (top & PRODUCT_PACKAGES), f"{path.relative_to(PACKAGE_DIR)} import 了產品線套件"


def test_tier_marker_matches_available_modules() -> None:
    tier = cognarc_core.tier()
    modules = _modules()
    has_enterprise = "cognarc_core.identity" in modules and "cognarc_core.audit" in modules
    has_internal = "cognarc_core.egress" in modules
    expected = {"oss": (False, False), "enterprise": (True, False), "internal": (True, True)}[tier]
    assert (has_enterprise, has_internal) == expected, f"tier={tier} 但模組組合不符"
