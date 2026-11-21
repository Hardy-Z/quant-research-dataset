"""Small, dependency-free research helpers: portfolio sorts and performance stats."""

from __future__ import annotations

import numpy as np
import pandas as pd


def quantile_portfolios(
    df: pd.DataFrame,
    signal: str,
    ret: str = "ret",
    date: str = "date",
    n: int = 10,
    weight: str | None = None,
    min_obs: int = 20,
) -> pd.DataFrame:
    """Sort assets into ``n`` quantiles of ``signal`` each date and average their returns.

    ``df`` holds one row per asset and date, where ``signal`` is known at
    ``date`` and ``ret`` is the return over the *next* holding period (shift
    returns yourself so there is no look-ahead). Returns a wide frame indexed
    by date with columns ``1..n`` and ``long_short`` (quantile n minus 1).
    ``weight`` (e.g. lagged market cap) gives value-weighted portfolios.
    Dates with fewer than ``min_obs`` valid rows are skipped.
    """
    cols = [date, signal, ret] + ([weight] if weight else [])
    data = df[cols].dropna()
    counts = data.groupby(date)[signal].transform("size")
    data = data[counts >= max(min_obs, n)]
    if data.empty:
        return pd.DataFrame(columns=[*range(1, n + 1), "long_short"])
    ranks = data.groupby(date)[signal].rank(method="first")
    sizes = data.groupby(date)[signal].transform("size")
    data = data.assign(q=np.ceil(ranks * n / sizes).astype(int).clip(1, n))
    if weight:
        w = data[weight].clip(lower=0)
        num = (data[ret] * w).groupby([data[date], data["q"]]).sum()
        den = w.groupby([data[date], data["q"]]).sum()
        port = (num / den).unstack("q")
    else:
        port = data.groupby([date, "q"])[ret].mean().unstack("q")
    port.columns = [int(c) for c in port.columns]
    port["long_short"] = port[n] - port[1]
    port.columns.name = None
    return port


def performance_summary(
    returns: pd.Series | pd.DataFrame, periods_per_year: int = 252
) -> pd.DataFrame:
    """Annualized return, volatility, Sharpe ratio (zero risk-free rate), max drawdown, hit rate."""
    frame = returns.to_frame() if isinstance(returns, pd.Series) else returns
    rows = {}
    for name, r in frame.items():
        r = r.dropna()
        if r.empty:
            continue
        wealth = (1 + r).cumprod()
        years = len(r) / periods_per_year
        ann_ret = wealth.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
        vol = r.std(ddof=1) * np.sqrt(periods_per_year)
        rows[name] = {
            "ann_return": ann_ret,
            "ann_vol": vol,
            "sharpe": r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year)
            if r.std(ddof=1) > 0
            else np.nan,
            "max_drawdown": (wealth / wealth.cummax() - 1).min(),
            "hit_rate": (r > 0).mean(),
            "n_periods": len(r),
        }
    return pd.DataFrame(rows).T
