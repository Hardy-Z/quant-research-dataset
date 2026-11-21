"""Dataset registry.

Every dataset is described by one YAML file under ``registry/<market>/<asset>/``.
The YAML entry is the single source of truth for a dataset: its id, where it
sits in the storage layout, its columns (names, types, units, descriptions),
how it is partitioned, and how to build it from raw files. Adding a dataset
means adding one YAML file (and, only if the raw data needs special handling,
one adapter).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import pyarrow as pa
import yaml

from .errors import DatasetNotFoundError, RegistryError

PARTITIONINGS = ("none", "year", "year_month")
FREQUENCIES = ("static", "intraday", "daily", "monthly", "quarterly", "annual")

_TYPES: dict[str, pa.DataType] = {
    "bool": pa.bool_(),
    "int8": pa.int8(),
    "int16": pa.int16(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "string": pa.string(),
    "date32": pa.date32(),
    "timestamp[us, UTC]": pa.timestamp("us", tz="UTC"),
    "timestamp[us]": pa.timestamp("us"),
}

_ID_RE = re.compile(r"^[a-z0-9_]+(/[a-z0-9_]+){2}$")


def arrow_type(name: str) -> pa.DataType:
    """Map a registry type name (e.g. ``"float64"``) to a pyarrow type."""
    try:
        return _TYPES[name]
    except KeyError:
        raise RegistryError(
            f"unknown column type {name!r}; expected one of {sorted(_TYPES)}"
        ) from None


@dataclass(frozen=True)
class ColumnSpec:
    """One column of a dataset."""

    name: str
    type: str
    description: str = ""
    unit: str | None = None
    source: str | None = None  # raw column name, when it differs from ``name``

    @property
    def arrow_type(self) -> pa.DataType:
        return arrow_type(self.type)

    @property
    def source_name(self) -> str:
        return self.source or self.name


@dataclass(frozen=True)
class BuildSpec:
    """How to build the dataset from raw files (maintainers only)."""

    source: tuple[str, ...]
    format: str = "parquet"
    include_ids: tuple[str, ...] = ()
    exclude_ids: tuple[str, ...] = ()
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetSpec:
    """Metadata for one dataset, loaded from its registry YAML file."""

    id: str
    title: str
    description: str
    market: str
    asset_class: str
    frequency: str
    source: str
    license: str
    columns: tuple[ColumnSpec, ...]
    build: BuildSpec
    id_column: str | None = None
    date_column: str | None = None
    partitioning: str = "none"
    sort_by: tuple[str, ...] = ()
    adapter: str = "default"
    aliases: tuple[str, ...] = ()
    publish: bool = True
    notes: tuple[str, ...] = ()
    path: Path | None = None  # file the spec was loaded from

    # ------------------------------------------------------------------ helpers
    @property
    def name(self) -> str:
        """Last component of the id, e.g. ``crsp_daily``."""
        return self.id.rsplit("/", 1)[-1]

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> ColumnSpec:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.id} has no column {name!r}")

    @property
    def schema(self) -> pa.Schema:
        """The Arrow schema every prepared partition of this dataset has."""
        return pa.schema([pa.field(c.name, c.arrow_type) for c in self.columns])

    # --------------------------------------------------------------- validation
    @classmethod
    def from_dict(cls, data: dict[str, Any], path: Path | None = None) -> DatasetSpec:
        where = f" in {path}" if path else ""
        required = (
            "id",
            "title",
            "market",
            "asset_class",
            "frequency",
            "source",
            "license",
            "columns",
            "build",
        )
        missing = [k for k in required if k not in data]
        if missing:
            raise RegistryError(f"missing keys {missing}{where}")

        ds_id = str(data["id"])
        if not _ID_RE.match(ds_id):
            raise RegistryError(f"dataset id {ds_id!r}{where} must look like 'market/asset/name'")
        market, asset, _ = ds_id.split("/")
        if market != data["market"] or asset != data["asset_class"]:
            raise RegistryError(f"id {ds_id!r}{where} does not match market/asset_class fields")

        columns = tuple(
            ColumnSpec(
                name=str(c["name"]),
                type=str(c["type"]),
                description=str(c.get("description", "")).strip(),
                unit=c.get("unit"),
                source=c.get("source"),
            )
            for c in data["columns"]
        )
        names = [c.name for c in columns]
        if len(set(names)) != len(names):
            raise RegistryError(f"duplicate column names{where}")
        for c in columns:
            arrow_type(c.type)  # raises on unknown types

        partitioning = str(data.get("partitioning", "none"))
        if partitioning not in PARTITIONINGS:
            raise RegistryError(f"partitioning {partitioning!r}{where} not in {PARTITIONINGS}")
        frequency = str(data["frequency"])
        if frequency not in FREQUENCIES:
            raise RegistryError(f"frequency {frequency!r}{where} not in {FREQUENCIES}")

        id_column = data.get("id_column")
        date_column = data.get("date_column")
        for key, col in (("id_column", id_column), ("date_column", date_column)):
            if col is not None and col not in names:
                raise RegistryError(f"{key} {col!r}{where} is not a declared column")
        if partitioning != "none" and date_column is None:
            raise RegistryError(f"partitioned dataset{where} needs a date_column")
        sort_by = tuple(data.get("sort_by", ()))
        unknown = [c for c in sort_by if c not in names]
        if unknown:
            raise RegistryError(f"sort_by columns {unknown}{where} are not declared")

        b = data["build"]
        src = b.get("source")
        if not src:
            raise RegistryError(f"build.source is required{where}")
        build = BuildSpec(
            source=tuple([src] if isinstance(src, str) else src),
            format=str(b.get("format", "parquet")),
            include_ids=tuple(str(x) for x in b.get("include_ids", ())),
            exclude_ids=tuple(str(x) for x in b.get("exclude_ids", ())),
            options=dict(b.get("options", {})),
        )

        return cls(
            id=ds_id,
            title=str(data["title"]),
            description=str(data.get("description", "")).strip(),
            market=market,
            asset_class=asset,
            frequency=frequency,
            source=str(data["source"]),
            license=str(data["license"]),
            columns=columns,
            build=build,
            id_column=id_column,
            date_column=date_column,
            partitioning=partitioning,
            sort_by=sort_by,
            adapter=str(data.get("adapter", "default")),
            aliases=tuple(str(a) for a in data.get("aliases", ())),
            publish=bool(data.get("publish", True)),
            notes=tuple(str(n).strip() for n in data.get("notes", ())),
            path=path,
        )


class Registry:
    """A collection of :class:`DatasetSpec` objects with alias lookup."""

    def __init__(self, specs: Iterable[DatasetSpec]):
        self._specs: dict[str, DatasetSpec] = {}
        self._aliases: dict[str, str] = {}
        for spec in specs:
            self.add(spec)

    def add(self, spec: DatasetSpec) -> None:
        if spec.id in self._specs:
            raise RegistryError(f"dataset {spec.id!r} is registered twice")
        self._specs[spec.id] = spec
        for alias in (spec.name, *spec.aliases):
            # A bare name that is ambiguous across markets is simply not an alias.
            if alias in self._aliases and self._aliases[alias] != spec.id:
                self._aliases[alias] = ""
            else:
                self._aliases[alias] = spec.id

    def resolve(self, key: str) -> str:
        """Turn an id or alias into a dataset id."""
        if key in self._specs:
            return key
        target = self._aliases.get(key)
        if target:
            return target
        if target == "":
            options = sorted(
                i for i in self._specs if i.endswith("/" + key) or key in self._specs[i].aliases
            )
            raise DatasetNotFoundError(f"{key!r} is ambiguous; use one of {options}")
        raise DatasetNotFoundError(
            f"unknown dataset {key!r}; call list_datasets() to see what is available"
        )

    def get(self, key: str) -> DatasetSpec:
        return self._specs[self.resolve(key)]

    def __iter__(self) -> Iterator[DatasetSpec]:
        return iter(sorted(self._specs.values(), key=lambda s: s.id))

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self.resolve(key)
        except DatasetNotFoundError:
            return False
        return True

    def filter(
        self,
        market: str | None = None,
        asset_class: str | None = None,
        frequency: str | None = None,
    ) -> list[DatasetSpec]:
        return [
            s
            for s in self
            if (market is None or s.market == market)
            and (asset_class is None or s.asset_class == asset_class)
            and (frequency is None or s.frequency == frequency)
        ]


def load_spec_file(path: Path) -> DatasetSpec:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RegistryError(f"{path} does not contain a YAML mapping")
    return DatasetSpec.from_dict(data, path=path)


def _yaml_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.yaml") if p.is_file())


def builtin_registry_dir() -> Path:
    return Path(str(resources.files("quant_research_dataset") / "registry"))


def load_registry(extra_dirs: Iterable[str | os.PathLike[str]] = ()) -> Registry:
    """Load the built-in registry plus YAML files from ``extra_dirs``.

    Directories listed in the ``QRD_REGISTRY_PATH`` environment variable
    (separated by ``os.pathsep``) are added too, so private datasets can be
    registered without changing the package.
    """
    dirs = [builtin_registry_dir(), *(Path(d) for d in extra_dirs)]
    env = os.environ.get("QRD_REGISTRY_PATH")
    if env:
        dirs += [Path(p) for p in env.split(os.pathsep) if p]
    specs = [load_spec_file(f) for d in dirs for f in _yaml_files(d)]
    return Registry(specs)


@lru_cache(maxsize=1)
def default_registry() -> Registry:
    """The registry used by the public API (cached)."""
    return load_registry()
