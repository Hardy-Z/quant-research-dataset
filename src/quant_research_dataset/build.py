"""Build prepared, partitioned parquet files from raw source files.

This is maintainer tooling: it turns the raw downloads (WRDS parquet/CSV,
vendor CSVs) into the standard layout the client reads::

    <out>/<market>/<asset>/<name>/year=2015/part-0.parquet
    <out>/<market>/<asset>/<name>/year=2015/month=08/part-0.parquet
    <out>/<market>/<asset>/<name>/data.parquet          (unpartitioned)
    <out>/manifest.json

Everything is driven by the registry YAML: which raw files to read, how to
rename and type each column, how to partition and sort. Raw files are only
ever read, never modified.
"""

from __future__ import annotations

import csv
import datetime as dt
import logging
import re
import shutil
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .errors import QRDError
from .manifest import Manifest, build_manifest
from .registry import DatasetSpec, Registry, default_registry

log = logging.getLogger(__name__)

ROW_GROUP_SIZE = 131_072
COMPRESSION = "zstd"
COMPRESSION_LEVEL = 6


# --------------------------------------------------------------------- sources
def source_files(spec: DatasetSpec, source_root: Path) -> list[Path]:
    """Resolve the raw files for ``spec`` (``build.source`` may hold globs)."""
    files: list[Path] = []
    for pattern in spec.build.source:
        matches = sorted(source_root.glob(pattern))
        if not matches:
            raise QRDError(f"{spec.id}: no source files match {pattern!r} under {source_root}")
        files += matches
    return files


def _read_csv(path: Path, spec: DatasetSpec) -> pa.Table:
    # Read every column as text and convert explicitly later. This keeps
    # identifiers such as gvkey ("001004") and CUSIPs intact.
    with path.open(encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh))
    convert = pacsv.ConvertOptions(
        column_types={name: pa.string() for name in header},
        strings_can_be_null=True,
        null_values=[""],
    )
    table = pacsv.read_csv(path, convert_options=convert)
    pattern = spec.build.options.get("id_from_filename")
    if pattern:
        if spec.id_column is None:
            raise QRDError(f"{spec.id}: id_from_filename needs an id_column")
        m = re.search(pattern, path.name)
        if not m:
            raise QRDError(f"{spec.id}: {path.name} does not match id_from_filename {pattern!r}")
        target = spec.column(spec.id_column).source_name
        table = table.append_column(target, pa.array([m.group("id")] * table.num_rows, pa.string()))
    return table


def read_source(spec: DatasetSpec, source_root: Path) -> ds.Dataset:
    """Open the raw source as an Arrow dataset (CSV files are read eagerly)."""
    files = source_files(spec, source_root)
    if spec.build.format == "parquet":
        return ds.dataset([str(f) for f in files], format="parquet")
    if spec.build.format == "csv":
        tables = [_read_csv(f, spec) for f in files]
        return ds.dataset(pa.concat_tables(tables, promote_options="default"))
    raise QRDError(f"{spec.id}: unsupported source format {spec.build.format!r}")


# ------------------------------------------------------------------ conversion
def _to_naive_or_zoned(
    arr: pa.ChunkedArray, target: pa.DataType, tz: str | None
) -> pa.ChunkedArray:
    """Convert a timestamp array to ``target``, localising naive values to ``tz``."""
    src_tz = getattr(arr.type, "tz", None)
    tgt_tz = getattr(target, "tz", None)
    if src_tz is None and tgt_tz is not None:
        arr = pc.assume_timezone(arr, timezone=tz or "UTC")
    return arr.cast(target)


def convert_column(
    arr: pa.ChunkedArray, target: pa.DataType, options: dict[str, Any]
) -> pa.ChunkedArray:
    """Convert a raw column to its registry type."""
    if pa.types.is_dictionary(arr.type):
        arr = arr.cast(arr.type.value_type)
    if arr.type == target:
        return arr
    src = arr.type
    tz = options.get("timezone")
    if pa.types.is_string(src) or pa.types.is_large_string(src):
        if pa.types.is_date32(target):
            return pc.strptime(arr, format="%Y-%m-%d", unit="s").cast(pa.date32())
        if pa.types.is_timestamp(target):
            fmt = options.get("timestamp_format", "%Y-%m-%d %H:%M:%S")
            return _to_naive_or_zoned(pc.strptime(arr, format=fmt, unit="us"), target, tz)
        if pa.types.is_integer(target):
            as_float = arr.cast(pa.float64())
            return as_float.cast(target)  # safe cast: fails on fractional values
        return arr.cast(target)
    if pa.types.is_timestamp(src):
        if pa.types.is_date32(target):
            return arr.cast(pa.date32())
        if pa.types.is_timestamp(target):
            return _to_naive_or_zoned(arr, target, tz)
    return arr.cast(target)


def standardize(raw: pa.Table, spec: DatasetSpec) -> pa.Table:
    """Select, rename, type, filter and sort raw columns into the registry schema."""
    opts = spec.build.options
    columns: dict[str, pa.ChunkedArray] = {}
    for col in spec.columns:
        if col.source_name not in raw.column_names:
            raise QRDError(f"{spec.id}: source column {col.source_name!r} not found")
        arr = raw.column(col.source_name)
        for token in opts.get("null_tokens", {}).get(col.source_name, []):
            arr = pc.if_else(pc.equal(arr, token), pa.scalar(None, arr.type), arr)
        arr = convert_column(arr, col.arrow_type, opts)
        scale = opts.get("scale", {}).get(col.name)
        if scale is not None:
            arr = pc.multiply(arr, pa.scalar(float(scale))).cast(col.arrow_type)
        columns[col.name] = arr
    table = pa.table(columns, schema=spec.schema)

    if spec.id_column and (spec.build.include_ids or spec.build.exclude_ids):
        ids = table.column(spec.id_column)
        if spec.build.include_ids:
            table = table.filter(pc.is_in(ids, pa.array(spec.build.include_ids)))
        if spec.build.exclude_ids:
            table = table.filter(pc.invert(pc.is_in(ids, pa.array(spec.build.exclude_ids))))
    if spec.sort_by and table.num_rows:
        table = table.sort_by([(c, "ascending") for c in spec.sort_by])
    return table


# ------------------------------------------------------------------ partitions
@dataclass(frozen=True)
class Period:
    year: int
    month: int | None = None

    @property
    def start(self) -> dt.date:
        return dt.date(self.year, self.month or 1, 1)

    @property
    def stop(self) -> dt.date:  # exclusive
        if self.month is None:
            return dt.date(self.year + 1, 1, 1)
        return dt.date(self.year + (self.month == 12), self.month % 12 + 1, 1)

    def relpath(self) -> str:
        if self.month is None:
            return f"year={self.year}/part-0.parquet"
        return f"year={self.year}/month={self.month:02d}/part-0.parquet"


def periods_between(first: dt.date, last: dt.date, partitioning: str) -> list[Period]:
    out: list[Period] = []
    for year in range(first.year, last.year + 1):
        if partitioning == "year":
            out.append(Period(year))
        else:
            lo = first.month if year == first.year else 1
            hi = last.month if year == last.year else 12
            out += [Period(year, m) for m in range(lo, hi + 1)]
    return out


def _as_date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _bound(value: dt.date, typ: pa.DataType) -> pa.Scalar:
    if pa.types.is_timestamp(typ):
        tz = dt.timezone.utc if typ.tz else None
        return pa.scalar(dt.datetime(value.year, value.month, value.day, tzinfo=tz), type=typ)
    return pa.scalar(value, type=typ)


def iter_partitions(spec: DatasetSpec, source: ds.Dataset) -> Iterator[tuple[str, pa.Table]]:
    """Yield ``(relative path, standardized table)`` for each output file."""
    if spec.partitioning == "none":
        yield "data.parquet", standardize(source.to_table(), spec)
        return

    assert spec.date_column is not None
    raw_date = spec.column(spec.date_column).source_name
    raw_type = source.schema.field(raw_date).type
    if pa.types.is_date(raw_type) or pa.types.is_timestamp(raw_type):
        # Large typed sources: scan one period at a time to bound memory.
        mm = pc.min_max(source.to_table(columns=[raw_date]).column(0))
        for period in periods_between(
            _as_date(mm["min"].as_py()), _as_date(mm["max"].as_py()), spec.partitioning
        ):
            expr = (pc.field(raw_date) >= _bound(period.start, raw_type)) & (
                pc.field(raw_date) < _bound(period.stop, raw_type)
            )
            table = standardize(source.to_table(filter=expr), spec)
            if table.num_rows:
                yield period.relpath(), table
        return

    # Small text sources: standardize once, then split in memory.
    table = standardize(source.to_table(), spec)
    dates = table.column(spec.date_column)
    years = pc.year(dates)
    months = pc.month(dates) if spec.partitioning == "year_month" else None
    month_list = months.to_pylist() if months is not None else [None] * len(years)
    keys = sorted(set(zip(years.to_pylist(), month_list, strict=True)))
    for year, month in keys:
        mask = pc.equal(years, year)
        if months is not None:
            mask = pc.and_(mask, pc.equal(months, month))
        yield Period(year, month).relpath(), table.filter(mask)


def write_table(table: pa.Table, path: Path, row_group_size: int = ROW_GROUP_SIZE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        compression=COMPRESSION,
        compression_level=COMPRESSION_LEVEL,
        row_group_size=row_group_size,
        write_statistics=True,
    )


def build_dataset(spec: DatasetSpec, source_root: str | Path, out_root: str | Path) -> list[Path]:
    """Build one dataset. Its previous output folder is replaced."""
    source_root, out_root = Path(source_root).resolve(), Path(out_root).resolve()
    if (
        out_root == source_root
        or source_root in out_root.parents
        or out_root in source_root.parents
    ):
        raise QRDError("out_root and source_root must not contain each other")
    target = out_root / spec.id
    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    written: list[Path] = []
    rows = 0
    for rel, table in iter_partitions(spec, read_source(spec, source_root)):
        write_table(table, tmp / rel, int(spec.build.options.get("row_group_size", ROW_GROUP_SIZE)))
        written.append(target / rel)
        rows += table.num_rows
    if not written:
        raise QRDError(f"{spec.id}: the source produced no rows")
    if target.exists():
        shutil.rmtree(target)
    tmp.rename(target)
    log.info("built %s: %d files, %d rows", spec.id, len(written), rows)
    return written


def build_all(
    source_root: str | Path,
    out_root: str | Path,
    datasets: Iterable[str] | None = None,
    registry: Registry | None = None,
    version: str = "dev",
) -> Manifest:
    """Build the selected datasets (all by default) and write ``manifest.json``.

    The manifest always covers every dataset present under ``out_root``, so
    datasets can be rebuilt one at a time.
    """
    registry = registry or default_registry()
    specs = [registry.get(d) for d in datasets] if datasets else list(registry)
    out = Path(out_root)
    out.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        log.info("building %s", spec.id)
        build_dataset(spec, source_root, out)
    manifest = build_manifest(out, registry, version=version)
    manifest.save(out)
    return manifest
