"""Download the CSI 300 (HS300) stock data of FinMultiTime into a raw source folder.

FinMultiTime (Xu et al., 2025, arXiv:2506.05019) is published on Hugging Face
under the MIT license. This script fetches only its HS300 price series and
stock list, at a fixed revision, and lays them out as the registry expects::

    <out>/finmultitime/HS300_time_series/<symbol>.csv
    <out>/finmultitime/hs300_stocks.csv       (stock list, re-encoded to UTF-8)

Then build as usual::

    python scripts/fetch_csi300.py --out <raw root>
    qrd -v build --source <raw root> --out prepared --version 2025.12 \
        --dataset cn_hk/equity/csi300_stock_daily --dataset cn_hk/equity/csi300_stocks
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = (
    "Wenyan0110/"
    "Multimodal-Dataset-Image_Text_Table_TimeSeries-for-Financial-Time-Series-Forecasting"
)
REVISION = "72d4e97b9acb92651949b8efb22c55676ff633ff"
PRICES_ZIP = "time_series/HS300_time_series.zip"
STOCK_LIST = "hs300stock_data_description.csv"  # GBK-encoded
STOCK_LIST_COLUMNS = 7  # code, name, industry, then one 0/1 flag per modality


def _download(filename: str, cache: Path) -> Path:
    return Path(
        hf_hub_download(REPO_ID, filename, repo_type="dataset", revision=REVISION, local_dir=cache)
    )


def extract_prices(zip_path: Path, dest: Path) -> int:
    """Extract the per-stock CSV files flat into ``dest``; returns the file count."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name  # never trust paths inside the archive
            if info.is_dir() or not name.endswith(".csv"):
                continue
            with zf.open(info) as src, (dest / name).open("wb") as out:
                shutil.copyfileobj(src, out)
            count += 1
    return count


def convert_stock_list(src: Path, dest: Path) -> int:
    """Re-encode the stock list to UTF-8 and drop its trailing note columns."""
    rows = list(csv.reader(io.StringIO(src.read_bytes().decode("gbk"))))
    rows = [r[:STOCK_LIST_COLUMNS] for r in rows if r and r[0].strip()]
    with dest.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerows(rows)
    return len(rows) - 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="raw source root to write into")
    args = parser.parse_args(argv)

    target = args.out / "finmultitime"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        files = extract_prices(_download(PRICES_ZIP, cache), target / "HS300_time_series")
        stocks = convert_stock_list(_download(STOCK_LIST, cache), target / "hs300_stocks.csv")
    print(f"wrote {files} price files and {stocks} stocks under {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
