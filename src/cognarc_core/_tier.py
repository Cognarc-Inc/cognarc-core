"""發行層級標記。由 tools/export_tier.py 在匯出時改寫；來源 repo 本身是 internal。"""

from typing import Literal

Tier = Literal["oss", "enterprise", "internal"]
TIER: Tier = "oss"
