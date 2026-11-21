"""Compustat fundamentals adapter: point-in-time availability dates."""

from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd

from ..registry import DatasetSpec
from .base import Adapter, register_adapter

#: Conservative reporting lags used when the report date is unknown.
DEFAULT_LAG_DAYS = {"quarterly": 90, "annual": 180}


def available_date(
    df: pd.DataFrame,
    frequency: str,
    lag_days: int | None = None,
    report_date_col: str = "rdq",
) -> pd.Series:
    """Date from which a fundamentals row was known to investors.

    Uses the earnings report date (``rdq``) when there is one, otherwise the
    fiscal period end (``datadate``) plus a fixed lag: 90 days for quarterly
    and 180 days for annual data by default. Joining on this date instead of
    ``datadate`` avoids look-ahead bias in backtests.
    """
    lag = pd.Timedelta(days=lag_days if lag_days is not None else DEFAULT_LAG_DAYS[frequency])
    fallback = pd.to_datetime(df["datadate"]) + lag
    if report_date_col in df.columns:
        return pd.to_datetime(df[report_date_col]).fillna(fallback).rename("available_date")
    return fallback.rename("available_date")


@register_adapter
class CompustatAdapter(Adapter):
    """Options:

    ``point_in_time``
        Add an ``available_date`` column (see :func:`available_date`).
    ``lag_days``
        Lag used when the report date is missing. Defaults to 90 days
        (quarterly) or 180 days (annual).
    """

    name: ClassVar[str] = "us_compustat"
    options: ClassVar[dict[str, Any]] = {"point_in_time": False, "lag_days": None}

    def extra_columns(self, spec: DatasetSpec, options: dict[str, Any]) -> list[str]:
        if not options["point_in_time"]:
            return []
        return ["datadate", *(["rdq"] if "rdq" in spec.column_names else [])]

    def postprocess(
        self, df: pd.DataFrame, spec: DatasetSpec, options: dict[str, Any]
    ) -> pd.DataFrame:
        if options["point_in_time"]:
            df = df.assign(available_date=available_date(df, spec.frequency, options["lag_days"]))
        return df
