"""Market-specific logic, kept out of the generic loader.

An adapter can add a pushed-down row filter (e.g. "common stocks only"),
derived columns (e.g. option mid prices) or point-in-time fields to a dataset
at load time. Datasets pick an adapter with the ``adapter:`` key in their
registry YAML; datasets without one use the base :class:`Adapter`.
"""

from . import us_compustat, us_crsp, us_optionmetrics  # noqa: F401  (registers adapters)
from .base import Adapter, get_adapter, register_adapter

__all__ = ["Adapter", "get_adapter", "register_adapter"]
