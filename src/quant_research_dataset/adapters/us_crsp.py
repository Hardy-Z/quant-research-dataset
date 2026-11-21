"""CRSP (US stocks) adapter."""

from __future__ import annotations

from functools import reduce
from typing import Any, ClassVar

import pyarrow.compute as pc

from ..registry import DatasetSpec
from .base import Adapter, register_adapter

#: The usual "ordinary common stock" screen in CRSP CIZ flags: common shares
#: of US-incorporated companies, listed on NYSE, NYSE American or Nasdaq,
#: trading regular way and active. It is the CIZ equivalent of the classic
#: ``shrcd in (10, 11)`` and ``exchcd in (1, 2, 3)`` filter.
COMMON_STOCK_SCREEN: dict[str, tuple[str, ...]] = {
    "share_type": ("NS",),
    "security_type": ("EQTY",),
    "security_sub_type": ("COM",),
    "us_inc_flg": ("Y",),
    "issuer_type": ("CORP", "ACOR"),
    "primary_exch": ("N", "A", "Q"),
    "conditional_type": ("RW",),
    "trading_status_flg": ("A",),
}


def common_stock_expression() -> pc.Expression:
    """Arrow filter for :data:`COMMON_STOCK_SCREEN`."""
    parts = [pc.field(col).isin(list(values)) for col, values in COMMON_STOCK_SCREEN.items()]
    return reduce(lambda a, b: a & b, parts)


@register_adapter
class CRSPAdapter(Adapter):
    """Options:

    ``common_only``
        Keep only ordinary common shares (see :data:`COMMON_STOCK_SCREEN`),
        the standard universe for cross-sectional equity research.
    """

    name: ClassVar[str] = "us_crsp"
    options: ClassVar[dict[str, Any]] = {"common_only": False}

    def row_filter(self, spec: DatasetSpec, options: dict[str, Any]) -> pc.Expression | None:
        return common_stock_expression() if options["common_only"] else None
