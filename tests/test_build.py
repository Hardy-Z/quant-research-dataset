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
        for p in (data_dir / "us/equity/crsp_daily").rglob("*.parquet")
    )
    assert crsp == [
        "us/equity/crsp_daily/year=2019/part-0.parquet",
        "us/equity/crsp_daily/year=2020/part-0.parquet",
    ]
    opts = {
        p.parent.relative_to(data_dir).as_posix()
        for p in (data_dir / "us/options/spx_option_prices").rglob("*.parquet")
    }
    assert opts == {
        "us/options/spx_option_prices/year=2019/month=12",
        "us/options/spx_option_prices/year=2020/month=01",
    }
    assert (data_dir / "us/equity/ccm_link/data.parquet").exists()


def test_manifest_contents(data_dir: Path) -> None:
    m = Manifest.load(data_dir)
    assert m.version == "test"
    crsp = m.entry("us/equity/crsp_daily")
    assert crsp.rows == 12 and crsp.ids == 3
    assert (crsp.start, crsp.end) == ("2019-12-30", "2020-01-03")
    for f in crsp.files:
        assert hashlib.sha256((data_dir / f.path).read_bytes()).hexdigest() == f.sha256


def test_column_conversions(data_dir: Path) -> None:
    ccm = _read(data_dir, "us/equity/ccm_link")
    assert ccm["gvkey"].tolist()[0] == "001000"  # leading zeros kept
    assert ccm["linkenddt"].isna().sum() == 2  # 'E' -> null
    assert "E" in ccm["tic"].tolist()  # the null token only applies to LINKENDDT

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


def test_sorted_output(data_dir: Path) -> None:
    crsp = _read(data_dir, "us/equity/crsp_daily")
    crsp["date"] = pd.to_datetime(crsp["date"])
    for _, part in crsp.groupby(crsp["date"].dt.year):
        assert part[["permno", "date"]].equals(
            part[["permno", "date"]].sort_values(["permno", "date"])
        )


def test_source_files_untouched(tmp_path: Path, source_root: Path, registry: Registry) -> None:
    before = {p: p.stat().st_mtime_ns for p in source_root.rglob("*") if p.is_file()}
    build_dataset(registry.get("crsp"), source_root, tmp_path / "out")
    after = {p: p.stat().st_mtime_ns for p in source_root.rglob("*") if p.is_file()}
    assert before == after


def test_output_inside_source_rejected(source_root: Path, registry: Registry) -> None:
    with pytest.raises(QRDError, match="contain"):
        build_dataset(registry.get("crsp"), source_root, source_root / "prepared")


def test_missing_source(tmp_path: Path, registry: Registry) -> None:
    with pytest.raises(QRDError, match="no source files"):
        build_dataset(registry.get("crsp"), tmp_path / "empty", tmp_path / "out")


def test_periods_between() -> None:
    p = periods_between(dt.date(2019, 11, 5), dt.date(2020, 2, 1), "year_month")
    assert [(x.year, x.month) for x in p] == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)]
    assert p[1].stop == dt.date(2020, 1, 1)
    assert [x.year for x in periods_between(dt.date(2019, 1, 1), dt.date(2021, 1, 1), "year")] == [
        2019,
        2020,
        2021,
    ]
