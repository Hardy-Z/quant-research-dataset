"""Upload prepared data to a Hugging Face dataset repository (maintainers only).

Only datasets whose registry entry has ``publish: true`` are uploaded, and the
uploaded ``manifest.json`` lists only those, so the client never points at
files that are not there.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .catalog import render_dataset_card
from .errors import QRDError
from .manifest import MANIFEST_NAME, Manifest, sha256_file
from .registry import DatasetSpec, Registry, default_registry


@dataclass(frozen=True)
class ReleasePlan:
    repo_id: str
    datasets: tuple[str, ...]
    files: int
    bytes: int
    manifest: Manifest
    card: str

    def summary(self) -> str:
        lines = [
            f"Upload to {self.repo_id}: {len(self.datasets)} datasets, {self.files} files, {self.bytes / 1e9:.2f} GB"
        ]
        lines += [f"  - {d}" for d in self.datasets]
        return "\n".join(lines)


def verify(data_dir: str | Path, datasets: Iterable[str] | None = None) -> list[str]:
    """Check every file against the manifest. Returns a list of problems (empty = OK)."""
    root = Path(data_dir)
    manifest = Manifest.load(root)
    problems = []
    for ds_id, entry in manifest.datasets.items():
        if datasets is not None and ds_id not in set(datasets):
            continue
        for f in entry.files:
            p = root / f.path
            if not p.exists():
                problems.append(f"missing: {f.path}")
            elif p.stat().st_size != f.bytes or sha256_file(p) != f.sha256:
                problems.append(f"checksum mismatch: {f.path}")
    return problems


def plan_release(
    data_dir: str | Path,
    repo_id: str,
    datasets: Iterable[str] | None = None,
    registry: Registry | None = None,
) -> ReleasePlan:
    """Work out what would be uploaded, without touching the network."""
    registry = registry or default_registry()
    full = Manifest.load(Path(data_dir))
    if datasets:
        specs: list[DatasetSpec] = [registry.get(d) for d in datasets]
    else:
        specs = [s for s in registry if s.publish]
    missing = [s.id for s in specs if s.id not in full.datasets]
    if missing:
        raise QRDError(f"not built yet: {missing}; run `qrd build` first")
    manifest = Manifest(
        datasets={s.id: full.datasets[s.id] for s in specs},
        version=full.version,
        created_at=full.created_at,
    )
    card = render_dataset_card(registry, manifest, repo_id, specs)
    return ReleasePlan(
        repo_id=repo_id,
        datasets=tuple(s.id for s in specs),
        files=sum(len(manifest.datasets[s.id].files) for s in specs),
        bytes=sum(manifest.datasets[s.id].bytes for s in specs),
        manifest=manifest,
        card=card,
    )


def publish(
    data_dir: str | Path,
    plan: ReleasePlan,
    *,
    private: bool = True,
    tag: str | None = None,
    token: str | None = None,
) -> str:
    """Create the repo if needed (private by default), upload, and optionally tag.

    Returns the URL of the dataset repo.
    """
    from huggingface_hub import HfApi

    problems = verify(data_dir, plan.datasets)
    if problems:
        raise QRDError(
            "refusing to upload, local files do not match the manifest:\n"
            + "\n".join(problems[:10])
        )
    api = HfApi(token=token)
    api.create_repo(plan.repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        folder_path=str(data_dir),
        repo_id=plan.repo_id,
        repo_type="dataset",
        allow_patterns=[f"{d}/**/*.parquet" for d in plan.datasets],
        commit_message=f"Data files for version {plan.manifest.version}",
    )
    manifest_bytes = (
        json.dumps(plan.manifest.to_dict(), indent=1, ensure_ascii=False) + "\n"
    ).encode()
    api.upload_file(
        path_or_fileobj=manifest_bytes,
        path_in_repo=MANIFEST_NAME,
        repo_id=plan.repo_id,
        repo_type="dataset",
        commit_message=f"Manifest for version {plan.manifest.version}",
    )
    api.upload_file(
        path_or_fileobj=plan.card.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=plan.repo_id,
        repo_type="dataset",
        commit_message="Dataset card",
    )
    if tag:
        api.create_tag(plan.repo_id, tag=tag, repo_type="dataset", exist_ok=True)
    return f"https://huggingface.co/datasets/{plan.repo_id}"
