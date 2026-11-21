# Changelog

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
