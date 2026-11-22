"""US market shortcuts: stocks, fundamentals, SPX options, rates and ETFs.

These wrap :func:`~quant_research_dataset.load` with the conventions most
academic and industry research uses, so common tasks take one call.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
import pandas as pd

from ..errors import QRDError
from ..query import DateLike, load

STOCK_DAILY = "us/equity/stock_daily"
FUNDAMENTALS_ANNUAL = "us/fundamentals/annual"
FUNDAMENTALS_QUARTERLY = "us/fundamentals/quarterly"
SPX_OPTIONS = "us/options/spx_option_prices"
SPX_SURFACE = "us/options/spx_vol_surface"
SPX_INDEX = "us/index/spx_daily"
ZERO_CURVE = "us/rates/zero_curve"


def _frame(obj: Any) -> pd.DataFrame:
    assert isinstance(obj, pd.DataFrame)
    return obj


def _ns(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).astype("datetime64[ns]")


# ------------------------------------------------------------------- equities
def get_stock_daily(
    permnos: int | Sequence[int] | None = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
    *,
    tickers: str | Sequence[str] | None = None,
    common_only: bool = False,
) -> pd.DataFrame:
    """Daily US stock data by PERMNO and/or ticker.

    >>> qrd.us.get_stock_daily(tickers="AAPL", start="2024-01-01",
    ...                       columns=["date", "permno", "ret"])   # doctest: +SKIP
    """
    filters = {"ticker": tickers} if tickers is not None else None
    return _frame(load(STOCK_DAILY, permnos, start, end, columns, filters, common_only=common_only))


def get_fundamentals(
    freq: Literal["quarterly", "annual"] = "quarterly",
    gvkeys: str | Sequence[str] | None = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
    *,
    point_in_time: bool = True,
    lag_days: int | None = None,
) -> pd.DataFrame:
    """Company fundamentals, with an ``available_date`` column by default.

    ``start``/``end`` select on the fiscal period end (``datadate``).
    """
    if freq not in ("quarterly", "annual"):
        raise QRDError("freq must be 'quarterly' or 'annual'")
    dataset = FUNDAMENTALS_QUARTERLY if freq == "quarterly" else FUNDAMENTALS_ANNUAL
    return _frame(
        load(dataset, gvkeys, start, end, columns, point_in_time=point_in_time, lag_days=lag_days)
    )


def merge_fundamentals(
    prices: pd.DataFrame,
    fundamentals: pd.DataFrame,
    *,
    date_col: str = "date",
    available_col: str = "available_date",
    max_staleness: str | pd.Timedelta | None = "400D",
) -> pd.DataFrame:
    """Attach the latest *known* fundamentals to each daily stock row (point in time).

    Stock rows carry the company key ``gvkey`` of the link valid on their date
    (added when the data is built), so the join needs no link table. Each row
    gets the most recent fundamentals row of its company whose
    ``available_date`` is on or before ``date``. Rows without a company, or
    without fundamentals known within ``max_staleness``, get nulls. Every input
    row is kept, in its original order.

    ``prices`` must include ``gvkey`` and ``date``; ``fundamentals`` must
    include ``gvkey``, ``datadate`` and ``available_date`` (load it with
    ``point_in_time=True``). Fundamentals columns whose names clash with
    ``prices`` get a ``_fund`` suffix.
    """
    for col in ("gvkey", "datadate", available_col):
        if col not in fundamentals.columns:
            raise QRDError(f"fundamentals is missing column {col!r} (use point_in_time=True)")
    for col in ("gvkey", date_col):
        if col not in prices.columns:
            raise QRDError(f"prices is missing column {col!r}; include it in columns=[...]")

    left = prices.assign(**{date_col: _ns(prices[date_col])}).reset_index(drop=True)
    left["_row"] = np.arange(len(left))

    # Latest fundamentals per company and availability date (keep the latest period).
    f = fundamentals.drop(columns=[c for c in ("permno",) if c in fundamentals.columns])
    f = f.assign(**{available_col: _ns(f[available_col])})
    f = f.sort_values([available_col, "datadate"]).drop_duplicates(
        ["gvkey", available_col], keep="last"
    )
    clash = [c for c in f.columns if c in left.columns and c != "gvkey"]
    f = f.rename(columns={c: f"{c}_fund" for c in clash})
    right_on = f"{available_col}_fund" if available_col in clash else available_col

    linked = left[left["gvkey"].notna()].sort_values(date_col)
    merged = pd.merge_asof(
        linked,
        f.sort_values(right_on),
        left_on=date_col,
        right_on=right_on,
        by="gvkey",
        direction="backward",
        tolerance=pd.Timedelta(max_staleness) if max_staleness is not None else None,
    )
    out = pd.concat([merged, left[left["gvkey"].isna()]], ignore_index=True)
    return out.sort_values("_row").drop(columns="_row").reset_index(drop=True)


# -------------------------------------------------------------------- options
def interpolate_zero_rate(
    curve: pd.DataFrame, dates: pd.Series, days: pd.Series | np.ndarray
) -> np.ndarray:
    """Linearly interpolate the zero curve at each ``(date, days)``.

    Rates are flat beyond the shortest and longest maturities. Returns the
    rate in **decimal** (e.g. 0.045), continuously compounded.
    """
    dates = _ns(pd.Series(dates)).reset_index(drop=True)
    days_arr = np.asarray(days, dtype="float64")
    curve = curve.assign(date=_ns(curve["date"])).sort_values(["date", "days"])
    out = np.full(len(dates), np.nan)
    by_date: dict[Any, pd.DataFrame] = dict(iter(curve.groupby("date")))
    for d, idx in dates.groupby(dates).groups.items():
        g = by_date.get(d)
        if g is None:
            continue
        pos = np.asarray(list(idx))
        out[pos] = (
            np.interp(days_arr[pos], g["days"].to_numpy(float), g["rate"].to_numpy(float)) / 100.0
        )
    return out


def zero_rate(
    dates: Sequence[DateLike] | pd.Series, days: Sequence[float] | np.ndarray
) -> np.ndarray:
    """Zero rate (decimal) for each date and maturity in days, from the stored curve."""
    dates = _ns(pd.Series(list(dates) if not isinstance(dates, pd.Series) else dates))
    curve = _frame(load(ZERO_CURVE, start=dates.min(), end=dates.max()))
    return interpolate_zero_rate(curve, dates, np.asarray(days, dtype="float64"))


def get_spx_options(
    start: DateLike,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
    *,
    cp_flag: Literal["C", "P"] | None = None,
    min_dte: int | None = None,
    max_dte: int | None = None,
    with_market: bool = False,
) -> pd.DataFrame:
    """SPX option quotes for a date range, with ``mid``, ``spread`` and ``dte``.

    ``with_market=True`` adds the index close (``spot``), the zero rate
    matched to each option's maturity (``rate``, decimal) and ``moneyness``
    (strike / spot).
    """
    end = end if end is not None else start
    filters: dict[str, Any] = {}
    if cp_flag is not None:
        filters["cp_flag"] = cp_flag
    df = _frame(load(SPX_OPTIONS, start=start, end=end, columns=columns, filters=filters or None))
    if min_dte is not None:
        df = df[df["dte"] >= min_dte]
    if max_dte is not None:
        df = df[df["dte"] <= max_dte]
    if with_market and len(df):
        spx = _frame(load(SPX_INDEX, start=start, end=end, columns=["date", "close"]))
        df = df.merge(spx.rename(columns={"close": "spot"}), on="date", how="left")
        curve = _frame(load(ZERO_CURVE, start=start, end=end))
        df["rate"] = interpolate_zero_rate(curve, df["date"], df["dte"].to_numpy())
        if "strike" in df.columns:
            df["moneyness"] = df["strike"] / df["spot"]
    return df.reset_index(drop=True)


def get_vol_surface(
    start: DateLike | None = None,
    end: DateLike | None = None,
    *,
    days: int | Sequence[int] | None = None,
    delta: int | Sequence[int] | None = None,
    cp_flag: Literal["C", "P"] | None = None,
) -> pd.DataFrame:
    """The SPX standardized vol surface, optionally restricted to grid points.

    >>> qrd.us.get_vol_surface("2020-01-01", "2020-12-31", days=30, delta=50, cp_flag="C")  # doctest: +SKIP
    """
    filters: dict[str, Any] = {}
    if days is not None:
        filters["days"] = days
    if delta is not None:
        filters["delta"] = delta
    if cp_flag is not None:
        filters["cp_flag"] = cp_flag
    return _frame(load(SPX_SURFACE, start=start, end=end, filters=filters or None))
