"""Query datasets with SQL through DuckDB (optional dependency).

>>> con = qrd.duckdb_connect(["us_stock_daily", "usd_zero_curve"], start="2024-01-01")  # doctest: +SKIP
>>> con.sql("select permno, avg(ret) from us_stock_daily group by 1").df()           # doctest: +SKIP

Each dataset becomes a view named after its first alias, e.g.
``us_stock_daily`` (or its key in a ``{name: dataset}`` mapping). Only partitions overlapping
``[start, end]`` are downloaded; the date filter itself is up to your SQL.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import QRDError
from .query import DateLike, files_for, get_spec


def _view_name(dataset: str) -> str:
    """Descriptive view name: the dataset's first alias, else the last id part."""
    spec = get_spec(dataset)
    return spec.aliases[0] if spec.aliases else spec.name


def duckdb_connect(
    datasets: Sequence[str] | Mapping[str, str],
    start: DateLike | None = None,
    end: DateLike | None = None,
    connection: Any = None,
) -> Any:
    """Return a DuckDB connection with one view per dataset."""
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise QRDError(
            "SQL support needs duckdb: pip install 'quant-research-dataset[duckdb]'"
        ) from exc

    con = connection or duckdb.connect()
    items = (
        datasets.items()
        if isinstance(datasets, Mapping)
        else ((_view_name(d), d) for d in datasets)
    )
    for view, dataset in items:
        if not view.isidentifier():
            raise QRDError(f"view name {view!r} is not a valid identifier")
        paths = [p.as_posix() for p in files_for(dataset, start, end)]
        if not paths:
            raise QRDError(f"no files for {dataset} in the requested range")
        file_list = ", ".join("'" + p.replace("'", "''") + "'" for p in paths)
        con.execute(f"create or replace view {view} as select * from read_parquet([{file_list}])")
    return con
