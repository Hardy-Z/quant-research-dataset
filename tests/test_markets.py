from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import quant_research_dataset as qrd
from quant_research_dataset.adapters.us_fundamentals import available_date
from quant_research_dataset.errors import QRDError
from quant_research_dataset.markets.us import interpolate_zero_rate


def test_common_only_screen(local: Path) -> None:
    everything = qrd.load("us_stock_daily")
    common = qrd.load("us_stock_daily", common_only=True)
    assert set(everything["permno"]) == {10001, 10002, 10003}
    assert set(common["permno"]) == {10001, 10002}  # 10003 is an ETF


def test_get_prices_dispatch(local: Path) -> None:
    assert set(qrd.get_prices(start="2020-01-01", common_only=True)["permno"]) == {10001, 10002}
    assert set(qrd.get_prices(market="cn_hk")["symbol"]) == {"600001.SS", "000002.SZ"}
    with pytest.raises(QRDError, match="no price dataset"):
        qrd.get_prices(market="mars")


def test_csi300_shortcuts(local: Path) -> None:
    stocks = qrd.cn_hk.get_csi300_stocks()
    assert list(stocks.columns) == ["symbol", "name", "industry", "has_prices"]
    assert len(stocks) == 3
    px = qrd.cn_hk.get_csi300_prices("600001.SS", start="2020-01-01")
    assert px["close"].tolist() == [10.6]
    assert qrd.load("hs300_stock_daily").shape[0] == 3


def test_get_stock_daily_by_ticker(local: Path) -> None:
    df = qrd.get_stock_daily(tickers="AAA", columns=["date", "permno"])
    assert set(df["permno"]) == {10001}


def test_point_in_time_fundamentals(local: Path) -> None:
    q = qrd.get_fundamentals("quarterly")
    q = q.set_index(["gvkey", "datadate"])
    # report date used when present
    assert q.loc[("001000", pd.Timestamp("2019-09-30")), "available_date"] == pd.Timestamp(
        "2019-10-30"
    )
    # otherwise period end + 90 days
    assert q.loc[("001000", pd.Timestamp("2019-12-31")), "available_date"] == pd.Timestamp(
        "2020-03-30"
    )
    a = qrd.get_fundamentals("annual", lag_days=10)
    assert (a["available_date"] - a["datadate"]).dt.days.eq(10).all()
    raw = qrd.get_fundamentals("annual", point_in_time=False)
    assert "available_date" not in raw.columns
    with pytest.raises(QRDError):
        qrd.get_fundamentals("monthly")  # type: ignore[arg-type]


def test_available_date_without_rdq() -> None:
    df = pd.DataFrame({"datadate": pd.to_datetime(["2020-12-31"])})
    assert available_date(df, "annual").iloc[0] == pd.Timestamp("2021-06-29")


def test_merge_fundamentals_is_point_in_time(local: Path) -> None:
    prices = qrd.load("us_stock_daily", columns=["date", "permno", "gvkey", "ret"])
    fund = qrd.get_fundamentals("quarterly", columns=["gvkey", "datadate", "permno", "atq"])
    merged = qrd.merge_fundamentals(prices, fund)
    assert "permno_fund" not in merged.columns  # the stock's own permno is kept
    a = merged[merged.permno == 10001].set_index("date")
    # gvkey 001000 Q3 2019 became public 2019-10-30; Q4 only on 2020-03-30
    assert (a["atq"] == 100.0).all()
    b = merged[merged.permno == 10002].set_index("date")
    # gvkey 002000 reported on 2019-11-05, but its link to 10002 starts on 2019-12-31
    assert np.isnan(b.loc["2019-12-30", "atq"])
    assert b["atq"].iloc[1:].eq(50.0).all()
    assert b["gvkey"].iloc[1:].eq("002000").all()
    assert merged[merged.permno == 10003]["atq"].isna().all()  # no link
    assert len(merged) == len(prices)


def test_merge_fundamentals_requires_available_date(local: Path) -> None:
    prices = qrd.load("us_stock_daily", columns=["date", "permno", "gvkey"])
    fund = qrd.get_fundamentals(
        "quarterly", point_in_time=False, columns=["gvkey", "datadate", "atq"]
    )
    with pytest.raises(QRDError, match="available_date"):
        qrd.merge_fundamentals(prices, fund)
    with pytest.raises(QRDError, match="gvkey"):
        qrd.merge_fundamentals(prices.drop(columns="gvkey"), qrd.get_fundamentals("quarterly"))


def test_option_derived_fields_and_market(local: Path) -> None:
    df = qrd.get_spx_options("2019-12-31", with_market=True)
    assert len(df) == 2
    call = df[df.cp_flag == "C"].iloc[0]
    assert call["mid"] == 10.5 and call["spread"] == 1.0 and call["dte"] == 17
    assert call["spot"] == pytest.approx(3230.78)
    assert call["moneyness"] == pytest.approx(3200 / 3230.78)
    # 17 days between the 10d (1.0%) and 100d (2.0%) points
    assert call["rate"] == pytest.approx((1.0 + (17 - 10) / 90 * 1.0) / 100)
    assert len(qrd.get_spx_options("2019-12-31", cp_flag="P")) == 1
    assert len(qrd.get_spx_options("2019-12-31", max_dte=30)) == 1
    plain = qrd.load("spx_options", derived=False)
    assert "mid" not in plain.columns


def test_zero_rate_interpolation_is_flat_outside_grid() -> None:
    curve = pd.DataFrame(
        {"date": pd.to_datetime(["2020-01-02"] * 2), "days": [10, 100], "rate": [1.0, 2.0]}
    )
    out = interpolate_zero_rate(
        curve,
        pd.Series(pd.to_datetime(["2020-01-02"] * 3 + ["2020-01-03"])),
        np.array([1, 55, 500, 30]),
    )
    assert out[:3] == pytest.approx([0.01, 0.015, 0.02])
    assert np.isnan(out[3])  # no curve that day


def test_zero_rate_from_store(local: Path) -> None:
    assert qrd.zero_rate(["2020-01-02"], [100])[0] == pytest.approx(0.025)


def test_vol_surface_grid_filter(local: Path) -> None:
    df = qrd.get_vol_surface("2019-12-31", "2019-12-31", days=30, delta=50, cp_flag="C")
    assert df["impl_volatility"].tolist() == [0.12]


def test_duckdb_views(local: Path) -> None:
    con = qrd.duckdb_connect(["us_stock_daily", "usd_zero_curve"])
    n = con.sql("select count(*) from us_stock_daily").fetchall()[0][0]
    assert n == 12
    con = qrd.duckdb_connect({"px": "us_stock_daily"}, start="2020-01-01")
    assert con.sql("select count(*) from px").fetchall()[0][0] == 6
