# Changelog

## Unreleased

* New datasets `cn_hk/equity/csi300_stock_daily` (adjusted daily prices of the
  810 stocks that have been in the CSI 300, 2006 to March 2025) and
  `cn_hk/equity/csi300_stocks` (names and Shenwan industries), from the
  MIT-licensed FinMultiTime release; `scripts/fetch_csi300.py` downloads the source.
* Shortcuts `qrd.cn_hk.get_csi300_prices` and `get_csi300_stocks`.
* Build: string dates with a time and UTC offset keep their local calendar date.

## 0.1.0 (unreleased)

First release.

* Generic API: `load`, `list_datasets`, `describe`, `download`, `files_for`.
* YAML dataset registry with typed schemas, units and descriptions; generated
  data dictionary and Hugging Face dataset card.
* Storage backends: Hugging Face Hub (gated or private repos) and local folders.
* Build pipeline from raw vendor files to partitioned Parquet with a
  checksummed manifest; `qrd verify` and `qrd publish`.
* 13 datasets, named by content (source kept as metadata): US stock daily,
  US fundamentals quarterly/annual, SPX option prices and
  vol surface, SPX index, USD zero curve, US ETF bars (1d, 5m, 1m), China A/H
  daily bars, A/H pairs, CNY/HKD FX.
* Stock-company links are applied at build time: stock rows carry `gvkey` and
  fundamentals carry `permno` (primary share class).
* US helpers: common-stock screen, point-in-time fundamentals,
  `merge_fundamentals`, option chains with spot, rates and moneyness.
* China/HK helpers: A/H premium.
* Research helpers: quantile portfolio sorts, performance summary.
* SQL access through DuckDB.
