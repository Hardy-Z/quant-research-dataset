"""Storage backends: where prepared parquet files come from.

A backend does two things: return the :class:`~.manifest.Manifest`, and turn
manifest paths into local file paths (downloading them first if needed).
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from .config import Settings, get_settings
from .errors import ConfigError, ManifestError
from .manifest import MANIFEST_NAME, Manifest


class Backend(Protocol):
    def manifest(self) -> Manifest: ...

    def fetch(self, paths: Sequence[str]) -> list[Path]: ...

    def describe(self) -> str: ...


class LocalBackend:
    """Read prepared files from a directory on disk."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        if not self.root.is_dir():
            raise ConfigError(f"data directory {self.root} does not exist")
        self._manifest: Manifest | None = None

    def manifest(self) -> Manifest:
        if self._manifest is None:
            self._manifest = Manifest.load(self.root / MANIFEST_NAME)
        return self._manifest

    def fetch(self, paths: Sequence[str]) -> list[Path]:
        out = [self.root / p for p in paths]
        missing = [str(p) for p in out if not p.exists()]
        if missing:
            raise ManifestError(f"files listed in the manifest are missing: {missing[:3]}")
        return out

    def describe(self) -> str:
        return f"local directory {self.root}"


class HubBackend:
    """Download prepared files from a Hugging Face dataset repository.

    Files are cached by ``huggingface_hub``, so each partition is downloaded
    once per revision. Private and gated repos need a token: run
    ``hf auth login`` or set ``HF_TOKEN``.
    """

    def __init__(
        self,
        repo_id: str,
        revision: str = "main",
        cache_dir: str | Path | None = None,
        token: str | None = None,
        max_workers: int = 8,
    ):
        self.repo_id = repo_id
        self.revision = revision
        self.cache_dir = cache_dir
        self.token = token
        self.max_workers = max_workers
        self._manifest: Manifest | None = None

    def _download(self, filename: str) -> Path:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError

        try:
            return Path(
                hf_hub_download(
                    repo_id=self.repo_id,
                    filename=filename,
                    repo_type="dataset",
                    revision=self.revision,
                    cache_dir=self.cache_dir,
                    token=self.token,
                )
            )
        except GatedRepoError as exc:
            raise ConfigError(
                f"{self.repo_id} is gated: request access on its Hugging Face page, then log in "
                "with `hf auth login` or set HF_TOKEN"
            ) from exc
        except RepositoryNotFoundError as exc:
            raise ConfigError(
                f"dataset repo {self.repo_id!r} not found, or it is private and no valid token "
                "was given. Log in with `hf auth login` or set HF_TOKEN."
            ) from exc

    def manifest(self) -> Manifest:
        if self._manifest is None:
            self._manifest = Manifest.load(self._download(MANIFEST_NAME))
        return self._manifest

    def fetch(self, paths: Sequence[str]) -> list[Path]:
        if len(paths) <= 1:
            return [self._download(p) for p in paths]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(self._download, paths))

    def describe(self) -> str:
        return f"Hugging Face dataset {self.repo_id}@{self.revision}"


def backend_from_settings(settings: Settings) -> Backend:
    if settings.data_dir is not None:
        return LocalBackend(settings.data_dir)
    return HubBackend(
        repo_id=settings.repo_id,
        revision=settings.revision,
        cache_dir=settings.cache_dir,
        token=settings.token,
    )


@lru_cache(maxsize=4)
def _cached_backend(settings: Settings) -> Backend:
    return backend_from_settings(settings)


def get_backend() -> Backend:
    """The backend for the current settings (cached per settings)."""
    return _cached_backend(get_settings())


def clear_backend_cache() -> None:
    _cached_backend.cache_clear()
