"""OptionMetrics adapter: derived option fields."""

from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd

from ..registry import DatasetSpec
from .base import Adapter, register_adapter


@register_adapter
class OptionPricesAdapter(Adapter):
    """Options:

    ``derived``
        Add ``mid`` (bid/offer midpoint), ``spread`` (offer minus bid) and
        ``dte`` (calendar days to expiry). On by default.
    """

    name: ClassVar[str] = "us_option_prices"
    options: ClassVar[dict[str, Any]] = {"derived": True}

    def extra_columns(self, spec: DatasetSpec, options: dict[str, Any]) -> list[str]:
        return ["best_bid", "best_offer", "date", "exdate"] if options["derived"] else []

    def postprocess(
        self, df: pd.DataFrame, spec: DatasetSpec, options: dict[str, Any]
    ) -> pd.DataFrame:
        if not options["derived"]:
            return df
        bid, ask = df["best_bid"], df["best_offer"]
        dte = (pd.to_datetime(df["exdate"]) - pd.to_datetime(df["date"])).dt.days
        return df.assign(mid=(bid + ask) / 2.0, spread=ask - bid, dte=dte.astype("int32"))
