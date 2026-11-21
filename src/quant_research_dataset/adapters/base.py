"""Adapter base class and lookup."""

from __future__ import annotations

from typing import Any, ClassVar, TypeVar

import pandas as pd
import pyarrow.compute as pc

from ..errors import QRDError
from ..registry import DatasetSpec

_ADAPTERS: dict[str, type[Adapter]] = {}
AdapterType = TypeVar("AdapterType", bound="type[Adapter]")


class Adapter:
    """Load-time hooks for a dataset.

    Subclasses declare the keyword options they accept in ``options`` (name
    to default value). :func:`quant_research_dataset.load` forwards extra
    keyword arguments to the adapter and rejects options it does not declare.
    """

    name: ClassVar[str] = "default"
    options: ClassVar[dict[str, Any]] = {}

    def resolve_options(self, spec: DatasetSpec, given: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(given) - set(self.options))
        if unknown:
            allowed = ", ".join(sorted(self.options)) or "none"
            raise QRDError(f"{spec.id} does not accept options {unknown} (allowed: {allowed})")
        return {**self.options, **given}

    def row_filter(self, spec: DatasetSpec, options: dict[str, Any]) -> pc.Expression | None:
        """An Arrow filter pushed down into the parquet scan, or ``None``."""
        return None

    def extra_columns(self, spec: DatasetSpec, options: dict[str, Any]) -> list[str]:
        """Columns :meth:`postprocess` needs even if the caller did not ask for them."""
        return []

    def postprocess(
        self, df: pd.DataFrame, spec: DatasetSpec, options: dict[str, Any]
    ) -> pd.DataFrame:
        """Add derived columns after the scan."""
        return df


def register_adapter(cls: AdapterType) -> AdapterType:
    """Class decorator that makes an adapter available by its ``name``."""
    _ADAPTERS[cls.name] = cls
    return cls


register_adapter(Adapter)


def get_adapter(name: str) -> Adapter:
    try:
        return _ADAPTERS[name]()
    except KeyError:
        raise QRDError(f"unknown adapter {name!r}; known: {sorted(_ADAPTERS)}") from None
