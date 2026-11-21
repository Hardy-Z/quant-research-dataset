"""Command-line interface: ``qrd <command>``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from . import __version__
from .errors import QRDError


def _cmd_list(args: argparse.Namespace) -> int:
    from .query import list_datasets

    df = list_datasets(args.market, args.asset)
    with pd.option_context("display.max_colwidth", 60, "display.width", 200):
        print(df[["id", "title", "frequency"]].to_string(index=False))
    return 0


def _cmd_describe(args: argparse.Namespace) -> int:
    from .query import describe

    info = describe(args.dataset, coverage=not args.offline)
    cols = info.pop("columns")
    for k, v in info.items():
        if v not in (None, [], {}, ""):
            print(f"{k:>14}: {v}")
    print()
    with pd.option_context("display.max_colwidth", 80, "display.width", 200):
        print(cols.to_string(index=False))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from .build import build_all

    manifest = build_all(args.source, args.out, args.dataset or None, version=args.version)
    for ds_id, e in manifest.datasets.items():
        print(f"{ds_id:40s} {e.rows:>12,} rows {e.bytes / 1e6:>9.1f} MB  {e.start} .. {e.end}")
    return 0


def _cmd_docs(args: argparse.Namespace) -> int:
    from .catalog import render_data_dictionary
    from .manifest import Manifest
    from .publish import plan_release
    from .registry import default_registry

    manifest = Manifest.load(args.data_dir) if args.data_dir else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "datasets.md").write_text(
        render_data_dictionary(default_registry(), manifest), encoding="utf-8"
    )
    print(f"wrote {out / 'datasets.md'}")
    if args.data_dir and args.card:
        plan = plan_release(args.data_dir, args.repo_id)
        Path(args.card).parent.mkdir(parents=True, exist_ok=True)
        Path(args.card).write_text(plan.card, encoding="utf-8")
        print(f"wrote {args.card}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from .publish import verify

    problems = verify(args.data_dir)
    for p in problems:
        print(p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def _cmd_publish(args: argparse.Namespace) -> int:
    from .publish import plan_release, publish

    plan = plan_release(args.data_dir, args.repo_id, args.dataset or None)
    print(plan.summary())
    if not args.yes:
        print("\nDry run. Add --yes to upload.")
        return 0
    url = publish(args.data_dir, plan, private=not args.public, tag=args.tag)
    print(f"Uploaded: {url}")
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from .query import download

    paths = download(args.dataset, args.start, args.end)
    print(f"{len(paths)} file(s) cached")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qrd", description="Quant research dataset tools")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list", help="list datasets")
    s.add_argument("--market")
    s.add_argument("--asset")
    s.set_defaults(func=_cmd_list)

    s = sub.add_parser("describe", help="show a dataset's metadata and columns")
    s.add_argument("dataset")
    s.add_argument("--offline", action="store_true", help="skip coverage (no manifest lookup)")
    s.set_defaults(func=_cmd_describe)

    s = sub.add_parser("download", help="pre-fetch partitions into the cache")
    s.add_argument("dataset")
    s.add_argument("--start")
    s.add_argument("--end")
    s.set_defaults(func=_cmd_download)

    s = sub.add_parser("build", help="[maintainers] build prepared partitions from raw files")
    s.add_argument("--source", required=True, help="root folder of the raw files")
    s.add_argument("--out", required=True, help="output folder for prepared data")
    s.add_argument("--dataset", action="append", help="build only this dataset (repeatable)")
    s.add_argument("--version", default="dev", help="data version label, e.g. 2025.12")
    s.set_defaults(func=_cmd_build)

    s = sub.add_parser("docs", help="[maintainers] regenerate the data dictionary and dataset card")
    s.add_argument("--data-dir", help="prepared data folder (adds coverage)")
    s.add_argument("--out", default="docs", help="folder for datasets.md")
    s.add_argument("--card", help="also write the Hugging Face dataset card here")
    s.add_argument("--repo-id", default="Hardy-Z/quant-research-dataset")
    s.set_defaults(func=_cmd_docs)

    s = sub.add_parser("verify", help="[maintainers] check prepared files against the manifest")
    s.add_argument("--data-dir", required=True)
    s.set_defaults(func=_cmd_verify)

    s = sub.add_parser(
        "publish", help="[maintainers] upload to Hugging Face (dry run unless --yes)"
    )
    s.add_argument("--data-dir", required=True)
    s.add_argument("--repo-id", required=True)
    s.add_argument("--dataset", action="append", help="publish only this dataset (repeatable)")
    s.add_argument(
        "--public", action="store_true", help="create the repo public (default: private)"
    )
    s.add_argument("--tag", help="tag the upload, e.g. v2025.12")
    s.add_argument("--yes", action="store_true", help="actually upload")
    s.set_defaults(func=_cmd_publish)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s"
    )
    try:
        return int(args.func(args))
    except QRDError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
