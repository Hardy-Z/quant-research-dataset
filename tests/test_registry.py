from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from quant_research_dataset.adapters import get_adapter
from quant_research_dataset.errors import DatasetNotFoundError, RegistryError
from quant_research_dataset.registry import DatasetSpec, Registry, load_registry, load_spec_file


def _minimal(**over: object) -> dict:
    data = {
        "id": "xx/equity/toy",
        "title": "Toy",
        "market": "xx",
        "asset_class": "equity",
        "frequency": "daily",
        "source": "made up",
        "license": "none",
        "id_column": "sym",
        "date_column": "date",
        "partitioning": "year",
        "build": {"source": "toy.csv", "format": "csv"},
        "columns": [{"name": "sym", "type": "string"}, {"name": "date", "type": "date32"}],
    }
    data.update(over)
    return data


def test_builtin_registry_loads(registry: Registry) -> None:
    ids = [s.id for s in registry]
    assert len(ids) == len(set(ids)) >= 13
    assert {"us", "cn_hk"} <= {s.market for s in registry}
    for spec in registry:
        assert spec.path is not None and spec.path.parent.as_posix().endswith(
            f"{spec.market}/{spec.asset_class}"
        )
        assert isinstance(spec.schema, pa.Schema)
        get_adapter(spec.adapter)  # every referenced adapter exists
        assert spec.description and all(c.description for c in spec.columns)


def test_names_describe_content_not_vendor(registry: Registry) -> None:
    vendors = (
        "crsp",
        "compustat",
        "ccm",
        "optionmetrics",
        "wrds",
        "alpaca",
        "yahoo",
        "finmultitime",
    )
    for spec in registry:
        for name in (spec.id, *spec.aliases):
            assert not any(v in name.lower() for v in vendors), name


def test_alias_resolution(registry: Registry) -> None:
    assert registry.resolve("us_stock_daily") == "us/equity/stock_daily"
    assert registry.resolve("us_stock_daily") == "us/equity/stock_daily"
    assert registry.resolve("us/equity/stock_daily") == "us/equity/stock_daily"
    assert "us_fundamentals_quarterly" in registry and "nope" not in registry


def test_ambiguous_name_is_rejected(registry: Registry) -> None:
    # "daily_bars" exists in both us/etf and cn_hk/equity
    with pytest.raises(DatasetNotFoundError, match="ambiguous"):
        registry.resolve("daily_bars")


def test_unknown_dataset() -> None:
    reg = Registry([DatasetSpec.from_dict(_minimal())])
    with pytest.raises(DatasetNotFoundError, match="list_datasets"):
        reg.get("missing")


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"id": "toy"}, "market/asset/name"),
        ({"market": "yy"}, "does not match"),
        ({"partitioning": "weekly"}, "partitioning"),
        ({"frequency": "hourly"}, "frequency"),
        ({"date_column": "nope"}, "not a declared column"),
        (
            {"columns": [{"name": "sym", "type": "decimal"}, {"name": "date", "type": "date32"}]},
            "unknown column type",
        ),
        (
            {"columns": [{"name": "sym", "type": "string"}, {"name": "sym", "type": "string"}]},
            "duplicate",
        ),
        ({"sort_by": ["zzz"]}, "sort_by"),
        ({"build": {}}, "build.source"),
    ],
)
def test_invalid_specs(override: dict, message: str) -> None:
    with pytest.raises(RegistryError, match=message):
        DatasetSpec.from_dict(_minimal(**override))


def test_missing_keys() -> None:
    data = _minimal()
    del data["license"]
    with pytest.raises(RegistryError, match="missing keys"):
        DatasetSpec.from_dict(data)


def test_duplicate_ids_rejected() -> None:
    spec = DatasetSpec.from_dict(_minimal())
    with pytest.raises(RegistryError, match="twice"):
        Registry([spec, spec])


def test_extra_registry_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    folder = tmp_path / "xx" / "equity"
    folder.mkdir(parents=True)
    (folder / "toy.yaml").write_text(yaml.safe_dump(_minimal()), encoding="utf-8")
    monkeypatch.setenv("QRD_REGISTRY_PATH", str(tmp_path))
    reg = load_registry()
    assert reg.get("toy").id == "xx/equity/toy"
    assert load_spec_file(folder / "toy.yaml").market == "xx"
