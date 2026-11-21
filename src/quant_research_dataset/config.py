"""Where the library reads data from.

Two sources are supported:

* **Hugging Face Hub** (default): partitions are downloaded on demand from a
  dataset repository and cached locally by ``huggingface_hub``.
* **Local directory**: a folder with the same layout, for example the output of
  ``qrd build`` or a mirror on a shared drive.

Settings come from, in order of precedence: :func:`configure`, environment
variables, then the defaults below.

=====================  ===============================================
Environment variable   Meaning
=====================  ===============================================
``QRD_DATA_DIR``       Local dataset root. If set, the Hub is not used.
``QRD_REPO_ID``        Hugging Face dataset repo, ``owner/name``.
``QRD_REVISION``       Branch, tag or commit of the dataset repo.
``QRD_CACHE_DIR``      Download cache (defaults to the HF cache).
``HF_TOKEN``           Token for private or gated repos (read by
                       ``huggingface_hub``).
=====================  ===============================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

DEFAULT_REPO_ID = "Hardy-Z/quant-research-dataset"
DEFAULT_REVISION = "main"


@dataclass(frozen=True)
class Settings:
    """Resolved data-source settings."""

    data_dir: Path | None = None
    repo_id: str = DEFAULT_REPO_ID
    revision: str = DEFAULT_REVISION
    cache_dir: Path | None = None
    token: str | None = None

    @property
    def source(self) -> str:
        """``"local"`` when reading from a directory, else ``"hub"``."""
        return "local" if self.data_dir is not None else "hub"


_overrides: dict[str, object] = {}


def _from_env() -> Settings:
    data_dir = os.environ.get("QRD_DATA_DIR")
    cache_dir = os.environ.get("QRD_CACHE_DIR")
    return Settings(
        data_dir=Path(data_dir).expanduser() if data_dir else None,
        repo_id=os.environ.get("QRD_REPO_ID", DEFAULT_REPO_ID),
        revision=os.environ.get("QRD_REVISION", DEFAULT_REVISION),
        cache_dir=Path(cache_dir).expanduser() if cache_dir else None,
    )


def get_settings() -> Settings:
    """Return the settings currently in effect."""
    return replace(_from_env(), **_overrides)  # type: ignore[arg-type]


def configure(
    *,
    data_dir: str | os.PathLike[str] | None = None,
    repo_id: str | None = None,
    revision: str | None = None,
    cache_dir: str | os.PathLike[str] | None = None,
    token: str | None = None,
    reset: bool = False,
) -> Settings:
    """Set where data is read from for the rest of the session.

    Examples
    --------
    >>> import quant_research_dataset as qrd
    >>> qrd.configure(data_dir="D:/qrd")                 # doctest: +SKIP
    >>> qrd.configure(repo_id="me/my-fork", revision="v2025.12")  # doctest: +SKIP

    Pass ``reset=True`` to drop earlier overrides first. Setting ``repo_id``
    switches back to the Hub even if a local ``data_dir`` was set earlier.
    """
    from .storage import clear_backend_cache

    if reset:
        _overrides.clear()
    if data_dir is not None:
        _overrides["data_dir"] = Path(data_dir).expanduser()
    if repo_id is not None:
        _overrides["repo_id"] = repo_id
        if data_dir is None:
            _overrides["data_dir"] = None
    if revision is not None:
        _overrides["revision"] = revision
    if cache_dir is not None:
        _overrides["cache_dir"] = Path(cache_dir).expanduser()
    if token is not None:
        _overrides["token"] = token
    clear_backend_cache()
    return get_settings()
