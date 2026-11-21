# Data dictionary

Generated from the dataset registry by `qrd docs`. Do not edit by hand.

| Dataset | Title | Frequency | Source |
|---|---|---|---|
| [`cn_hk/equity/ah_pairs`](#cn_hkequityah_pairs) | A/H dual-listed share pairs | static | Eastmoney A/H comparison board |
| [`cn_hk/equity/daily_bars`](#cn_hkequitydaily_bars) | China A-share and Hong Kong H-share daily bars | daily | Yahoo Finance (via yfinance) |
| [`cn_hk/fx/daily`](#cn_hkfxdaily) | CNY/HKD and USD/HKD daily exchange rates | daily | Yahoo Finance (via yfinance) |
| [`us/equity/ccm_link`](#usequityccm_link) | CRSP/Compustat merged link table | static | CRSP/Compustat Merged (CCM) database via WRDS |
| [`us/equity/crsp_daily`](#usequitycrsp_daily) | CRSP daily stock file | daily | CRSP US Stock Database, CIZ (v2) format, via WRDS |
| [`us/etf/bars_1min`](#usetfbars_1min) | US ETF 1-minute bars | intraday | Alpaca Markets historical stock bars (SIP feed) |
| [`us/etf/bars_5min`](#usetfbars_5min) | US ETF 5-minute bars | intraday | Alpaca Markets historical stock bars (SIP feed) |
| [`us/etf/daily_bars`](#usetfdaily_bars) | US ETF daily bars | daily | Alpaca Markets historical stock bars (SIP feed) |
| [`us/fundamentals/compustat_annual`](#usfundamentalscompustat_annual) | Compustat annual fundamentals | annual | S&P Compustat North America `comp.funda` via WRDS |
| [`us/fundamentals/compustat_quarterly`](#usfundamentalscompustat_quarterly) | Compustat quarterly fundamentals | quarterly | S&P Compustat North America `comp.fundq` via WRDS |
| [`us/index/spx_daily`](#usindexspx_daily) | S&P 500 index daily prices | daily | OptionMetrics IvyDB US `secprd` (Security Prices), SPX, via WRDS |
| [`us/options/spx_option_prices`](#usoptionsspx_option_prices) | SPX index option prices, implied volatility and greeks | daily | OptionMetrics IvyDB US `opprcd` (Option Prices), SPX (secid 108105), via WRDS |
| [`us/options/spx_vol_surface`](#usoptionsspx_vol_surface) | SPX standardized volatility surface | daily | OptionMetrics IvyDB US `vsurfd` (Volatility Surface), SPX, via WRDS |
| [`us/rates/zero_curve`](#usrateszero_curve) | USD zero-coupon yield curve | daily | OptionMetrics IvyDB US `zerocd` (Zero Coupon Yield Curve), via WRDS |

## Market: `cn_hk`

### `cn_hk/equity/ah_pairs`: A/H dual-listed share pairs

Companies with both an A-share line (Shanghai or Shenzhen, in CNY) and an H-share line (Hong Kong, in HKD), with the Yahoo Finance symbol of each.

**Source:** Eastmoney A/H comparison board  
**License:** Public listing information  
**Frequency:** static  
**Keys:** id `a_symbol`, date `-`  
**Aliases:** `ah_pairs`, `ah_pairs`

**Coverage:** 100 rows, 100 distinct `a_symbol`, 0.0 MB in 1 file(s).


| Column | Type | Unit | Description |
|---|---|---|---|
| `a_symbol` | string |  | A-share Yahoo symbol (.SS or .SZ) |
| `h_symbol` | string |  | H-share Yahoo symbol (.HK) |
| `name` | string |  | Company name (Chinese) |

### `cn_hk/equity/daily_bars`: China A-share and Hong Kong H-share daily bars

Daily prices for the A-share and H-share lines of about 100 companies dual listed in Shanghai/Shenzhen and Hong Kong. Pair the two lines with cn_hk/equity/ah_pairs.

**Source:** Yahoo Finance (via yfinance)  
**License:** Yahoo Finance terms of service  
**Frequency:** daily  
**Keys:** id `symbol`, date `date`  
**Aliases:** `daily_bars`, `ah_daily`

**Coverage:** 2014-01-02 to 2026-11-20, 606,826 rows, 239 distinct `symbol`, 8.6 MB in 1 file(s).


**Notes**

- Symbols use Yahoo suffixes: .SS = Shanghai, .SZ = Shenzhen, .HK = Hong Kong.
- A shares are quoted in CNY and H shares in HKD; use cn_hk/fx/daily to convert.
- adj_close is adjusted for splits and dividends; open and close are not.

| Column | Type | Unit | Description |
|---|---|---|---|
| `symbol` | string |  | Yahoo Finance symbol |
| `date` | date32 |  | Trading date (local exchange) |
| `open` | float64 | local currency | Open |
| `close` | float64 | local currency | Close |
| `adj_close` | float64 | local currency | Close adjusted for splits and dividends |
| `volume` | float64 | shares | Volume |

### `cn_hk/fx/daily`: CNY/HKD and USD/HKD daily exchange rates

Daily exchange rates used to put A shares (CNY) and H shares (HKD) on the same currency.

**Source:** Yahoo Finance (via yfinance)  
**License:** Yahoo Finance terms of service  
**Frequency:** daily  
**Keys:** id `symbol`, date `date`  
**Aliases:** `daily`, `cnhk_fx`

**Coverage:** 2014-01-01 to 2026-11-20, 6,711 rows, 2 distinct `symbol`, 0.1 MB in 1 file(s).


**Notes**

- CNYHKD=X is HKD per 1 CNY; HKD=X is HKD per 1 USD.

| Column | Type | Unit | Description |
|---|---|---|---|
| `symbol` | string |  | Yahoo Finance symbol |
| `date` | date32 |  | Date |
| `open` | float64 |  | Open rate |
| `close` | float64 |  | Close rate |

## Market: `us`

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

### `us/etf/bars_1min`: US ETF 1-minute bars

1-minute open and close for SPY, QQQ and IWM during regular trading hours (09:30-16:00 New York time), adjusted for splits and dividends.

**Source:** Alpaca Markets historical stock bars (SIP feed)  
**License:** Alpaca market data terms  
**Frequency:** intraday  
**Keys:** id `symbol`, date `timestamp`  
**Aliases:** `bars_1min`, `etf_1min`

**Coverage:** 2016-01-04 to 2026-09-25, 3,150,459 rows, 3 distinct `symbol`, 24.6 MB in 11 file(s).


**Notes**

- timestamp is the bar open time in UTC.
- Known gaps: QQQ has a single bar on 2018-05-02 and 2018-05-03; on 2020-03-09/12/16/18, 14 bars are missing (market-wide circuit-breaker halts).
- Early-close days (day after Thanksgiving, Christmas Eve, July 3) include bars after the 13:00 close.

| Column | Type | Unit | Description |
|---|---|---|---|
| `symbol` | string |  | Ticker |
| `timestamp` | timestamp[us, UTC] |  | Bar open time (UTC) |
| `open` | float64 | USD | Open (adjusted) |
| `close` | float64 | USD | Close (adjusted) |

### `us/etf/bars_5min`: US ETF 5-minute bars

5-minute OHLCV bars for SPY during regular trading hours (09:30-16:00 New York time), adjusted for splits and dividends.

**Source:** Alpaca Markets historical stock bars (SIP feed)  
**License:** Alpaca market data terms  
**Frequency:** intraday  
**Keys:** id `symbol`, date `timestamp`  
**Aliases:** `bars_5min`, `etf_5min`

**Coverage:** 2016-01-04 to 2026-09-25, 210,387 rows, 1 distinct `symbol`, 4.3 MB in 11 file(s).


**Notes**

- timestamp is the bar open time in UTC. Convert with df.timestamp.dt.tz_convert('America/New_York').

| Column | Type | Unit | Description |
|---|---|---|---|
| `symbol` | string |  | Ticker |
| `timestamp` | timestamp[us, UTC] |  | Bar open time (UTC) |
| `open` | float64 | USD | Open (adjusted) |
| `high` | float64 | USD | High (adjusted) |
| `low` | float64 | USD | Low (adjusted) |
| `close` | float64 | USD | Close (adjusted) |
| `volume` | float64 | shares | Volume (adjusted) |

### `us/etf/daily_bars`: US ETF daily bars

Daily bars for liquid US ETFs (SPY, QQQ, IWM, TLT, IEF, GLD), adjusted for splits and dividends. Useful as benchmarks and for cross-asset studies.

**Source:** Alpaca Markets historical stock bars (SIP feed)  
**License:** Alpaca market data terms  
**Frequency:** daily  
**Keys:** id `symbol`, date `date`  
**Aliases:** `daily_bars`, `etf_daily`

**Coverage:** 2016-01-04 to 2026-09-25, 16,188 rows, 6 distinct `symbol`, 0.2 MB in 1 file(s).


**Notes**

- SPY, QQQ and IWM have open and close only; high, low and volume are null for them.
- Prices are split and dividend adjusted, so close-to-close changes are total returns.

| Column | Type | Unit | Description |
|---|---|---|---|
| `symbol` | string |  | Ticker |
| `date` | date32 |  | Trading date |
| `open` | float64 | USD | Open (adjusted) |
| `high` | float64 | USD | High (adjusted) |
| `low` | float64 | USD | Low (adjusted) |
| `close` | float64 | USD | Close (adjusted) |
| `volume` | float64 | shares | Volume (adjusted) |

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
