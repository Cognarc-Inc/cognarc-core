"""Cognarc Core：決策紀錄、授權、結果、身分與審計的共用層。

產品線（Jarvis、Praxon）建在這一層之上；本套件不得 import 任何產品線套件。
三個發行層級（oss、enterprise、internal）共用同一個 import 路徑 `cognarc_core`，
以 `cognarc_core.tier()` 查詢目前安裝的是哪一層；同一個環境永遠只能安裝其中一個 distribution。

文件與 docstring 裡的 SPEC-xx、ADR-xx、I-xx、S-xx 是 Cognarc 內部規格與不變量的編號，保留作追溯用。
"""

from cognarc_core._tier import TIER, Tier

__version__ = "0.1.0"
__all__ = ["TIER", "Tier", "__version__", "tier"]


def tier() -> Tier:
    """目前安裝的發行層級：'oss'、'enterprise' 或 'internal'。"""
    return TIER
