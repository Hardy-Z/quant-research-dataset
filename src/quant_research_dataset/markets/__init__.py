"""Per-market convenience functions built on the generic :func:`load`.

Each market lives in its own module (``us``, ``cn_hk``) so new markets can be
added without touching existing code. :func:`get_prices` dispatches to the
main daily equity dataset of a market.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from ..errors import QRDError
from ..query import DateLike, load
from . import cn_hk, us

#: Main daily equity price dataset of each market.
PRICE_DATASETS: dict[str, str] = {
    "us": "us/equity/crsp_daily",
    "cn_hk": "cn_hk/equity/daily_bars",
}


def get_prices(
    ids: Any = None,
    start: DateLike | None = None,
    end: DateLike | None = None,
    columns: Sequence[str] | None = None,
    *,
    market: str = "us",
    **options: Any,
) -> pd.DataFrame:
    """Daily equity prices for any market (PERMNOs for ``us``, symbols for ``cn_hk``).

    Extra keyword options go to the dataset's adapter, e.g. ``common_only=True``.
    """
    try:
        dataset = PRICE_DATASETS[market]
    except KeyError:
        raise QRDError(
            f"no price dataset for market {market!r}; known: {sorted(PRICE_DATASETS)}"
        ) from None
    df = load(dataset, ids, start, end, columns, **options)
    assert isinstance(df, pd.DataFrame)
    return df


__all__ = ["PRICE_DATASETS", "cn_hk", "get_prices", "us"]
