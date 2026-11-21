"""China A-share / Hong Kong H-share shortcuts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from ..query import DateLike, load

BARS = "cn_hk/equity/daily_bars"
PAIRS = "cn_hk/equity/ah_pairs"
FX = "cn_hk/fx/daily"
CNYHKD = "CNYHKD=X"  # HKD per 1 CNY


def _frame(obj: Any) -> pd.DataFrame:
    assert isinstance(obj, pd.DataFrame)
    return obj


def get_ah_pairs() -> pd.DataFrame:
    """All A/H pairs: ``a_symbol``, ``h_symbol``, ``name``."""
    return _frame(load(PAIRS))


def get_bars(
    symbols: str | Sequence[str] | None = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Daily bars for A-share and/or H-share symbols."""
    return _frame(load(BARS, symbols, start, end, columns))


def ah_premium(
    start: DateLike | None = None,
    end: DateLike | None = None,
    pairs: pd.DataFrame | None = None,
    price_col: str = "close",
) -> pd.DataFrame:
    """Daily A/H premium for each pair: ``a_price_cny / h_price_cny - 1``.

    H-share prices are converted from HKD to CNY with the CNY/HKD rate of the
    same date (the latest earlier rate if that date is missing). Only dates
    on which both lines traded are returned.
    """
    pairs = get_ah_pairs() if pairs is None else pairs
    symbols = sorted(set(pairs["a_symbol"]) | set(pairs["h_symbol"]))
    bars = get_bars(symbols, start, end, columns=["symbol", "date", price_col])
    fx = _frame(load(FX, CNYHKD, start, end, columns=["date", "close"]))
    fx = fx.rename(columns={"close": "cnyhkd"}).sort_values("date")

    a = bars.rename(columns={"symbol": "a_symbol", price_col: "a_price"})
    h = bars.rename(columns={"symbol": "h_symbol", price_col: "h_price_hkd"})
    out = pairs.merge(a, on="a_symbol").merge(h, on=["h_symbol", "date"]).sort_values("date")
    out = pd.merge_asof(out, fx, on="date", direction="backward")
    out["h_price_cny"] = out["h_price_hkd"] / out["cnyhkd"]
    out["premium"] = out["a_price"] / out["h_price_cny"] - 1.0
    cols = [
        "date",
        "name",
        "a_symbol",
        "h_symbol",
        "a_price",
        "h_price_hkd",
        "cnyhkd",
        "h_price_cny",
        "premium",
    ]
    return out[cols].sort_values(["a_symbol", "date"]).reset_index(drop=True)
