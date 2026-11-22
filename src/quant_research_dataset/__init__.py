"""quant-research-dataset: one API for research-grade market data across markets.

>>> import quant_research_dataset as qrd
>>> qrd.list_datasets(market="us")                                     # doctest: +SKIP
>>> df = qrd.load("us/equity/stock_daily", start="2024-01-01",
...               columns=["date", "permno", "ret"], common_only=True)  # doctest: +SKIP

Generic API
    :func:`load`, :func:`list_datasets`, :func:`describe`, :func:`download`
Per-market shortcuts
    :mod:`qrd.us <quant_research_dataset.markets.us>`,
    :mod:`qrd.cn_hk <quant_research_dataset.markets.cn_hk>`
Research helpers
    :func:`quantile_portfolios`, :func:`performance_summary`
"""

from ._version import __version__
from .analytics import performance_summary, quantile_portfolios
from .config import configure, get_settings
from .errors import ConfigError, DatasetNotFoundError, ManifestError, QRDError, RegistryError
from .markets import cn_hk, get_prices, us
from .markets.us import (
    get_fundamentals,
    get_spx_options,
    get_stock_daily,
    get_vol_surface,
    merge_fundamentals,
    zero_rate,
)
from .query import describe, download, files_for, get_spec, list_datasets, load
from .registry import DatasetSpec, Registry, default_registry, load_registry
from .sql import duckdb_connect

__all__ = [
    "ConfigError",
    "DatasetNotFoundError",
    "DatasetSpec",
    "ManifestError",
    "QRDError",
    "Registry",
    "RegistryError",
    "__version__",
    "cn_hk",
    "configure",
    "default_registry",
    "describe",
    "download",
    "duckdb_connect",
    "files_for",
    "get_fundamentals",
    "get_prices",
    "get_settings",
    "get_spec",
    "get_spx_options",
    "get_stock_daily",
    "get_vol_surface",
    "list_datasets",
    "load",
    "load_registry",
    "merge_fundamentals",
    "performance_summary",
    "quantile_portfolios",
    "us",
    "zero_rate",
]
