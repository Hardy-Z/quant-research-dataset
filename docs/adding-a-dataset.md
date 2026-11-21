# Adding a dataset

A dataset is one YAML file under `src/quant_research_dataset/registry/<market>/<asset_class>/<name>.yaml`
(or in a folder listed in `QRD_REGISTRY_PATH`, for private datasets). The build
pipeline, the loader, the data dictionary and the Hub dataset card all read it.

## Example

```yaml
id: jp/equity/topix_daily          # market/asset_class/name; also the storage path
title: TOPIX constituents daily bars
aliases: [topix]                   # optional short names for qrd.load()
market: jp                         # must match the id
asset_class: equity                # must match the id
frequency: daily                   # static | intraday | daily | monthly | quarterly | annual
source: Vendor X end-of-day file
license: Vendor X terms
publish: false                     # true = included by `qrd publish`
description: >
  One paragraph on what the data is and what it is good for.
id_column: code                    # what `ids=` filters on (optional)
date_column: date                  # what `start=`/`end=` filter on (required if partitioned)
partitioning: year                 # none | year | year_month
sort_by: [code, date]              # row order inside each file
adapter: default                   # load-time logic, see below
notes:
  - "Anything a user must know, e.g. units or known gaps."
build:
  source: vendor_x/topix_*.csv     # glob(s) relative to the raw source root
  format: csv                      # parquet | csv
  options:                         # all optional
    id_from_filename: '^(?P<id>\d+)_daily\.csv$'   # take the id from each file name
    timezone: Asia/Tokyo           # localise naive timestamps before converting to UTC
    null_tokens: {EndDate: ["E"]}  # raw values that mean null
    scale: {strike: 0.001}         # multiply a column after renaming
    row_group_size: 131072
  include_ids: []                  # keep only these ids
  exclude_ids: []                  # drop these ids
columns:
  - {name: code, type: string, description: Local security code}
  - {name: date, source: TradeDate, type: date32, description: Trading date}
  - {name: close, source: Close, type: float64, unit: JPY, description: Closing price}
```

Column `type` is one of `bool`, `int8/16/32/64`, `float32/64`, `string`,
`date32`, `timestamp[us, UTC]`, `timestamp[us]`. `source` is the raw column
name when it differs from `name`. CSV columns are read as text and converted
explicitly, so identifiers with leading zeros survive.

## Columns computed at build time

A column can be derived from other source files instead of read from the raw
table. Mark it `derived: true` and name an enrichment step in
`build.options.enrich`. For example, US daily stocks get the company key that
was linked to each stock on each date:

```yaml
build:
  source: WRDS_data/crsp/crsp_daily_stock_*.parquet
  options:
    enrich: {function: us_stock_gvkey, source: WRDS_data/crsp/ccm_link_table.csv}
columns:
  - {name: gvkey, type: string, derived: true, description: Linked company key}
```

Steps are registered with `quant_research_dataset.links.register_enricher`.

## Build and check

```bash
qrd build --source <raw root> --out prepared --dataset jp/equity/topix_daily
qrd verify --data-dir prepared
qrd docs --data-dir prepared          # refresh docs/datasets.md
pytest                                # the registry tests validate every YAML file
```

## Load-time logic (adapters)

If users need a standard filter or derived fields, write an adapter:

```python
from typing import Any, ClassVar
import pyarrow.compute as pc
from quant_research_dataset.adapters import Adapter, register_adapter


@register_adapter
class TopixAdapter(Adapter):
    name: ClassVar[str] = "jp_topix"
    options: ClassVar[dict[str, Any]] = {"prime_only": False}

    def row_filter(self, spec, options):
        return pc.field("segment") == "Prime" if options["prime_only"] else None
```

then set `adapter: jp_topix` in the YAML. Users call
`qrd.load("topix", prime_only=True)`; unknown options are rejected with a clear
error. For convenience functions, add a module under `markets/`.
