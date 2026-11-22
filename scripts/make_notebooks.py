"""Generate (and optionally execute) the example notebooks.

python scripts/make_notebooks.py                     # notebooks without outputs
QRD_DATA_DIR=prepared python scripts/make_notebooks.py --execute
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]

HUB_NOTE = """
# Data is read from the Hugging Face Hub by default (run `hf auth login` once).
# To use a local copy instead:  qrd.configure(data_dir="path/to/data")
pd.set_option("display.width", 140)"""

SETUP_QUICKSTART = (
    """\
import pandas as pd

import quant_research_dataset as qrd
"""
    + HUB_NOTE
)

SETUP_MOMENTUM = (
    """\
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import quant_research_dataset as qrd
"""
    + HUB_NOTE
)

QUICKSTART = [
    (
        "md",
        """\
# quant-research-dataset: quick tour

One API for every dataset: discover it, read its documentation, and load exactly the rows and columns you need.""",
    ),
    ("code", SETUP_QUICKSTART),
    ("md", "## 1. Discover"),
    ("code", 'qrd.list_datasets()[["id", "title", "frequency", "id_column", "date_column"]]'),
    (
        "code",
        """\
info = qrd.describe("us_stock_daily")
{k: info[k] for k in ("title", "rows", "start", "end", "n_ids", "size_mb", "load_options")}""",
    ),
    ("code", 'info["columns"].head(12)'),
    ("md", "## 2. US stocks: daily data by ticker or PERMNO"),
    (
        "code",
        """\
aapl = qrd.us.get_stock_daily(tickers="AAPL", start="2025-01-01",
                             columns=["date", "permno", "gvkey", "close", "ret", "mktcap"])
aapl.tail()""",
    ),
    (
        "md",
        """\
## 3. Point-in-time fundamentals

`available_date` is the earnings report date (`rdq`), so a backtest only sees numbers that were already public.""",
    ),
    (
        "code",
        """\
fund = qrd.get_fundamentals("quarterly", start="2024-01-01",
                            columns=["gvkey", "datadate", "rdq", "atq", "ceqq", "niq"])
merged = qrd.merge_fundamentals(aapl, fund)
merged[["date", "permno", "close", "datadate", "available_date", "ceqq", "niq"]].drop_duplicates("datadate")""",
    ),
    ("md", "## 4. SPX options: a full chain with spot, rates and moneyness"),
    (
        "code",
        """\
chain = qrd.get_spx_options("2024-03-15", with_market=True, min_dte=25, max_dte=40)
chain[["exdate", "cp_flag", "strike", "mid", "dte", "impl_volatility", "delta", "spot", "rate", "moneyness"]].head()""",
    ),
    (
        "code",
        """\
expiry = chain[chain.am_settlement == 1].exdate.min()  # the standard (AM-settled) monthly expiry
otm = chain[(chain.exdate == expiry)
            & (((chain.cp_flag == "P") & (chain.moneyness < 1)) | ((chain.cp_flag == "C") & (chain.moneyness >= 1)))]
otm = otm[otm.moneyness.between(0.75, 1.1)].sort_values("moneyness")
ax = otm.plot(x="moneyness", y="impl_volatility", marker=".", legend=False, figsize=(7, 3.5))
ax.set(title=f"SPX smile on 2024-03-15, expiry {expiry:%Y-%m-%d}", xlabel="strike / spot", ylabel="implied vol");""",
    ),
    ("md", "## 5. Volatility surface: 30-day at-the-money implied vol"),
    (
        "code",
        """\
atm = qrd.get_vol_surface(days=30, delta=50, cp_flag="C").set_index("date")["impl_volatility"]
ax = atm.plot(figsize=(9, 3.5), title="SPX 30-day ATM implied volatility")
ax.set_ylabel("implied vol");""",
    ),
    (
        "md",
        """\
## 6. Beyond the US: CSI 300 industries

The same API covers the China A-share stocks that have been in the CSI 300. Prices are
adjusted, so close-to-close changes are total returns. Days without trading (volume 0) are dropped.""",
    ),
    (
        "code",
        """\
stocks = qrd.cn_hk.get_csi300_stocks()
px = qrd.cn_hk.get_csi300_prices(start="2015-01-01", columns=["symbol", "date", "close", "volume"])
px = px[px.volume > 0].sort_values(["symbol", "date"])
px["ret"] = px.groupby("symbol").close.pct_change()
px = px.merge(stocks[["symbol", "industry"]], on="symbol")
names = {"银行": "Banks", "食品饮料": "Food & beverage", "电子": "Electronics", "医药生物": "Pharma & biotech"}
ind = px[px.industry.isin(names)].groupby(["date", "industry"]).ret.mean().unstack().rename(columns=names)
ax = (1 + ind.fillna(0)).cumprod().plot(figsize=(9, 3.5), logy=True,
                                         title="Equal-weighted CSI 300 stocks by industry (growth of 1)")
ax.set_ylabel("growth of 1");""",
    ),
    ("md", "## 7. SQL with DuckDB"),
    (
        "code",
        """\
con = qrd.duckdb_connect(["us_stock_daily"], start="2025-01-01", end="2025-12-31")
con.sql(\"\"\"
    select ticker, exp(sum(ln(1 + ret))) - 1 as ret_2025, max(mktcap) / 1e6 as max_mktcap_bn
    from us_stock_daily
    where share_type = 'NS' and security_sub_type = 'COM' and ret is not null
    group by ticker
    order by max_mktcap_bn desc
    limit 10
\"\"\").df()""",
    ),
]

MOMENTUM = [
    (
        "md",
        """\
# Cross-sectional momentum on US stocks, 2016-2025

A standard 12-1 momentum strategy (Jegadeesh and Titman, 1993) built from daily US stock data (`us_stock_daily`, sourced from CRSP) with `quant-research-dataset`:

* **Universe:** ordinary common stocks on NYSE, NYSE American and Nasdaq (`common_only=True`), excluding stocks below the NYSE 20th percentile of market cap.
* **Signal:** cumulative return from month t-12 to t-2, skipping the most recent month to avoid short-term reversal.
* **Portfolios:** value-weighted deciles, rebalanced monthly; long the winners (D10), short the losers (D1).

Returns are before trading costs.""",
    ),
    ("code", SETUP_MOMENTUM),
    ("md", "## Data: 11 years of daily US stock data in one call"),
    (
        "code",
        """\
daily = qrd.load("us_stock_daily", columns=["date", "permno", "ret", "mktcap", "primary_exch", "vwretd"],
                 common_only=True)
print(f"{len(daily):,} rows, {daily.permno.nunique():,} stocks, "
      f"{daily.date.min():%Y-%m-%d} to {daily.date.max():%Y-%m-%d}")""",
    ),
    ("md", "## Monthly returns and the 12-1 signal"),
    (
        "code",
        """\
daily["month"] = daily["date"].dt.to_period("M")
daily["logret"] = np.log1p(daily["ret"])
monthly = (daily.groupby(["permno", "month"])
           .agg(logret=("logret", "sum"), mktcap=("mktcap", "last"), exch=("primary_exch", "last"))
           .reset_index()
           .sort_values(["permno", "month"]))
monthly["ret"] = np.expm1(monthly["logret"])
monthly["m"] = monthly["month"].dt.year * 12 + monthly["month"].dt.month  # month number

g = monthly.groupby("permno")
monthly["lag_mktcap"] = g["mktcap"].shift(1)
monthly["lag_exch"] = g["exch"].shift(1)
# Sum of log returns over months t-12..t-2 (11 months), skipping month t-1.
monthly["mom"] = g["logret"].transform(lambda s: s.shift(2).rolling(11, min_periods=11).sum())

# Shifts above count rows; keep only rows where those rows are the right calendar months.
consecutive = (g["m"].shift(1) == monthly["m"] - 1) & (g["m"].shift(12) == monthly["m"] - 12)
panel = monthly[consecutive].copy()
panel[["permno", "month", "ret", "lag_mktcap", "mom"]].head()""",
    ),
    ("md", "## Size filter (NYSE 20th percentile) and decile sorts"),
    (
        "code",
        """\
nyse_p20 = panel[panel.lag_exch == "N"].groupby("month")["lag_mktcap"].quantile(0.2).rename("nyse_p20")
panel = panel.join(nyse_p20, on="month")
universe = panel[(panel.lag_mktcap >= panel.nyse_p20) & panel.mom.notna() & panel.ret.notna()]
print(f"{universe.month.nunique()} months, median {universe.groupby('month').size().median():.0f} stocks per month")

port = qrd.quantile_portfolios(universe, signal="mom", ret="ret", date="month", n=10, weight="lag_mktcap")
port.index = port.index.to_timestamp("M")
market = daily.drop_duplicates("date").groupby("month")["vwretd"].apply(lambda r: np.expm1(np.log1p(r).sum()))
market.index = market.index.to_timestamp("M")
port["market"] = market.reindex(port.index)
port.tail()""",
    ),
    ("md", "## Results"),
    (
        "code",
        """\
stats = qrd.performance_summary(port[[1, 5, 10, "long_short", "market"]], periods_per_year=12)
stats.style.format({"ann_return": "{:.1%}", "ann_vol": "{:.1%}", "sharpe": "{:.2f}",
                    "max_drawdown": "{:.1%}", "hit_rate": "{:.0%}", "n_periods": "{:.0f}"})""",
    ),
    (
        "code",
        """\
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
growth = (1 + port[[1, 10, "market"]]).cumprod().rename(columns={1: "losers (D1)", 10: "winners (D10)"})
growth.plot(ax=axes[0], title="Growth of $1, value-weighted deciles")
(1 + port["long_short"]).cumprod().plot(ax=axes[1], color="C3", title="Winners minus losers (D10 - D1)")
axes[1].axhline(1, color="grey", lw=0.8)
for ax in axes:
    ax.set_xlabel("")
fig.tight_layout()
fig.savefig("../docs/img/momentum.png", dpi=120)""",
    ),
    (
        "code",
        """\
yearly = port.groupby(port.index.year)[[10, 1, "long_short", "market"]].apply(lambda r: (1 + r).prod() - 1)
yearly.style.format("{:.1%}")""",
    ),
    (
        "md",
        """## Takeaways

* Over 2016-2025, past winners (D10) returned about 21% a year against 9% for past losers (D1). The winners-minus-losers spread earned about 5.5% a year, with 26% volatility (Sharpe 0.33) and a 39% maximum drawdown.
* The premium is far from steady. The spread lost heavily in 2016 and 2023, when beaten-down stocks led rebounds, and gained most in 2022 and 2024.
* The whole study (universe screen, monthly returns, size filter, value-weighted decile sorts, performance statistics) takes a few short cells, because data access, cleaning rules and portfolio helpers live in the library.
* Natural next steps: trading costs from bid-ask spreads (`bid`, `ask` are in the dataset), volatility scaling of the long-short leg, and robustness to the size cut-off.""",
    ),
]


def build(cells: list[tuple[str, str]]) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.cells = [
        nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src)
        for kind, src in cells
    ]
    return nb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--only", choices=["quickstart", "momentum"])
    args = parser.parse_args()
    (ROOT / "docs" / "img").mkdir(parents=True, exist_ok=True)
    for name, cells in {"quickstart": QUICKSTART, "momentum": MOMENTUM}.items():
        if args.only and name != args.only:
            continue
        nb = build(cells)
        if args.execute:
            from nbclient import NotebookClient

            client = NotebookClient(
                nb, timeout=1800, resources={"metadata": {"path": str(ROOT / "examples")}}
            )
            client.execute()
        path = ROOT / "examples" / f"{name}.ipynb"
        nbf.write(nb, path)
        print("wrote", path)


if __name__ == "__main__":
    main()
