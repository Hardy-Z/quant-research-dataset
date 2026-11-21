# quant-research-dataset

One Python API for research-grade market data across markets, served from a
versioned, partitioned Parquet dataset on the Hugging Face Hub.

```python
import quant_research_dataset as qrd

qrd.list_datasets()
df = qrd.load(
    "us/equity/stock_daily", start="2024-01-01", columns=["date", "permno", "ret"], common_only=True
)
```

* [Data dictionary](datasets.md): every dataset and column
* [Adding a dataset](adding-a-dataset.md)
* [Maintainer guide](maintainers.md): build, verify, publish

## Configuration

| Setting | Python | Environment variable | Default |
|---|---|---|---|
| Local data folder (skips the Hub) | `qrd.configure(data_dir=...)` | `QRD_DATA_DIR` | none |
| Hub dataset repo | `qrd.configure(repo_id=...)` | `QRD_REPO_ID` | `Hardy0102/quant-research-dataset` |
| Revision (branch or tag) | `qrd.configure(revision=...)` | `QRD_REVISION` | `main` |
| Download cache | `qrd.configure(cache_dir=...)` | `QRD_CACHE_DIR` | Hugging Face cache |
| Extra registry folders | | `QRD_REGISTRY_PATH` | none |
| Access token | `qrd.configure(token=...)` | `HF_TOKEN` | `hf auth login` |

## Command line

```text
qrd list [--market us] [--asset options]
qrd describe us_stock_daily
qrd download us_stock_daily --start 2024-01-01
qrd build | docs | verify | publish      # maintainers
```
