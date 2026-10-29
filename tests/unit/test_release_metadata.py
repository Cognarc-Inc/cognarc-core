"""發行中繼資料一致：pyproject、套件 __version__、CITATION.cff、CHANGELOG 指向同一個版本與日期。

發行時只改其中一處、忘了其他處，是公開 repo 最常見的版本錯配；這裡在每一層的匯出樹都檢查。
"""

import re
import tomllib
from pathlib import Path

import cognarc_core

ROOT = Path(__file__).resolve().parents[2]


def _project_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return str(project["version"])


def _citation_field(name: str) -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(rf'^{name}:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    assert match, f"CITATION.cff 缺 {name}"
    return match.group(1)


def _changelog_date(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$", text, re.MULTILINE)
    assert match, f"CHANGELOG.md 缺 ## [{version}] - YYYY-MM-DD 段落"
    return match.group(1)


def test_package_version_matches_pyproject() -> None:
    assert cognarc_core.__version__ == _project_version()


def test_citation_version_matches_pyproject() -> None:
    assert _citation_field("version") == _project_version()


def test_citation_date_matches_changelog() -> None:
    assert _citation_field("date-released") == _changelog_date(_project_version())
