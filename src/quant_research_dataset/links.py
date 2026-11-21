"""Build-time enrichment steps, such as adding linked identifiers.

A dataset opts in with ``build.options.enrich: {function: <name>, ...}`` in
its registry YAML and declares the added columns with ``derived: true``. The
build calls the step once per output partition, after the raw columns have
been standardized.

The US steps use the CRSP/Compustat (CCM) link table so that stock prices
carry a company key (``gvkey``) and fundamentals carry a stock key
(``permno``). Users can then join the two directly, with the standard link
rules already applied.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from .errors import QRDError
from .registry import DatasetSpec

Enricher = Callable[[pa.Table], pa.Table]
EnricherFactory = Callable[[DatasetSpec, Path, dict[str, Any]], Enricher]

ENRICHERS: dict[str, EnricherFactory] = {}

#: Standard CCM link filters: usable link types, and primary links only.
LINK_TYPES = ("LC", "LU")
LINK_PRIMARY = ("P", "C")  # P is ranked ahead of C when both match


def register_enricher(name: str) -> Callable[[EnricherFactory], EnricherFactory]:
    def deco(factory: EnricherFactory) -> EnricherFactory:
        ENRICHERS[name] = factory
        return factory

    return deco


def make_enricher(spec: DatasetSpec, source_root: Path) -> Enricher | None:
    """The enrichment step for ``spec``, or ``None`` if it has none."""
    params = spec.build.options.get("enrich")
    if not params:
        return None
    name = params.get("function")
    if name not in ENRICHERS:
        raise QRDError(f"{spec.id}: unknown enrich function {name!r}; known: {sorted(ENRICHERS)}")
    return ENRICHERS[name](spec, source_root, params)


# ---------------------------------------------------------------- CCM links
def read_ccm_links(path: Path) -> pd.DataFrame:
    """Read the raw CCM link table and apply the standard filters.

    Returns ``gvkey, permno, linkdt, linkenddt, rank`` where ``linkenddt`` is
    NaT for links that are still active (raw value ``E``) and ``rank`` is 0
    for ``LINKPRIM = P`` and 1 for ``C``.
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh))
    raw = pacsv.read_csv(
        path, convert_options=pacsv.ConvertOptions(column_types={c: pa.string() for c in header})
    ).to_pandas()
    raw = raw[raw["LINKTYPE"].isin(LINK_TYPES) & raw["LINKPRIM"].isin(LINK_PRIMARY)]
    links = pd.DataFrame(
        {
            "gvkey": raw["gvkey"],
            "permno": pd.to_numeric(raw["LPERMNO"]).astype("int64"),
            "linkdt": pd.to_datetime(raw["LINKDT"]),
            "linkenddt": pd.to_datetime(raw["LINKENDDT"].where(raw["LINKENDDT"] != "E")),
            "rank": (raw["LINKPRIM"] != "P").astype("int8"),
        }
    )
    return links.reset_index(drop=True)


def match_links(
    keys: pd.DataFrame, links: pd.DataFrame, on: str, date_col: str, out: str
) -> np.ndarray:
    """For each row of ``keys`` return ``links[out]`` of the link valid on its date.

    When several links are valid, the primary one (``rank`` 0) wins, then the
    smallest identifier, so the result is deterministic. Rows without a valid
    link get null.
    """
    left = pd.DataFrame(
        {
            on: keys[on].to_numpy(),
            "d": pd.to_datetime(keys[date_col]).to_numpy(),
            "_row": np.arange(len(keys)),
        }
    )
    cand = left.merge(links[[on, out, "linkdt", "linkenddt", "rank"]], on=on)
    valid = (cand["d"] >= cand["linkdt"]) & (
        cand["linkenddt"].isna() | (cand["d"] <= cand["linkenddt"])
    )
    best = cand[valid].sort_values(["_row", "rank", out]).drop_duplicates("_row")
    result = np.full(len(keys), None, dtype=object)
    result[best["_row"].to_numpy()] = best[out].to_numpy()
    return result


def _set(table: pa.Table, name: str, values: np.ndarray, typ: pa.DataType) -> pa.Table:
    arr = pa.array(list(values), type=typ)
    if name in table.column_names:
        return table.set_column(table.column_names.index(name), name, arr)
    return table.append_column(name, arr)


def _link_source(spec: DatasetSpec, source_root: Path, params: dict[str, Any]) -> pd.DataFrame:
    rel = params.get("source")
    if not rel:
        raise QRDError(f"{spec.id}: enrich step needs a 'source' path to the link table")
    path = source_root / rel
    if not path.exists():
        raise QRDError(f"{spec.id}: link table {path} not found")
    return read_ccm_links(path)


@register_enricher("us_stock_gvkey")
def _stock_gvkey(spec: DatasetSpec, source_root: Path, params: dict[str, Any]) -> Enricher:
    """Add ``gvkey`` to daily stock rows, using the link valid on each date."""
    links = _link_source(spec, source_root, params)
    links = links.assign(permno=links["permno"].astype("int32"))

    def enrich(table: pa.Table) -> pa.Table:
        keys = table.select(["permno", "date"]).to_pandas(date_as_object=False)
        return _set(
            table, "gvkey", match_links(keys, links, "permno", "date", "gvkey"), pa.string()
        )

    return enrich


@register_enricher("us_fundamentals_permno")
def _fundamentals_permno(spec: DatasetSpec, source_root: Path, params: dict[str, Any]) -> Enricher:
    """Add the primary share class ``permno`` to fundamentals, as linked on ``datadate``."""
    links = _link_source(spec, source_root, params)

    def enrich(table: pa.Table) -> pa.Table:
        keys = table.select(["gvkey", "datadate"]).to_pandas(date_as_object=False)
        permno = match_links(keys, links, "gvkey", "datadate", "permno")
        return _set(table, "permno", permno, pa.int32())

    return enrich
