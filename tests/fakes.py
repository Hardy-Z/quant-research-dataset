"""Synthetic raw files that mimic the vendor downloads.

The fake tree has the same paths, file formats and *raw* column names as the
real source folder, so tests exercise the real registry YAML end to end.
All values are made up.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from quant_research_dataset.registry import DatasetSpec, Registry

D = dt.date


def _filler(spec: DatasetSpec, name: str, n: int) -> list[Any]:
    typ = spec.column(name).type
    if typ == "string":
        return ["x"] * n
    if typ.startswith("int"):
        return [1] * n
    if typ.startswith("float"):
        return [1.0] * n
    if typ == "date32":
        return [D(2020, 1, 1)] * n
    raise AssertionError(f"no filler for {typ}")


def raw_table(
    spec: DatasetSpec, data: dict[str, list[Any]], drop: tuple[str, ...] = ()
) -> dict[str, list[Any]]:
    """Raw-named columns: ``data`` is keyed by *standard* names; others get fillers."""
    n = len(next(iter(data.values())))
    out: dict[str, list[Any]] = {}
    for col in spec.columns:
        if col.name in drop or col.derived:
            continue
        values = data[col.name] if col.name in data else _filler(spec, col.name, n)
        out[col.source_name] = values
    return out


def _parquet(
    path: Path, cols: dict[str, list[Any]], types: dict[str, pa.DataType] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {k: pa.array(v, type=(types or {}).get(k)) for k, v in cols.items()}
    pq.write_table(pa.table(arrays), path)


def _csv(path: Path, cols: dict[str, list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    as_text = {
        k: pa.array(["" if v is None else str(v) for v in vals], pa.string())
        for k, vals in cols.items()
    }
    pacsv.write_csv(pa.table(as_text), path, pacsv.WriteOptions(quoting_style="none"))


def _int_types(spec: DatasetSpec) -> dict[str, pa.DataType]:
    """Keep raw integer columns integer-typed (pa.array would infer int64 anyway)."""
    return {
        c.source_name: c.arrow_type
        for c in spec.columns
        if c.type in ("int32", "int64", "date32", "float64")
    }


def write_fake_source(root: Path, reg: Registry) -> Path:
    """Write the whole fake raw tree under ``root`` and return it."""
    # --- CRSP: 3 PERMNOs, 4 days spanning a year boundary --------------------
    crsp = reg.get("us/equity/stock_daily")
    days = [D(2019, 12, 30), D(2019, 12, 31), D(2020, 1, 2), D(2020, 1, 3)]
    rows = [(p, d) for p in (10001, 10002, 10003) for d in days]
    n = len(rows)
    data = {
        "permno": [p for p, _ in rows],
        "date": [d for _, d in rows],
        "ticker": [{10001: "AAA", 10002: "BBB", 10003: "ETF"}[p] for p, _ in rows],
        "ret": [0.01 * (i % 4) for i in range(n)],
        "close": [100.0 + i for i in range(n)],
        "mktcap": [1000.0 * (1 + i % 3) for i in range(n)],
        "share_type": ["NS"] * n,
        "security_type": [("FUND" if p == 10003 else "EQTY") for p, _ in rows],
        "security_sub_type": [("ETF" if p == 10003 else "COM") for p, _ in rows],
        "us_inc_flg": ["Y"] * n,
        "issuer_type": ["CORP"] * n,
        "primary_exch": ["Q"] * n,
        "conditional_type": ["RW"] * n,
        "trading_status_flg": ["A"] * n,
    }
    _parquet(
        root / "WRDS_data/crsp/crsp_daily_stock_2019-2020.parquet",
        raw_table(crsp, data),
        _int_types(crsp),
    )

    # --- CCM link table (raw CSV, LINKENDDT 'E' = active) --------------------
    _csv(
        root / "WRDS_data/crsp/ccm_link_table.csv",
        {
            "gvkey": ["001000", "002000", "003000"],
            "conm": ["A CORP", "B CORP", "OLD CORP"],
            "tic": ["E", "BBB", "OLD"],
            "cusip": ["000000001", "000000002", "000000003"],
            "LINKPRIM": ["P", "C", "P"],
            "LIID": ["01", "01", "01"],
            "LINKTYPE": ["LC", "LU", "LX"],  # LX is not a usable link type
            "LPERMNO": [10001, 10002, 10002],
            "LPERMCO": [1, 2, 2],
            "LINKDT": ["2000-01-01", "2019-12-31", "2000-01-01"],
            "LINKENDDT": ["E", "E", "2010-01-01"],
        },
    )

    # --- Compustat quarterly and annual --------------------------------------
    fundq = reg.get("us/fundamentals/quarterly")
    _parquet(
        root / "WRDS_data/compustat/compustat_fundq_quarterly_2019-2020.parquet",
        raw_table(
            fundq,
            {
                "gvkey": ["001000", "001000", "002000"],
                "datadate": [D(2019, 9, 30), D(2019, 12, 31), D(2019, 9, 30)],
                "rdq": [D(2019, 10, 30), None, D(2019, 11, 5)],
                "atq": [100.0, 110.0, 50.0],
                "fyearq": [2019, 2019, 2019],
            },
        ),
        _int_types(fundq),
    )
    funda = reg.get("us/fundamentals/annual")
    _parquet(
        root / "WRDS_data/compustat/compustat_funda_annual_2019-2020.parquet",
        raw_table(
            funda,
            {
                "gvkey": ["001000", "002000"],
                "datadate": [D(2018, 12, 31), D(2019, 12, 31)],
                "at": [90.0, 55.0],
                "fyear": [2018, 2019],
            },
        ),
        _int_types(funda),
    )

    # --- OptionMetrics -------------------------------------------------------
    opt = reg.get("us/options/spx_option_prices")
    _parquet(
        root / "WRDS_data/optionmetrics/optionm_opprcd_spx_option_prices_2019-2020.parquet",
        raw_table(
            opt,
            {
                "date": [D(2019, 12, 31), D(2019, 12, 31), D(2020, 1, 2)],
                "exdate": [D(2020, 1, 17), D(2020, 3, 20), D(2020, 1, 17)],
                "cp_flag": ["C", "P", "C"],
                "strike": [3200000, 3000000, 3250000],  # raw OptionMetrics: strike x 1000
                "best_bid": [10.0, 20.0, 5.0],
                "best_offer": [11.0, 22.0, 6.0],
                "optionid": [1, 2, 3],
            },
        ),
        _int_types(opt),
    )
    surf = reg.get("us/options/spx_vol_surface")
    _parquet(
        root / "WRDS_data/optionmetrics/optionm_vsurfd_spx_vol_surface_2019-2020.parquet",
        raw_table(
            surf,
            {
                "date": [D(2019, 12, 31), D(2019, 12, 31), D(2020, 1, 2)],
                "days": [30, 60, 30],
                "delta": [50, 50, 50],
                "cp_flag": ["C", "C", "C"],
                "impl_volatility": [0.12, 0.13, 0.14],
            },
        ),
        _int_types(surf),
    )
    spx = reg.get("us/index/spx_daily")
    _csv(
        root / "WRDS_data/optionmetrics/optionm_secprd_spx_index_prices_2019-2020.csv",
        raw_table(spx, {"date": ["2019-12-31", "2020-01-02"], "close": [3230.78, 3257.85]}),
    )
    _csv(
        root / "WRDS_data/optionmetrics/optionm_zerocd_zero_curve_2019-2020.csv",
        {
            "date": ["2019-12-31", "2019-12-31", "2020-01-02", "2020-01-02"],
            "days": [10, 100, 10, 100],
            "rate": [1.0, 2.0, 1.5, 2.5],
        },
    )

    # --- CSI 300 constituents (per-stock CSVs with zoned timestamps) ---------
    header = "Date,Open,High,Low,Close,Volume,Dividends,Stock Splits\n"
    prices = root / "finmultitime/HS300_time_series"
    prices.mkdir(parents=True, exist_ok=True)
    (prices / "600001.SS.csv").write_text(
        header
        + "2019-12-31 00:00:00+08:00,10.0,10.5,9.9,10.2,1000,0.0,0.0\n"
        + "2020-01-02 00:00:00+08:00,10.2,10.8,10.1,10.6,1200,0.3,0.0\n",
        encoding="utf-8",
    )
    (prices / "000002.SZ.csv").write_text(
        header + "2020-01-02 00:00:00+08:00,20.0,20.0,20.0,20.0,0,0.0,1.5\n",
        encoding="utf-8",
    )
    (root / "finmultitime/hs300_stocks.csv").write_text(
        "证券代码,证券简称,申万一级行业,table,image,ts,text\n"
        "600001.SS,公司甲,银行,1,1,1,1\n"
        "000002.SZ,公司乙,房地产,1,0,1,1\n"
        "600003.SS,退市丙,传媒,0,0,0,1\n",
        encoding="utf-8",
    )
    return root
