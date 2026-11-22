"""China A-share shortcuts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from ..query import DateLike, load

CSI300_BARS = "cn_hk/equity/csi300_stock_daily"
CSI300_STOCKS = "cn_hk/equity/csi300_stocks"


def _frame(obj: Any) -> pd.DataFrame:
    assert isinstance(obj, pd.DataFrame)
    return obj


def get_csi300_stocks() -> pd.DataFrame:
    """Stocks that have been in the CSI 300: ``symbol``, ``name``, ``industry``, ``has_prices``."""
    return _frame(load(CSI300_STOCKS))


def get_csi300_prices(
    symbols: str | Sequence[str] | None = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Adjusted daily prices of CSI 300 constituent stocks (all of them by default)."""
    return _frame(load(CSI300_BARS, symbols, start, end, columns))
