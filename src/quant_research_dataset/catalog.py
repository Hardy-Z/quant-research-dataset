"""Generate human-readable docs from the registry: the data dictionary and the
Hugging Face dataset card. Both are rebuilt from YAML, so they never drift
from the code."""

from __future__ import annotations

from collections.abc import Iterable

import yaml

from .manifest import Manifest
from .registry import DatasetSpec, Registry


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _coverage(spec: DatasetSpec, manifest: Manifest | None) -> str:
    if manifest is None or spec.id not in manifest.datasets:
        return ""
    e = manifest.datasets[spec.id]
    span = f"{e.start} to {e.end}, " if e.start else ""
    ids = f", {e.ids:,} distinct `{spec.id_column}`" if e.ids is not None else ""
    return f"**Coverage:** {span}{e.rows:,} rows{ids}, {e.bytes / 1e6:,.1f} MB in {len(e.files)} file(s).\n\n"


def render_dataset_section(
    spec: DatasetSpec, manifest: Manifest | None = None, level: int = 3
) -> str:
    h = "#" * level
    lines = [
        f"{h} `{spec.id}`: {spec.title}\n",
        f"{spec.description}\n",
        f"**Source:** {spec.source}  ",
        f"**License:** {spec.license}  ",
        f"**Frequency:** {spec.frequency}  ",
        f"**Keys:** id `{spec.id_column or '-'}`, date `{spec.date_column or '-'}`  ",
        f"**Aliases:** {', '.join(f'`{a}`' for a in (spec.name, *spec.aliases))}\n",
        _coverage(spec, manifest),
    ]
    if spec.notes:
        lines += ["**Notes**\n", *[f"- {n}" for n in spec.notes], ""]
    lines += ["| Column | Type | Unit | Description |", "|---|---|---|---|"]
    lines += [
        f"| `{c.name}` | {c.type} | {_md_escape(c.unit or '')} | {_md_escape(c.description)} |"
        for c in spec.columns
    ]
    return "\n".join(lines) + "\n"


def render_data_dictionary(registry: Registry, manifest: Manifest | None = None) -> str:
    """Markdown data dictionary for every registered dataset."""
    out = [
        "# Data dictionary\n",
        "Generated from the dataset registry by `qrd docs`. Do not edit by hand.\n",
        "| Dataset | Title | Frequency | Source |",
        "|---|---|---|---|",
    ]
    specs = list(registry)
    out += [
        f"| [`{s.id}`](#{s.id.replace('/', '')}) | {s.title} | {s.frequency} | {s.source} |"
        for s in specs
    ]
    out.append("")
    market = None
    for s in specs:
        if s.market != market:
            market = s.market
            out.append(f"## Market: `{market}`\n")
        out.append(render_dataset_section(s, manifest))
    return "\n".join(out)


def _size_category(rows: int) -> str:
    for limit, label in [
        (1_000, "n<1K"),
        (10_000, "1K<n<10K"),
        (100_000, "10K<n<100K"),
        (1_000_000, "100K<n<1M"),
        (10_000_000, "1M<n<10M"),
        (100_000_000, "10M<n<100M"),
        (1_000_000_000, "100M<n<1B"),
    ]:
        if rows < limit:
            return label
    return "n>1B"


def render_dataset_card(
    registry: Registry,
    manifest: Manifest,
    repo_id: str,
    specs: Iterable[DatasetSpec] | None = None,
) -> str:
    """The README.md for the Hugging Face dataset repository."""
    specs = [s for s in (specs or registry) if s.id in manifest.datasets]
    total_rows = sum(manifest.datasets[s.id].rows for s in specs)
    header = {
        "pretty_name": "Quant Research Dataset",
        "license": "other",
        "license_name": "vendor-terms",
        "language": ["en"],
        "tags": [
            "finance",
            "stocks",
            "options",
            "fundamentals",
            "time-series",
            "quantitative-finance",
        ],
        "size_categories": [_size_category(total_rows)],
        "configs": [
            {"config_name": s.id.replace("/", "__"), "data_files": f"{s.id}/**/*.parquet"}
            for s in specs
        ],
        "extra_gated_prompt": (
            "Parts of this dataset are licensed from data vendors (CRSP, S&P Compustat, "
            "OptionMetrics, via WRDS). Access is granted for non-commercial academic research "
            "only, and only to people who confirm they may use these sources."
        ),
        "extra_gated_fields": {
            "Full name": "text",
            "Affiliation (university or company)": "text",
            "Intended use": "text",
            "I have, or my institution has, a current WRDS subscription covering CRSP, Compustat and OptionMetrics": "checkbox",
            "I will not redistribute the data": "checkbox",
        },
    }
    front = yaml.safe_dump(header, sort_keys=False, allow_unicode=True, width=1000)
    rows = "\n".join(
        f"| `{s.id}` | {s.title} | {manifest.datasets[s.id].start or '-'} | "
        f"{manifest.datasets[s.id].end or '-'} | {manifest.datasets[s.id].rows:,} |"
        for s in specs
    )
    body = f"""# Quant Research Dataset

Research-grade market data in one place, organized as `market/asset_class/dataset`
and stored as partitioned Parquet. Version `{manifest.version}`.

The companion Python package [`quant-research-dataset`](https://github.com/Hardy-Z/quant-research-dataset)
downloads only the partitions a query needs:

```python
import quant_research_dataset as qrd

qrd.list_datasets()
crsp = qrd.load("us/equity/crsp_daily", start="2024-01-01", end="2024-12-31",
                columns=["date", "permno", "ret", "mktcap"], common_only=True)
```

## Datasets

| Dataset | Title | Start | End | Rows |
|---|---|---|---|---|
{rows}

## Layout

```
<market>/<asset_class>/<dataset>/year=YYYY[/month=MM]/part-0.parquet
<market>/<asset_class>/<dataset>/data.parquet      # small, unpartitioned tables
manifest.json                                      # files, row counts, SHA-256, date ranges
```

## License and access

The code is MIT licensed. The data is not: each dataset keeps the terms of its
vendor (see the table below and `describe()` in the package). Access is gated
and approved by hand. Do not redistribute the files.

## Data dictionary

"""
    sections = "\n".join(render_dataset_section(s, manifest, level=3) for s in specs)
    return f"---\n{front}---\n\n{body}{sections}"
