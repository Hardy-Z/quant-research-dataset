from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest

import quant_research_dataset as qrd
from quant_research_dataset.errors import ConfigError, ManifestError, QRDError
from quant_research_dataset.storage import LocalBackend


class SpyBackend(LocalBackend):
    """Local backend that records which files were requested."""

    def __init__(self, root: Path):
        super().__init__(root)
        self.fetched: list[str] = []

    def fetch(self, paths: Sequence[str]) -> list[Path]:
        self.fetched += list(paths)
        return super().fetch(paths)


def test_list_and_describe(local: Path) -> None:
    us_opts = qrd.list_datasets(market="us", asset_class="options")
    assert set(us_opts["id"]) == {"us/options/spx_option_prices", "us/options/spx_vol_surface"}
    info = qrd.describe("crsp")
    assert info["rows"] == 12 and info["start"] == "2019-12-30" and info["n_ids"] == 3
    assert "common_only" in info["load_options"]
    assert {"name", "type", "unit", "description"} <= set(info["columns"].columns)
    offline = qrd.describe("crsp", coverage=False)
    assert "rows" not in offline


def test_load_by_id_and_dates(local: Path) -> None:
    df = qrd.load(
        "crsp", ids=10001, start="2019-12-31", end="2020-01-02", columns=["date", "permno", "ret"]
    )
    assert list(df.columns) == ["date", "permno", "ret"]
    assert df["permno"].unique().tolist() == [10001]
    assert df["date"].dt.strftime("%Y-%m-%d").tolist() == ["2019-12-31", "2020-01-02"]
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_ids_accept_strings_for_int_columns(local: Path) -> None:
    assert len(qrd.load("crsp", ids=["10001", "10002"])) == 8


def test_partition_pruning(data_dir: Path) -> None:
    spy = SpyBackend(data_dir)
    qrd.load("crsp", start="2020-01-01", backend=spy)
    assert spy.fetched == ["us/equity/crsp_daily/year=2020/part-0.parquet"]
    spy.fetched.clear()
    qrd.load("spx_options", start="2019-12-31", end="2019-12-31", backend=spy)
    assert spy.fetched == ["us/options/spx_option_prices/year=2019/month=12/part-0.parquet"]


def test_filters(local: Path) -> None:
    assert set(qrd.load("crsp", filters={"ticker": "BBB"})["permno"]) == {10002}
    assert set(qrd.load("crsp", filters={"ticker": ["AAA", "BBB"]})["permno"]) == {10001, 10002}
    assert (qrd.load("crsp", filters={"ret": (">", 0.015)})["ret"] > 0.015).all()
    with pytest.raises(QRDError, match="no column"):
        qrd.load("crsp", filters={"nope": 1})


def test_arrow_output(local: Path) -> None:
    table = qrd.load("crsp", columns=["permno", "date"], output="arrow")
    assert isinstance(table, pa.Table) and table.column_names == ["permno", "date"]
    with pytest.raises(QRDError, match="output"):
        qrd.load("crsp", output="polars")  # type: ignore[arg-type]


def test_empty_result_keeps_schema(local: Path) -> None:
    df = qrd.load("crsp", start="2030-01-01", columns=["date", "permno"])
    assert df.empty and list(df.columns) == ["date", "permno"]


def test_intraday_date_only_end_is_inclusive(local: Path) -> None:
    df = qrd.load("etf_5min", start="2019-12-31", end="2019-12-31")
    assert len(df) == 1  # the 20:55 UTC bar on 2019-12-31
    df = qrd.load("etf_5min", start="2020-01-02 14:30", end="2020-01-02 14:30")
    assert len(df) == 1


def test_validation_errors(local: Path) -> None:
    with pytest.raises(QRDError, match="no columns"):
        qrd.load("crsp", columns=["nope"])
    with pytest.raises(QRDError, match="does not accept"):
        qrd.load("crsp", bogus=True)
    with pytest.raises(QRDError, match="after end"):
        qrd.load("crsp", start="2020-02-01", end="2020-01-01")
    with pytest.raises(QRDError, match="no id column"):
        qrd.load("vol_surface", ids=1)
    with pytest.raises(QRDError, match="no date column"):
        qrd.load("ah_pairs", start="2020-01-01")


def test_static_table(local: Path) -> None:
    pairs = qrd.load("ah_pairs")
    assert pairs.iloc[0].to_dict() == {
        "a_symbol": "600001.SS",
        "h_symbol": "0001.HK",
        "name": "公司甲",
    }


def test_files_for_and_download(local: Path) -> None:
    paths = qrd.download("crsp", start="2019-01-01", end="2019-12-31")
    assert [p.parent.name for p in paths] == ["year=2019"]


def test_dataset_missing_from_manifest(tmp_path: Path, data_dir: Path) -> None:
    from quant_research_dataset.manifest import Manifest

    m = Manifest.load(data_dir)
    del m.datasets["us/equity/crsp_daily"]
    m.save(tmp_path)
    qrd.configure(data_dir=tmp_path)
    with pytest.raises(ManifestError, match="not present"):
        qrd.load("crsp")


def test_bad_data_dir(tmp_path: Path) -> None:
    qrd.configure(data_dir=tmp_path / "missing")
    with pytest.raises(ConfigError, match="does not exist"):
        qrd.load("crsp")


def test_env_var_configuration(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QRD_DATA_DIR", str(data_dir))
    qrd.configure(reset=True)
    assert qrd.get_settings().source == "local"
    assert len(qrd.load("crsp")) == 12


def test_configure_repo_switches_to_hub(data_dir: Path) -> None:
    qrd.configure(data_dir=data_dir)
    s = qrd.configure(repo_id="someone/else")
    assert s.source == "hub" and s.repo_id == "someone/else"
