from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from quant_research_dataset.build import build_dataset, periods_between
from quant_research_dataset.errors import QRDError
from quant_research_dataset.manifest import Manifest
from quant_research_dataset.registry import Registry


def _read(data_dir: Path, ds_id: str):
    return pq.read_table(sorted((data_dir / ds_id).rglob("*.parquet"))).to_pandas()


def test_every_dataset_is_built(data_dir: Path, registry: Registry) -> None:
    manifest = Manifest.load(data_dir)
    assert set(manifest.datasets) == {s.id for s in registry}
    for spec in registry:
        for f in manifest.datasets[spec.id].files:
            assert pq.read_schema(data_dir / f.path).equals(spec.schema, check_metadata=False)


def test_partition_layout(data_dir: Path) -> None:
    crsp = sorted(
        p.relative_to(data_dir).as_posix()
        for p in (data_dir / "us/equity/stock_daily").rglob("*.parquet")
    )
    assert crsp == [
        "us/equity/stock_daily/year=2019/part-0.parquet",
        "us/equity/stock_daily/year=2020/part-0.parquet",
    ]
    opts = {
        p.parent.relative_to(data_dir).as_posix()
        for p in (data_dir / "us/options/spx_option_prices").rglob("*.parquet")
    }
    assert opts == {
        "us/options/spx_option_prices/year=2019/month=12",
        "us/options/spx_option_prices/year=2020/month=01",
    }
    assert not (data_dir / "us/equity/stock_company_link").exists()  # links are baked in


def test_manifest_contents(data_dir: Path) -> None:
    m = Manifest.load(data_dir)
    assert m.version == "test"
    crsp = m.entry("us/equity/stock_daily")
    assert crsp.rows == 12 and crsp.ids == 3
    assert (crsp.start, crsp.end) == ("2019-12-30", "2020-01-03")
    for f in crsp.files:
        assert hashlib.sha256((data_dir / f.path).read_bytes()).hexdigest() == f.sha256


def test_column_conversions(data_dir: Path) -> None:
    opts = _read(data_dir, "us/options/spx_option_prices")
    assert sorted(opts["strike"]) == [3000.0, 3200.0, 3250.0]  # strike / 1000

    bars = _read(data_dir, "us/etf/bars_5min")
    first = bars.sort_values("timestamp")["timestamp"].iloc[0]
    assert str(first.tz) == "UTC"
    assert first.to_pydatetime() == dt.datetime(
        2019, 12, 31, 20, 55, tzinfo=dt.timezone.utc
    )  # 15:55 EST
    july = bars["timestamp"].iloc[-1]
    assert july.hour == 13 and july.minute == 30  # 09:30 EDT


def test_id_from_filename_and_missing_columns(data_dir: Path) -> None:
    etf = _read(data_dir, "us/etf/daily_bars")
    assert set(etf["symbol"]) == {"SPY", "GLD"}
    assert etf.loc[etf.symbol == "SPY", "high"].isna().all()
    assert etf.loc[etf.symbol == "GLD", "volume"].iloc[0] == 7_000_000


def test_include_exclude_ids(data_dir: Path) -> None:
    assert set(_read(data_dir, "cn_hk/equity/daily_bars")["symbol"]) == {"600001.SS", "0001.HK"}
    assert set(_read(data_dir, "cn_hk/fx/daily")["symbol"]) == {"CNYHKD=X"}


def test_zoned_dates_keep_local_day(data_dir: Path) -> None:
    bars = _read(data_dir, "cn_hk/equity/csi300_stock_daily").sort_values(["symbol", "date"])
    assert list(bars["symbol"]) == ["000002.SZ", "600001.SS", "600001.SS"]
    # "2019-12-31 00:00:00+08:00" is 2019-12-30 in UTC but must stay 2019-12-31
    assert [str(d)[:10] for d in bars["date"]] == ["2020-01-02", "2019-12-31", "2020-01-02"]
    assert bars["volume"].tolist() == [0, 1000, 1200]
    assert bars["split_ratio"].tolist() == [1.5, 0.0, 0.0]
    stocks = _read(data_dir, "cn_hk/equity/csi300_stocks")
    assert stocks.set_index("symbol")["has_prices"].to_dict() == {
        "000002.SZ": True,
        "600001.SS": True,
        "600003.SS": False,
    }


def test_sorted_output(data_dir: Path) -> None:
    crsp = _read(data_dir, "us/equity/stock_daily")
    crsp["date"] = pd.to_datetime(crsp["date"])
    for _, part in crsp.groupby(crsp["date"].dt.year):
        assert part[["permno", "date"]].equals(
            part[["permno", "date"]].sort_values(["permno", "date"])
        )


def test_source_files_untouched(tmp_path: Path, source_root: Path, registry: Registry) -> None:
    before = {p: p.stat().st_mtime_ns for p in source_root.rglob("*") if p.is_file()}
    build_dataset(registry.get("us_stock_daily"), source_root, tmp_path / "out")
    after = {p: p.stat().st_mtime_ns for p in source_root.rglob("*") if p.is_file()}
    assert before == after


def test_output_inside_source_rejected(source_root: Path, registry: Registry) -> None:
    with pytest.raises(QRDError, match="contain"):
        build_dataset(registry.get("us_stock_daily"), source_root, source_root / "prepared")


def test_missing_source(tmp_path: Path, registry: Registry) -> None:
    with pytest.raises(QRDError, match="no source files"):
        build_dataset(registry.get("us_stock_daily"), tmp_path / "empty", tmp_path / "out")


def test_periods_between() -> None:
    p = periods_between(dt.date(2019, 11, 5), dt.date(2020, 2, 1), "year_month")
    assert [(x.year, x.month) for x in p] == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)]
    assert p[1].stop == dt.date(2020, 1, 1)
    assert [x.year for x in periods_between(dt.date(2019, 1, 1), dt.date(2021, 1, 1), "year")] == [
        2019,
        2020,
        2021,
    ]


def test_stock_rows_get_the_company_linked_on_their_date(data_dir: Path) -> None:
    stocks = _read(data_dir, "us/equity/stock_daily")
    stocks["date"] = pd.to_datetime(stocks["date"])
    by = {
        p: g.sort_values("date")["gvkey"].fillna("-").tolist() for p, g in stocks.groupby("permno")
    }
    assert by[10001] == ["001000"] * 4  # LC/P link, active ("E")
    assert by[10002] == ["-", "002000", "002000", "002000"]  # LU/C link starts 2019-12-31
    assert by[10003] == ["-"] * 4  # only an unusable LX link


def test_fundamentals_get_the_primary_permno(data_dir: Path) -> None:
    q = _read(data_dir, "us/fundamentals/quarterly").set_index(["gvkey", "datadate"])["permno"]
    assert q.loc[("001000", dt.date(2019, 9, 30))] == 10001  # gvkey keeps its leading zeros
    assert pd.isna(q.loc[("002000", dt.date(2019, 9, 30))])  # before the link starts
    a = _read(data_dir, "us/fundamentals/annual").set_index("gvkey")["permno"]
    assert a.to_dict() == {"001000": 10001, "002000": 10002}


def test_null_tokens_apply_to_one_column_only() -> None:
    import pyarrow as pa

    from quant_research_dataset.build import standardize
    from quant_research_dataset.registry import DatasetSpec

    spec = DatasetSpec.from_dict(
        {
            "id": "xx/equity/toy",
            "title": "Toy",
            "market": "xx",
            "asset_class": "equity",
            "frequency": "static",
            "source": "made up",
            "license": "none",
            "build": {
                "source": "toy.csv",
                "format": "csv",
                "options": {"null_tokens": {"END": ["E"]}},
            },
            "columns": [
                {"name": "tic", "type": "string"},
                {"name": "end", "source": "END", "type": "date32"},
            ],
        }
    )
    raw = pa.table({"tic": ["E", "X"], "END": ["E", "2020-01-31"]})
    out = standardize(raw, spec).to_pydict()
    assert out == {"tic": ["E", "X"], "end": [None, dt.date(2020, 1, 31)]}


def test_derived_columns_need_an_enrich_step() -> None:
    from quant_research_dataset.errors import RegistryError
    from quant_research_dataset.registry import DatasetSpec

    data = {
        "id": "xx/equity/toy",
        "title": "Toy",
        "market": "xx",
        "asset_class": "equity",
        "frequency": "static",
        "source": "s",
        "license": "l",
        "build": {"source": "toy.csv"},
        "columns": [{"name": "k", "type": "string", "derived": True}],
    }
    with pytest.raises(RegistryError, match="enrich"):
        DatasetSpec.from_dict(data)
