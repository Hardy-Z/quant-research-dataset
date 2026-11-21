from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_research_dataset import performance_summary, quantile_portfolios


def _panel(n_assets: int = 50, n_dates: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-01", periods=n_dates)
    rows = []
    for d in dates:
        signal = rng.normal(size=n_assets)
        rows.append(
            pd.DataFrame(
                {"date": d, "id": range(n_assets), "signal": signal, "ret": signal * 0.01, "w": 1.0}
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_quantile_portfolios_monotone() -> None:
    port = quantile_portfolios(_panel(), "signal", n=5)
    assert list(port.columns) == [1, 2, 3, 4, 5, "long_short"]
    assert (port.diff(axis=1).iloc[:, 1:5] > 0).all().all()  # higher signal -> higher return
    assert (port["long_short"] > 0).all()


def test_value_weighted_equals_equal_weighted_with_equal_weights() -> None:
    p = _panel()
    ew = quantile_portfolios(p, "signal", n=5)
    vw = quantile_portfolios(p, "signal", n=5, weight="w")
    pd.testing.assert_frame_equal(ew, vw)


def test_min_obs_skips_thin_dates() -> None:
    p = _panel(n_assets=10)
    assert quantile_portfolios(p, "signal", n=5, min_obs=20).empty


def test_performance_summary_known_values() -> None:
    r = pd.Series([0.01, -0.01] * 126)
    s = performance_summary(r).iloc[0]
    assert s["hit_rate"] == 0.5
    assert s["ann_vol"] == pytest.approx(r.std() * np.sqrt(252))
    assert s["n_periods"] == 252
    # wealth 1.1 -> 0.55 -> 1.1: a 50% drawdown, fully recovered
    assert performance_summary(pd.Series([0.1, -0.5, 1.0])).iloc[0][
        "max_drawdown"
    ] == pytest.approx(-0.5)
    flat = performance_summary(pd.Series([0.0, 0.0]))
    assert np.isnan(flat.iloc[0]["sharpe"])
