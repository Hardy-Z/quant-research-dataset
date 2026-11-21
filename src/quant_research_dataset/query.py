"""The generic query API: :func:`load`, :func:`list_datasets`, :func:`describe`."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from functools import reduce
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

from .adapters import get_adapter
from .errors import QRDError
from .registry import DatasetSpec, Registry, default_registry
from .storage import Backend, get_backend

DateLike = str | dt.date | dt.datetime | pd.Timestamp
Output = Literal["pandas", "arrow"]


# --------------------------------------------------------------------- helpers
def _is_date_only(value: DateLike) -> bool:
    if isinstance(value, str):
        return len(value.strip()) == 10
    if isinstance(value, pd.Timestamp | dt.datetime):
        return False
    return isinstance(value, dt.date)


def _to_timestamp(value: DateLike) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts is pd.NaT:
        raise QRDError(f"invalid date {value!r}")
    return ts


def _date_bounds(
    start: DateLike | None, end: DateLike | None
) -> tuple[dt.date | None, dt.date | None]:
    lo = _to_timestamp(start).date() if start is not None else None
    hi = _to_timestamp(end).date() if end is not None else None
    if lo and hi and lo > hi:
        raise QRDError(f"start {lo} is after end {hi}")
    return lo, hi


def _scalar_for(value: DateLike, typ: pa.DataType, *, end: bool) -> tuple[pa.Scalar, bool]:
    """Turn a user date into an Arrow scalar comparable with a column of ``typ``.

    Returns the scalar and whether the comparison is exclusive. A date-only
    ``end`` on a timestamp column means "through the end of that day".
    """
    ts = _to_timestamp(value)
    if pa.types.is_date(typ):
        return pa.scalar(ts.date(), type=typ), False
    if pa.types.is_timestamp(typ):
        if typ.tz is not None:
            ts = ts.tz_localize(typ.tz) if ts.tzinfo is None else ts.tz_convert(typ.tz)
        elif ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        if end and _is_date_only(value):
            return pa.scalar(ts + pd.Timedelta(days=1), type=typ), True
        return pa.scalar(ts, type=typ), False
    raise QRDError(f"cannot filter a {typ} column by date")


def _values_for(values: Iterable[Any], typ: pa.DataType) -> pa.Array:
    try:
        return pa.array(list(values)).cast(typ)
    except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError) as exc:
        raise QRDError(f"cannot use {list(values)[:5]} as values of a {typ} column") from exc


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Iterable):
        return [value]
    return list(value)


def build_filter(
    spec: DatasetSpec,
    ids: Any = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    filters: Mapping[str, Any] | None = None,
) -> pc.Expression | None:
    """Build the Arrow filter for a :func:`load` call."""
    schema = spec.schema
    parts: list[pc.Expression] = []
    if ids is not None:
        if spec.id_column is None:
            raise QRDError(f"{spec.id} has no id column; use filters= instead")
        typ = schema.field(spec.id_column).type
        parts.append(pc.field(spec.id_column).isin(_values_for(_as_list(ids), typ)))
    if start is not None or end is not None:
        if spec.date_column is None:
            raise QRDError(f"{spec.id} has no date column, so start/end cannot be used")
        typ = schema.field(spec.date_column).type
        if start is not None:
            lo, _ = _scalar_for(start, typ, end=False)
            parts.append(pc.field(spec.date_column) >= lo)
        if end is not None:
            hi, exclusive = _scalar_for(end, typ, end=True)
            field = pc.field(spec.date_column)
            parts.append(field < hi if exclusive else field <= hi)
    for col, cond in (filters or {}).items():
        if col not in spec.column_names:
            raise QRDError(f"{spec.id} has no column {col!r} to filter on")
        typ = schema.field(col).type
        if isinstance(cond, pc.Expression):
            parts.append(cond)
        elif isinstance(cond, tuple) and len(cond) == 2 and cond[0] in _OPS:
            op, val = cond
            parts.append(_OPS[op](pc.field(col), pa.scalar(val).cast(typ)))
        else:
            parts.append(pc.field(col).isin(_values_for(_as_list(cond), typ)))
    return reduce(lambda a, b: a & b, parts) if parts else None


_OPS = {
    "==": lambda f, v: f == v,
    "!=": lambda f, v: f != v,
    ">": lambda f, v: f > v,
    ">=": lambda f, v: f >= v,
    "<": lambda f, v: f < v,
    "<=": lambda f, v: f <= v,
}


def to_pandas(table: pa.Table) -> pd.DataFrame:
    """Arrow to pandas with dates as ``datetime64`` rather than Python objects."""
    return table.to_pandas(date_as_object=False)


# ------------------------------------------------------------------ public API
def list_datasets(
    market: str | None = None,
    asset_class: str | None = None,
    frequency: str | None = None,
    *,
    registry: Registry | None = None,
) -> pd.DataFrame:
    """List registered datasets, optionally filtered by market, asset class or frequency.

    >>> qrd.list_datasets(market="us", asset_class="options")   # doctest: +SKIP
    """
    registry = registry or default_registry()
    rows = [
        {
            "id": s.id,
            "title": s.title,
            "market": s.market,
            "asset_class": s.asset_class,
            "frequency": s.frequency,
            "id_column": s.id_column,
            "date_column": s.date_column,
            "source": s.source,
        }
        for s in registry.filter(market, asset_class, frequency)
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "id",
            "title",
            "market",
            "asset_class",
            "frequency",
            "id_column",
            "date_column",
            "source",
        ],
    )


def get_spec(dataset: str, registry: Registry | None = None) -> DatasetSpec:
    """Return the :class:`~.registry.DatasetSpec` for an id or alias."""
    return (registry or default_registry()).get(dataset)


def describe(
    dataset: str,
    *,
    registry: Registry | None = None,
    backend: Backend | None = None,
    coverage: bool = True,
) -> dict[str, Any]:
    """Everything known about a dataset: metadata, columns and (if reachable) coverage.

    ``coverage`` adds row counts and date range from the manifest, which needs
    the data source to be reachable.
    """
    spec = get_spec(dataset, registry)
    info: dict[str, Any] = {
        "id": spec.id,
        "title": spec.title,
        "description": spec.description,
        "market": spec.market,
        "asset_class": spec.asset_class,
        "frequency": spec.frequency,
        "source": spec.source,
        "license": spec.license,
        "id_column": spec.id_column,
        "date_column": spec.date_column,
        "partitioning": spec.partitioning,
        "aliases": list(spec.aliases),
        "load_options": dict(get_adapter(spec.adapter).options),
        "notes": list(spec.notes),
        "columns": pd.DataFrame(
            [
                {"name": c.name, "type": c.type, "unit": c.unit, "description": c.description}
                for c in spec.columns
            ]
        ),
    }
    if coverage:
        entry = (backend or get_backend()).manifest().entry(spec.id)
        info.update(
            rows=entry.rows,
            size_mb=round(entry.bytes / 1e6, 1),
            start=entry.start,
            end=entry.end,
            n_ids=entry.ids,
            n_files=len(entry.files),
        )
    return info


def files_for(
    dataset: str,
    start: DateLike | None = None,
    end: DateLike | None = None,
    *,
    registry: Registry | None = None,
    backend: Backend | None = None,
) -> list[Path]:
    """Local paths of the partitions covering ``[start, end]``, downloading them if needed."""
    spec = get_spec(dataset, registry)
    backend = backend or get_backend()
    lo, hi = _date_bounds(start, end)
    entries = backend.manifest().entry(spec.id).select(lo, hi)
    return backend.fetch([e.path for e in entries])


def download(
    dataset: str,
    start: DateLike | None = None,
    end: DateLike | None = None,
    **kwargs: Any,
) -> list[Path]:
    """Pre-fetch partitions into the local cache (e.g. before going offline)."""
    return files_for(dataset, start, end, **kwargs)


def load(
    dataset: str,
    ids: Any = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    *,
    output: Output = "pandas",
    registry: Registry | None = None,
    backend: Backend | None = None,
    **options: Any,
) -> pd.DataFrame | pa.Table:
    """Load rows of any registered dataset.

    Parameters
    ----------
    dataset:
        Dataset id such as ``"us/equity/crsp_daily"``, or an alias such as
        ``"crsp_daily"``. See :func:`list_datasets`.
    ids:
        One value or a list of values of the dataset's id column (for
        example PERMNOs for CRSP, ``gvkey`` for Compustat, symbols for ETFs).
    start, end:
        Inclusive date range on the dataset's date column. For intraday data
        a date-only ``end`` includes the whole day. Naive times are UTC.
    columns:
        Columns to return (default: all). Only these columns are read.
    filters:
        Extra conditions, ``{column: value}``, ``{column: [values]}`` or
        ``{column: (op, value)}`` with op in ``== != > >= < <=``.
    output:
        ``"pandas"`` (default) or ``"arrow"``.
    **options:
        Dataset-specific options handled by its adapter, for example
        ``common_only=True`` for CRSP or ``point_in_time=True`` for
        Compustat. ``describe(dataset)["load_options"]`` lists them.

    Only partitions overlapping ``[start, end]`` are downloaded, and filters
    are pushed down into the parquet scan, so small queries stay fast.
    """
    registry = registry or default_registry()
    spec = registry.get(dataset)
    adapter = get_adapter(spec.adapter)
    opts = adapter.resolve_options(spec, options)
    backend = backend or get_backend()

    if columns is not None:
        columns = list(columns)
        unknown = [c for c in columns if c not in spec.column_names]
        if unknown:
            raise QRDError(f"{spec.id} has no columns {unknown}; available: {spec.column_names}")
    expr = build_filter(spec, ids, start, end, filters)
    extra = adapter.row_filter(spec, opts)
    if extra is not None:
        expr = extra if expr is None else expr & extra

    lo, hi = _date_bounds(start, end)
    entries = backend.manifest().entry(spec.id).select(lo, hi)
    read_cols = None
    if columns is not None:
        needed = [c for c in adapter.extra_columns(spec, opts) if c not in columns]
        read_cols = columns + needed
    if entries:
        paths = backend.fetch([e.path for e in entries])
        dataset_ = ds.dataset([str(p) for p in paths], format="parquet", schema=spec.schema)
        table = dataset_.to_table(columns=read_cols, filter=expr)
    else:
        schema = (
            spec.schema
            if read_cols is None
            else pa.schema([spec.schema.field(c) for c in read_cols])
        )
        table = schema.empty_table()

    sort_keys = [c for c in spec.sort_by if c in table.column_names]
    if sort_keys and table.num_rows:
        table = table.sort_by([(c, "ascending") for c in sort_keys])

    if output == "arrow":
        if columns is not None:
            table = table.select(columns)
        return table
    if output != "pandas":
        raise QRDError(f"output must be 'pandas' or 'arrow', not {output!r}")

    df = adapter.postprocess(to_pandas(table), spec, opts)
    if columns is not None:
        derived = [c for c in df.columns if c not in spec.column_names]
        df = df[columns + derived]
    return df.reset_index(drop=True)
