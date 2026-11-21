"""The manifest: an index of every prepared file.

``manifest.json`` sits at the root of the dataset repository. For each
dataset it lists the parquet files with their row counts, sizes, SHA-256
checksums and date ranges. The client reads it first, so a query for one year
of data downloads only the partitions that overlap that year.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq

from .errors import ManifestError
from .registry import DatasetSpec

MANIFEST_NAME = "manifest.json"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class FileEntry:
    path: str  # POSIX path relative to the dataset root
    rows: int
    bytes: int
    sha256: str
    start: str | None = None  # ISO date of the earliest row (UTC for timestamps)
    end: str | None = None

    def overlaps(self, start: dt.date | None, end: dt.date | None) -> bool:
        if self.start is None or self.end is None:
            return True
        if start is not None and dt.date.fromisoformat(self.end) < start:
            return False
        return not (end is not None and dt.date.fromisoformat(self.start) > end)


@dataclass(frozen=True)
class DatasetEntry:
    rows: int
    bytes: int
    files: tuple[FileEntry, ...]
    start: str | None = None
    end: str | None = None
    ids: int | None = None  # number of distinct values of the id column

    def select(self, start: dt.date | None = None, end: dt.date | None = None) -> list[FileEntry]:
        return [f for f in self.files if f.overlaps(start, end)]


@dataclass
class Manifest:
    datasets: dict[str, DatasetEntry]
    version: str = "dev"
    created_at: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    )
    format_version: int = FORMAT_VERSION

    def entry(self, dataset_id: str) -> DatasetEntry:
        try:
            return self.datasets[dataset_id]
        except KeyError:
            raise ManifestError(
                f"dataset {dataset_id!r} is registered but not present in this data source "
                f"(version {self.version}). It may not be published yet."
            ) from None

    # ---------------------------------------------------------------- (de)serialise
    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "version": self.version,
            "created_at": self.created_at,
            "datasets": {
                k: {**asdict(v), "files": [asdict(f) for f in v.files]}
                for k, v in sorted(self.datasets.items())
            },
        }

    def save(self, root: str | Path) -> Path:
        path = Path(root) / MANIFEST_NAME
        path.write_text(
            json.dumps(self.to_dict(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        if data.get("format_version") != FORMAT_VERSION:
            raise ManifestError(
                f"manifest format {data.get('format_version')} is not supported by this "
                f"library version (expected {FORMAT_VERSION}); try upgrading the package"
            )
        datasets = {
            k: DatasetEntry(
                rows=v["rows"],
                bytes=v["bytes"],
                files=tuple(FileEntry(**f) for f in v["files"]),
                start=v.get("start"),
                end=v.get("end"),
                ids=v.get("ids"),
            )
            for k, v in data["datasets"].items()
        }
        return cls(
            datasets=datasets,
            version=data.get("version", "dev"),
            created_at=data.get("created_at", ""),
        )

    @classmethod
    def load(cls, path: str | Path) -> Manifest:
        p = Path(path)
        if p.is_dir():
            p = p / MANIFEST_NAME
        if not p.exists():
            raise ManifestError(f"no {MANIFEST_NAME} found at {p}")
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


# ------------------------------------------------------------------- building
def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(dt.timezone.utc)
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)[:10]


def describe_file(path: Path, root: Path, spec: DatasetSpec) -> FileEntry:
    """Compute the manifest entry for one prepared parquet file."""
    meta = pq.read_metadata(path)
    start = end = None
    if spec.date_column is not None and meta.num_rows:
        col = pq.read_table(path, columns=[spec.date_column]).column(0)
        mm = pc.min_max(col)
        start, end = _iso_date(mm["min"].as_py()), _iso_date(mm["max"].as_py())
    return FileEntry(
        path=path.relative_to(root).as_posix(),
        rows=meta.num_rows,
        bytes=path.stat().st_size,
        sha256=sha256_file(path),
        start=start,
        end=end,
    )


def describe_dataset(spec: DatasetSpec, root: Path) -> DatasetEntry:
    folder = root / spec.id
    files = sorted(folder.rglob("*.parquet"))
    if not files:
        raise ManifestError(f"no parquet files found for {spec.id} under {folder}")
    entries = tuple(describe_file(f, root, spec) for f in files)
    starts = [e.start for e in entries if e.start]
    ends = [e.end for e in entries if e.end]
    ids = None
    if spec.id_column is not None:
        uniques: set[Any] = set()
        for f in files:
            uniques.update(
                pq.read_table(f, columns=[spec.id_column]).column(0).unique().to_pylist()
            )
        uniques.discard(None)
        ids = len(uniques)
    return DatasetEntry(
        rows=sum(e.rows for e in entries),
        bytes=sum(e.bytes for e in entries),
        files=entries,
        start=min(starts) if starts else None,
        end=max(ends) if ends else None,
        ids=ids,
    )


def build_manifest(
    root: str | Path, specs: Iterable[DatasetSpec], version: str = "dev"
) -> Manifest:
    """Scan ``root`` and build a manifest for every spec that has files there."""
    root = Path(root)
    datasets = {s.id: describe_dataset(s, root) for s in specs if (root / s.id).is_dir()}
    return Manifest(datasets=datasets, version=version)
