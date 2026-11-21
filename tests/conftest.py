from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

import quant_research_dataset as qrd
from quant_research_dataset.build import build_all
from quant_research_dataset.registry import Registry, default_registry

from .fakes import write_fake_source


@pytest.fixture(scope="session")
def registry() -> Registry:
    return default_registry()


@pytest.fixture(scope="session")
def source_root(tmp_path_factory: pytest.TempPathFactory, registry: Registry) -> Path:
    return write_fake_source(tmp_path_factory.mktemp("raw"), registry)


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory: pytest.TempPathFactory, source_root: Path) -> Path:
    out = tmp_path_factory.mktemp("prepared")
    build_all(source_root, out, version="test")
    return out


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for var in (
        "QRD_DATA_DIR",
        "QRD_REPO_ID",
        "QRD_REVISION",
        "QRD_CACHE_DIR",
        "QRD_REGISTRY_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    qrd.configure(reset=True)
    yield
    qrd.configure(reset=True)


@pytest.fixture
def local(data_dir: Path) -> Path:
    """Point the library at the prepared fake data."""
    qrd.configure(data_dir=data_dir)
    return data_dir
