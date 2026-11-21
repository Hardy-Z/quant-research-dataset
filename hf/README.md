---
pretty_name: Quant Research Dataset
license: other
license_name: vendor-terms
language:
- en
tags:
- finance
- stocks
- options
- fundamentals
- time-series
- quantitative-finance
size_categories:
- 10M<n<100M
configs:
- config_name: us__equity__ccm_link
  data_files: us/equity/ccm_link/**/*.parquet
- config_name: us__equity__crsp_daily
  data_files: us/equity/crsp_daily/**/*.parquet
- config_name: us__fundamentals__compustat_annual
  data_files: us/fundamentals/compustat_annual/**/*.parquet
- config_name: us__fundamentals__compustat_quarterly
  data_files: us/fundamentals/compustat_quarterly/**/*.parquet
- config_name: us__index__spx_daily
  data_files: us/index/spx_daily/**/*.parquet
- config_name: us__options__spx_option_prices
  data_files: us/options/spx_option_prices/**/*.parquet
- config_name: us__options__spx_vol_surface
  data_files: us/options/spx_vol_surface/**/*.parquet
- config_name: us__rates__zero_curve
  data_files: us/rates/zero_curve/**/*.parquet
extra_gated_prompt: Parts of this dataset are licensed from data vendors (CRSP, S&P Compustat, OptionMetrics, via WRDS). Access is granted for non-commercial academic research only, and only to people who confirm they may use these sources.
extra_gated_fields:
  Full name: text
  Affiliation (university or company): text
  Intended use: text
  I have, or my institution has, a current WRDS subscription covering CRSP, Compustat and OptionMetrics: checkbox
  I will not redistribute the data: checkbox
---

# Quant Research Dataset

Research-grade market data in one place, organized as `market/asset_class/dataset`
and stored as partitioned Parquet. Version `2025.12`.

The companion Python package [`quant-research-dataset`](https://github.com/Hardy-Z/quant-research-dataset)
downloads only the partitions a query needs:

```python
import quant_research_dataset as qrd

qrd.list_datasets()
crsp = qrd.load(
    "us/equity/crsp_daily",
    start="2024-01-01",
    end="2024-12-31",
    columns=["date", "permno", "ret", "mktcap"],
    common_only=True,
)
```

## Datasets

| Dataset | Title | Start | End | Rows |
|---|---|---|---|---|
| `us/equity/ccm_link` | CRSP/Compustat merged link table | - | - | 39,770 |
| `us/equity/crsp_daily` | CRSP daily stock file | 2015-01-02 | 2025-12-31 | 23,101,820 |
| `us/fundamentals/compustat_annual` | Compustat annual fundamentals | 2000-01-31 | 2026-10-31 | 254,888 |
| `us/fundamentals/compustat_quarterly` | Compustat quarterly fundamentals | 2000-01-31 | 2026-11-30 | 1,051,636 |
| `us/index/spx_daily` | S&P 500 index daily prices | 2015-08-31 | 2025-08-29 | 2,515 |
| `us/options/spx_option_prices` | SPX index option prices, implied volatility and greeks | 2015-08-31 | 2025-08-29 | 34,332,875 |
| `us/options/spx_vol_surface` | SPX standardized volatility surface | 2015-08-31 | 2025-08-29 | 940,610 |
| `us/rates/zero_curve` | USD zero-coupon yield curve | 2015-08-31 | 2025-08-29 | 81,588 |

## Layout

```
<market>/<asset_class>/<dataset>/year=YYYY[/month=MM]/part-0.parquet
<market>/<asset_class>/<dataset>/data.parquet      # small, unpartitioned tables
manifest.json                                      # files, row counts, SHA-256, date ranges
```

## License and access

The code is MIT licensed. The data is not: each dataset keeps the terms of its
vendor (see the table below and `describe()` in the package). Access is gated
and approved by hand. Do not redistribute the files.

## Data dictionary

### `us/equity/ccm_link`: CRSP/Compustat merged link table

Maps Compustat companies (gvkey) to CRSP securities (permno) over time. Use it to join fundamentals to prices; qrd.link_crsp_compustat() applies the standard link filters for you.

**Source:** CRSP/Compustat Merged (CCM) database via WRDS  
**License:** WRDS / CRSP subscription terms  
**Frequency:** static  
**Keys:** id `gvkey`, date `-`  
**Aliases:** `ccm_link`, `ccm`, `ccmxpf_linktable`

**Coverage:** 39,770 rows, 34,761 distinct `gvkey`, 1.4 MB in 1 file(s).


**Notes**

- linkenddt is null while a link is still active (CRSP writes 'E').
- Standard filter: linktype in (LC, LU) and linkprim in (P, C).

| Column | Type | Unit | Description |
|---|---|---|---|
| `gvkey` | string |  | Compustat company key (6 digits |
| `permno` | int32 |  | Linked CRSP PERMNO |
| `permco` | int32 |  | Linked CRSP PERMCO |
| `liid` | string |  | Compustat issue id of the linked security |
| `linktype` | string |  | Link type: LC=confirmed, LU=unconfirmed but usable, others are weaker |
| `linkprim` | string |  | Primary link marker: P=primary, C=primary per CRSP, J/N=secondary |
| `linkdt` | date32 |  | First date the link is valid |
| `linkenddt` | date32 |  | Last date the link is valid (null = still active) |
| `conm` | string |  | Company name |
| `tic` | string |  | Compustat ticker |
| `cusip` | string |  | Compustat CUSIP (9 characters) |

### `us/equity/crsp_daily`: CRSP daily stock file

Daily prices, returns, volume and shares outstanding for every US-listed security in CRSP, including delisted ones (no survivorship bias). Returns already include delisting returns on the delisting day, as in the CIZ format. Also carries the CRSP value-weighted market return and the S&P 500 return.

**Source:** CRSP US Stock Database, CIZ (v2) format, via WRDS  
**License:** WRDS / CRSP subscription terms  
**Frequency:** daily  
**Keys:** id `permno`, date `date`  
**Aliases:** `crsp_daily`, `crsp`, `crsp_dsf`

**Coverage:** 2015-01-02 to 2025-12-31, 23,101,820 rows, 16,915 distinct `permno`, 852.0 MB in 11 file(s).


**Notes**

- Use load(..., common_only=True) for the standard ordinary-common-stock universe.
- Tickers are reused over time; filter by permno for stable identity.
- mktcap and shrout are in thousands (of dollars and shares).

| Column | Type | Unit | Description |
|---|---|---|---|
| `date` | date32 |  | Trading date |
| `permno` | int32 |  | CRSP permanent security identifier |
| `permco` | int32 |  | CRSP permanent company identifier |
| `ticker` | string |  | Ticker symbol on this date |
| `cusip` | string |  | 8-character CUSIP on this date |
| `hdr_cusip` | string |  | Most recent (header) CUSIP |
| `siccd` | string |  | Standard Industrial Classification code |
| `primary_exch` | string |  | Primary exchange: N=NYSE, A=NYSE American, Q=Nasdaq, R=NYSE Arca, B=Cboe BZX, X=other, I=IEX |
| `share_type` | string |  | Share type: NS=ordinary shares, AD=ADR, SB=shares of beneficial interest, UG=units |
| `security_type` | string |  | Security type: EQTY=equity, FUND=fund |
| `security_sub_type` | string |  | Sub type: COM=common stock, ETF, CEF=closed-end fund |
| `issuer_type` | string |  | Issuer type: CORP, ACOR (asset-backed corporation), REIT |
| `us_inc_flg` | string |  | Y if incorporated in the US |
| `conditional_type` | string |  | Trading condition: RW=regular way, NW=when-issued, NT=not trading |
| `trading_status_flg` | string |  | Trading status: A=active, H=halted, S=suspended, D=delisted, X=unknown |
| `delist_flg` | string |  | Y on the delisting day |
| `open` | float64 | USD | Opening price |
| `high` | float64 | USD | High price |
| `low` | float64 | USD | Low price |
| `close` | float64 | USD | Closing price (null if no trade) |
| `prc` | float64 | USD | CRSP price: close, or bid/ask midpoint when there was no trade (see prc_flg) |
| `prc_flg` | string |  | Price source: TR=trade, BA=bid/ask average, others are special cases |
| `bid` | float64 | USD | Closing bid |
| `ask` | float64 | USD | Closing ask |
| `volume` | int64 | shares | Share volume |
| `num_trd` | int64 |  | Number of trades |
| `ret` | float64 | decimal | Total return including dividends (and the delisting return on the delisting day) |
| `retx` | float64 | decimal | Return excluding dividends |
| `ret_miss_flg` | string |  | Reason a return is missing; NA when the return is present |
| `shrout` | int64 | thousand shares | Shares outstanding |
| `mktcap` | float64 | thousand USD | Market capitalization (abs(prc) x shrout) |
| `fac_prc` | float64 |  | Factor to adjust price for this day's distribution |
| `cum_fac_pr` | float64 |  | Cumulative price adjustment factor |
| `vwretd` | float64 | decimal | CRSP value-weighted market return incl. dividends |
| `sprtrn` | float64 | decimal | S&P 500 index return |

### `us/fundamentals/compustat_annual`: Compustat annual fundamentals

Annual financial statement items for North American companies, active and inactive, in the standard industrial format (indfmt=INDL, datafmt=STD, consol=C). Values are as reported in the company's currency (curcd).

**Source:** S&P Compustat North America `comp.funda` via WRDS  
**License:** WRDS / S&P Compustat subscription terms  
**Frequency:** annual  
**Keys:** id `gvkey`, date `datadate`  
**Aliases:** `compustat_annual`, `funda`, `compustat_a`

**Coverage:** 2000-01-31 to 2026-10-31, 254,888 rows, 27,908 distinct `gvkey`, 29.5 MB in 1 file(s).


**Notes**

- datadate is the fiscal period end, not the date the numbers were public. Use load(..., point_in_time=True) for an available_date column.
- Join to CRSP with qrd.link_crsp_compustat() or qrd.merge_fundamentals().

| Column | Type | Unit | Description |
|---|---|---|---|
| `gvkey` | string |  | Compustat company key (6 digits, zero padded) |
| `datadate` | date32 |  | Fiscal period end date |
| `costat` | string |  | Company status: A=active, I=inactive |
| `curcd` | string |  | ISO currency of reported values |
| `datafmt` | string |  | Data format (STD = standardized) |
| `indfmt` | string |  | Industry format (INDL = industrial) |
| `consol` | string |  | Consolidation level (C = consolidated) |
| `tic` | string |  | Ticker |
| `conm` | string |  | Company name |
| `cusip` | string |  | CUSIP (9 characters) |
| `cik` | string |  | SEC Central Index Key |
| `exchg` | int64 |  | Stock exchange code |
| `fyr` | int64 |  | Fiscal year-end month |
| `fic` | string |  | Country of incorporation (ISO) |
| `gind` | string |  | GICS industry |
| `gsector` | string |  | GICS sector |
| `loc` | string |  | Country of headquarters (ISO) |
| `naics` | string |  | NAICS industry code |
| `sic` | string |  | SIC industry code |
| `ajex` | float64 |  | Cumulative adjustment factor (ex-date) |
| `fyear` | int64 |  | Fiscal year |
| `act` | float64 | million (reporting currency) | Current assets, total |
| `at` | float64 | million (reporting currency) | Total assets |
| `ceq` | float64 | million (reporting currency) | Common equity, total |
| `che` | float64 | million (reporting currency) | Cash and short-term investments |
| `dlc` | float64 | million (reporting currency) | Debt in current liabilities |
| `dltt` | float64 | million (reporting currency) | Long-term debt, total |
| `intan` | float64 | million (reporting currency) | Intangible assets, total |
| `invt` | float64 | million (reporting currency) | Inventories, total |
| `lct` | float64 | million (reporting currency) | Current liabilities, total |
| `lt` | float64 | million (reporting currency) | Total liabilities |
| `mib` | float64 | million (reporting currency) | Noncontrolling interest (balance sheet) |
| `ppent` | float64 | million (reporting currency) | Property, plant and equipment, net |
| `pstk` | float64 | million (reporting currency) | Preferred stock, par value |
| `pstkl` | float64 | million (reporting currency) | Preferred stock, liquidating value |
| `pstkrv` | float64 | million (reporting currency) | Preferred stock, redemption value |
| `rect` | float64 | million (reporting currency) | Receivables, total |
| `seq` | float64 | million (reporting currency) | Stockholders' equity, parent |
| `txditc` | float64 | million (reporting currency) | Deferred taxes and investment tax credit |
| `cogs` | float64 | million (reporting currency) | Cost of goods sold |
| `dp` | float64 | million (reporting currency) | Depreciation and amortization |
| `dvc` | float64 | million (reporting currency) | Dividends, common |
| `dvt` | float64 | million (reporting currency) | Dividends, total |
| `epsfx` | float64 | currency units per share | EPS, diluted, excl. extraordinary items |
| `epspx` | float64 | currency units per share | EPS, basic, excl. extraordinary items |
| `ib` | float64 | million (reporting currency) | Income before extraordinary items |
| `ni` | float64 | million (reporting currency) | Net income |
| `oiadp` | float64 | million (reporting currency) | Operating income after depreciation |
| `oibdp` | float64 | million (reporting currency) | Operating income before depreciation |
| `revt` | float64 | million (reporting currency) | Revenue, total |
| `sale` | float64 | million (reporting currency) | Sales (net) |
| `spi` | float64 | million (reporting currency) | Special items |
| `txt` | float64 | million (reporting currency) | Income taxes, total |
| `xint` | float64 | million (reporting currency) | Interest and related expense |
| `xrd` | float64 | million (reporting currency) | Research and development expense |
| `xsga` | float64 | million (reporting currency) | Selling, general and administrative expense |
| `capx` | float64 | million (reporting currency) | Capital expenditures |
| `dv` | float64 | million (reporting currency) | Cash dividends (cash flow statement) |
| `oancf` | float64 | million (reporting currency) | Net cash flow from operating activities |
| `prstkc` | float64 | million (reporting currency) | Purchase of common and preferred stock |
| `sstk` | float64 | million (reporting currency) | Sale of common and preferred stock |
| `csho` | float64 | million shares | Common shares outstanding |
| `emp` | float64 | thousand employees | Employees |
| `prcc_f` | float64 | currency units per share | Closing price at fiscal year end |

### `us/fundamentals/compustat_quarterly`: Compustat quarterly fundamentals

Quarterly financial statement items for North American companies, active and inactive, in the standard industrial format (indfmt=INDL, datafmt=STD, consol=C). Values are as reported in the company's currency (curcdq).

**Source:** S&P Compustat North America `comp.fundq` via WRDS  
**License:** WRDS / S&P Compustat subscription terms  
**Frequency:** quarterly  
**Keys:** id `gvkey`, date `datadate`  
**Aliases:** `compustat_quarterly`, `fundq`, `compustat_q`

**Coverage:** 2000-01-31 to 2026-11-30, 1,051,636 rows, 30,091 distinct `gvkey`, 96.5 MB in 1 file(s).


**Notes**

- Items ending in y (capxy, oancfy, ...) are fiscal year-to-date, not quarterly.
- datadate is the fiscal period end, not the date the numbers were public. Use load(..., point_in_time=True) for an available_date column.
- Join to CRSP with qrd.link_crsp_compustat() or qrd.merge_fundamentals().

| Column | Type | Unit | Description |
|---|---|---|---|
| `gvkey` | string |  | Compustat company key (6 digits, zero padded) |
| `datadate` | date32 |  | Fiscal period end date |
| `costat` | string |  | Company status: A=active, I=inactive |
| `curcdq` | string |  | ISO currency of reported values |
| `datafmt` | string |  | Data format (STD = standardized) |
| `indfmt` | string |  | Industry format (INDL = industrial) |
| `consol` | string |  | Consolidation level (C = consolidated) |
| `tic` | string |  | Ticker |
| `conm` | string |  | Company name |
| `cusip` | string |  | CUSIP (9 characters) |
| `cik` | string |  | SEC Central Index Key |
| `exchg` | int64 |  | Stock exchange code |
| `fyr` | int64 |  | Fiscal year-end month |
| `fic` | string |  | Country of incorporation (ISO) |
| `gind` | string |  | GICS industry |
| `gsector` | string |  | GICS sector |
| `loc` | string |  | Country of headquarters (ISO) |
| `naics` | string |  | NAICS industry code |
| `sic` | string |  | SIC industry code |
| `ajexq` | float64 |  | Cumulative adjustment factor (ex-date) |
| `datacqtr` | string |  | Calendar quarter, e.g. 2020Q1 |
| `datafqtr` | string |  | Fiscal quarter, e.g. 2020Q1 |
| `fqtr` | int64 |  | Fiscal quarter (1-4) |
| `fyearq` | int64 |  | Fiscal year |
| `rdq` | date32 |  | Report date of quarterly earnings (when the numbers became public) |
| `actq` | float64 | million (reporting currency) | Current assets, total |
| `atq` | float64 | million (reporting currency) | Total assets |
| `ceqq` | float64 | million (reporting currency) | Common equity, total |
| `cheq` | float64 | million (reporting currency) | Cash and short-term investments |
| `cogsq` | float64 | million (reporting currency) | Cost of goods sold |
| `cshoq` | float64 | million shares | Common shares outstanding |
| `cshprq` | float64 | million shares | Shares used to compute basic EPS |
| `dlcq` | float64 | million (reporting currency) | Debt in current liabilities |
| `dlttq` | float64 | million (reporting currency) | Long-term debt, total |
| `dpq` | float64 | million (reporting currency) | Depreciation and amortization |
| `epsfxq` | float64 | currency units per share | EPS, diluted, excl. extraordinary items |
| `epspxq` | float64 | currency units per share | EPS, basic, excl. extraordinary items |
| `ibq` | float64 | million (reporting currency) | Income before extraordinary items |
| `intanq` | float64 | million (reporting currency) | Intangible assets, total |
| `invtq` | float64 | million (reporting currency) | Inventories, total |
| `lctq` | float64 | million (reporting currency) | Current liabilities, total |
| `ltq` | float64 | million (reporting currency) | Total liabilities |
| `mibq` | float64 | million (reporting currency) | Noncontrolling interest (balance sheet) |
| `niq` | float64 | million (reporting currency) | Net income |
| `oiadpq` | float64 | million (reporting currency) | Operating income after depreciation |
| `oibdpq` | float64 | million (reporting currency) | Operating income before depreciation |
| `ppentq` | float64 | million (reporting currency) | Property, plant and equipment, net |
| `pstkq` | float64 | million (reporting currency) | Preferred stock, par value |
| `pstkrq` | float64 | million (reporting currency) | Preferred stock, redeemable |
| `rectq` | float64 | million (reporting currency) | Receivables, total |
| `revtq` | float64 | million (reporting currency) | Revenue, total |
| `saleq` | float64 | million (reporting currency) | Sales (net) |
| `seqq` | float64 | million (reporting currency) | Stockholders' equity, parent |
| `spiq` | float64 | million (reporting currency) | Special items |
| `txditcq` | float64 | million (reporting currency) | Deferred taxes and investment tax credit |
| `txtq` | float64 | million (reporting currency) | Income taxes, total |
| `xintq` | float64 | million (reporting currency) | Interest and related expense |
| `xrdq` | float64 | million (reporting currency) | Research and development expense |
| `xsgaq` | float64 | million (reporting currency) | Selling, general and administrative expense |
| `capxy` | float64 | million (reporting currency) | Capital expenditures, fiscal year to date |
| `dvy` | float64 | million (reporting currency) | Cash dividends (cash flow statement), fiscal year to date |
| `oancfy` | float64 | million (reporting currency) | Net cash flow from operating activities, fiscal year to date |
| `prstkcy` | float64 | million (reporting currency) | Purchase of common and preferred stock, fiscal year to date |
| `sstky` | float64 | million (reporting currency) | Sale of common and preferred stock, fiscal year to date |
| `dvpsxq` | float64 | currency units per share | Dividends per share by ex-date |
| `prccq` | float64 | currency units per share | Closing price at quarter end |

### `us/index/spx_daily`: S&P 500 index daily prices

Daily open, high, low and close of the S&P 500 index, aligned with the SPX option data (same calendar and source).

**Source:** OptionMetrics IvyDB US `secprd` (Security Prices), SPX, via WRDS  
**License:** WRDS / OptionMetrics subscription terms  
**Frequency:** daily  
**Keys:** id `-`, date `date`  
**Aliases:** `spx_daily`, `spx`, `secprd_spx`

**Coverage:** 2015-08-31 to 2025-08-29, 2,515 rows, 0.1 MB in 1 file(s).


| Column | Type | Unit | Description |
|---|---|---|---|
| `date` | date32 |  | Date |
| `open` | float64 | index points | Open |
| `high` | float64 | index points | High |
| `low` | float64 | index points | Low |
| `close` | float64 | index points | Close |
| `ret` | float64 | decimal | Daily price return |
| `secid` | int64 |  | OptionMetrics security id |
| `ticker` | string |  | Ticker |

### `us/options/spx_option_prices`: SPX index option prices, implied volatility and greeks

End-of-day best bid and offer, volume, open interest, implied volatility and greeks for every listed S&P 500 index option (standard AM-settled SPX and PM-settled SPXW weeklies). One row per option contract per day.

**Source:** OptionMetrics IvyDB US `opprcd` (Option Prices), SPX (secid 108105), via WRDS  
**License:** WRDS / OptionMetrics subscription terms  
**Frequency:** daily  
**Keys:** id `optionid`, date `date`  
**Aliases:** `spx_option_prices`, `spx_options`, `opprcd_spx`

**Coverage:** 2015-08-31 to 2025-08-29, 34,332,875 rows, 837,308 distinct `optionid`, 1,150.7 MB in 121 file(s).


**Notes**

- strike is in index points (OptionMetrics stores strike x 1000; it is divided here).
- load() adds mid, spread and dte (calendar days to expiry) by default; pass derived=False to skip.
- impl_volatility and greeks are null when OptionMetrics could not solve for them (e.g. deep ITM or no bid).
- Partitioned by month: a one-day query downloads one file of about 10 MB.
- The extract's root, suffix and forward_price fields were empty and are not included.

| Column | Type | Unit | Description |
|---|---|---|---|
| `date` | date32 |  | Quote date |
| `optionid` | int64 |  | OptionMetrics unique option identifier |
| `symbol` | string |  | Option symbol, e.g. SPXW 240315C5000000 (root SPX = AM-settled monthly, SPXW = PM-settled) |
| `exdate` | date32 |  | Expiration date |
| `cp_flag` | string |  | C = call, P = put |
| `strike` | float64 | index points | Strike price |
| `best_bid` | float64 | USD | Best closing bid across exchanges |
| `best_offer` | float64 | USD | Best closing offer across exchanges |
| `last_date` | date32 |  | Date of the last trade |
| `volume` | int64 | contracts | Contracts traded |
| `open_interest` | int64 | contracts | Open interest |
| `impl_volatility` | float64 | decimal (annualized) | Implied volatility |
| `delta` | float64 |  | Delta |
| `gamma` | float64 |  | Gamma |
| `vega` | float64 |  | Vega (price change per 1.00 change in volatility) |
| `theta` | float64 |  | Theta (annualized) |
| `am_settlement` | int64 |  | 1 if AM-settled (standard third-Friday SPX), 0 if PM-settled (SPXW) |
| `expiry_indicator` | string |  | OptionMetrics expiry flag: w = weekly, m = month-end, null = other (incl. standard monthly and Tuesday/Thursday dailies). Use am_settlement = 1 to pick standard monthly SPX expiries. |
| `ss_flag` | string |  | Settlement flag (0 = standard) |
| `symbol_flag` | string |  | Symbol format flag |
| `contract_size` | int64 |  | Contract multiplier |
| `cfadj` | float64 |  | Cumulative adjustment factor |
| `exercise_style` | string |  | E = European |
| `index_flag` | int64 |  | 1 if the underlying is an index |
| `issuer` | string |  | Underlying issuer name |
| `secid` | int64 |  | OptionMetrics security id of the underlying |

### `us/options/spx_vol_surface`: SPX standardized volatility surface

Daily interpolated implied volatility surface for SPX on a fixed grid of maturities (days) and deltas, built by OptionMetrics with a kernel smoother. Handy for constant-maturity IV, skew and term-structure studies.

**Source:** OptionMetrics IvyDB US `vsurfd` (Volatility Surface), SPX, via WRDS  
**License:** WRDS / OptionMetrics subscription terms  
**Frequency:** daily  
**Keys:** id `-`, date `date`  
**Aliases:** `spx_vol_surface`, `vol_surface`, `vsurfd_spx`

**Coverage:** 2015-08-31 to 2025-08-29, 940,610 rows, 19.1 MB in 11 file(s).


**Notes**

- delta is in percent: 50 = at-the-money; puts use negative deltas (-10 ... -90).

| Column | Type | Unit | Description |
|---|---|---|---|
| `date` | date32 |  | Date |
| `days` | int64 | calendar days | Maturity grid point |
| `delta` | int64 | percent | Delta grid point (negative for puts) |
| `cp_flag` | string |  | C = call, P = put |
| `impl_volatility` | float64 | decimal (annualized) | Interpolated implied volatility |
| `impl_strike` | float64 | index points | Strike implied by the delta and volatility |
| `impl_premium` | float64 | index points | Option premium implied by the surface |
| `dispersion` | float64 |  | Kernel-weighted dispersion of the input implied volatilities |
| `secid` | int64 |  | OptionMetrics security id of the underlying |

### `us/rates/zero_curve`: USD zero-coupon yield curve

Daily continuously compounded zero-coupon interest rates at a set of maturities, built by OptionMetrics from money-market and interest-rate futures prices. Used to discount option payoffs.

**Source:** OptionMetrics IvyDB US `zerocd` (Zero Coupon Yield Curve), via WRDS  
**License:** WRDS / OptionMetrics subscription terms  
**Frequency:** daily  
**Keys:** id `-`, date `date`  
**Aliases:** `zero_curve`, `zero_curve`, `zerocd`

**Coverage:** 2015-08-31 to 2025-08-29, 81,588 rows, 0.6 MB in 1 file(s).


**Notes**

- rate is in percent. qrd.zero_rate() interpolates it at any maturity.

| Column | Type | Unit | Description |
|---|---|---|---|
| `date` | date32 |  | Date |
| `days` | int64 | calendar days | Maturity |
| `rate` | float64 | percent (continuously compounded) | Zero-coupon rate |
