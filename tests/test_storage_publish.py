"""Hugging Face backend (with the network replaced by a local folder), docs and publishing."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

import quant_research_dataset as qrd
from quant_research_dataset import cli
from quant_research_dataset.catalog import render_data_dictionary
from quant_research_dataset.errors import ConfigError, QRDError
from quant_research_dataset.manifest import Manifest
from quant_research_dataset.publish import plan_release, verify
from quant_research_dataset.storage import HubBackend


@pytest.fixture
def fake_hub(monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> list[str]:
    """Replace hf_hub_download with a copy from the prepared fake data."""
    import huggingface_hub

    calls: list[str] = []

    def fake_download(
        repo_id: str, filename: str, repo_type: str, revision: str, **_: object
    ) -> str:
        assert repo_type == "dataset"
        if repo_id == "gated/repo":
            from huggingface_hub.errors import GatedRepoError

            err = GatedRepoError.__new__(
                GatedRepoError
            )  # skip __init__, which needs an HTTP response
            err.args = ("gated",)
            raise err
        calls.append(filename)
        return str(data_dir / filename)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake_download)
    return calls


def test_hub_backend_downloads_only_needed_files(fake_hub: list[str]) -> None:
    qrd.configure(repo_id="owner/qrd", revision="v1")
    df = qrd.load("us_stock_daily", start="2020-01-02", end="2020-01-02")
    assert len(df) == 3
    assert fake_hub == ["manifest.json", "us/equity/stock_daily/year=2020/part-0.parquet"]


def test_hub_backend_gated_message(fake_hub: list[str]) -> None:
    with pytest.raises(ConfigError, match="request access"):
        HubBackend("gated/repo").manifest()


def test_data_dictionary_mentions_every_dataset(data_dir: Path, registry) -> None:
    md = render_data_dictionary(registry, Manifest.load(data_dir))
    for spec in registry:
        assert f"`{spec.id}`" in md
    assert "**Coverage:**" in md


def test_release_plan_only_includes_publishable(data_dir: Path, registry) -> None:
    plan = plan_release(data_dir, "owner/qrd")
    assert set(plan.datasets) == {s.id for s in registry if s.publish}
    assert "us/etf/daily_bars" not in plan.datasets  # publish: false
    assert set(plan.manifest.datasets) == set(plan.datasets)
    front = yaml.safe_load(plan.card.split("---")[1])
    assert {c["config_name"] for c in front["configs"]} == {
        d.replace("/", "__") for d in plan.datasets
    }
    assert front["extra_gated_fields"]
    explicit = plan_release(data_dir, "owner/qrd", datasets=["us_etf_daily"])
    assert explicit.datasets == ("us/etf/daily_bars",)


def test_upload_patterns_select_exactly_the_release(data_dir: Path) -> None:
    from huggingface_hub.utils import filter_repo_objects

    plan = plan_release(data_dir, "owner/qrd")
    on_disk = [p.relative_to(data_dir).as_posix() for p in data_dir.rglob("*") if p.is_file()]
    selected = set(filter_repo_objects(on_disk, allow_patterns=plan.paths))
    expected = {f.path for e in plan.manifest.datasets.values() for f in e.files}
    assert selected == expected  # includes unpartitioned data.parquet files
    assert "us/rates/zero_curve/data.parquet" in selected
    assert not any(p.startswith("us/etf/") for p in selected)


def test_release_plan_requires_built_data(tmp_path: Path, data_dir: Path) -> None:
    m = Manifest.load(data_dir)
    m.datasets.pop("us/equity/stock_daily")
    m.save(tmp_path)
    with pytest.raises(QRDError, match="not built"):
        plan_release(tmp_path, "owner/qrd")


def test_verify_detects_tampering(tmp_path: Path, data_dir: Path) -> None:
    copy = tmp_path / "copy"
    shutil.copytree(data_dir, copy)
    assert verify(copy) == []
    target = next((copy / "us/index/spx_daily").glob("*.parquet"))
    target.write_bytes(target.read_bytes() + b"x")
    (copy / "us/rates/zero_curve/data.parquet").unlink()
    problems = verify(copy)
    assert any("checksum" in p for p in problems) and any("missing" in p for p in problems)


def test_cli_commands(
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert cli.main(["list", "--market", "cn_hk"]) == 0
    assert "cn_hk/fx/daily" in capsys.readouterr().out
    assert cli.main(["describe", "us_stock_daily", "--offline"]) == 0
    assert "permno" in capsys.readouterr().out
    assert cli.main(["verify", "--data-dir", str(data_dir)]) == 0
    assert cli.main(["publish", "--data-dir", str(data_dir), "--repo-id", "owner/qrd"]) == 0
    assert "Dry run" in capsys.readouterr().out
    card = tmp_path / "card.md"
    assert (
        cli.main(["docs", "--data-dir", str(data_dir), "--out", str(tmp_path), "--card", str(card)])
        == 0
    )
    assert (tmp_path / "datasets.md").exists() and card.read_text(encoding="utf-8").startswith(
        "---"
    )
    monkeypatch.setenv("QRD_DATA_DIR", str(data_dir))
    qrd.configure(reset=True)
    assert cli.main(["describe", "nope"]) == 2
    assert "unknown dataset" in capsys.readouterr().err
