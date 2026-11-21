"""Exception types raised by the library."""

from __future__ import annotations


class QRDError(Exception):
    """Base class for all library errors."""


class DatasetNotFoundError(QRDError, KeyError):
    """Raised when a dataset id or alias is not in the registry."""

    def __str__(self) -> str:  # KeyError would otherwise wrap the message in quotes
        return str(self.args[0]) if self.args else ""


class RegistryError(QRDError):
    """Raised when a registry YAML entry is malformed."""


class ConfigError(QRDError):
    """Raised when the data source is not configured correctly."""


class ManifestError(QRDError):
    """Raised when the manifest is missing or does not match the registry."""
