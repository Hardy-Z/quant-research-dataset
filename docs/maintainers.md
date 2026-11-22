# Maintainer guide

## 1. Build the prepared dataset

Raw vendor files stay where they are; the build only reads them.

```bash
qrd -v build --source "<raw data root>" --out prepared --version 2025.12
qrd verify --data-dir prepared
```

The CSI 300 datasets come from a public release instead of the raw folder.
Fetch them into a separate source folder and build them from there:

```bash
python scripts/fetch_csi300.py --out source_data_extra
qrd -v build --source source_data_extra --out prepared --version 2025.12 \
    --dataset cn_hk/equity/csi300_stock_daily --dataset cn_hk/equity/csi300_stocks
```

`prepared/` is git-ignored. It contains one folder per dataset and
`manifest.json` (rows, bytes, SHA-256 and date range of every file). Rebuild a
single dataset with `--dataset <id>`; the manifest is refreshed for everything
present.

## 2. Regenerate the docs

```bash
qrd docs --data-dir prepared --out docs --card hf/README.md --repo-id <owner>/quant-research-dataset
```

This writes the data dictionary (`docs/datasets.md`) and the Hugging Face
dataset card (`hf/README.md`) from the registry.

## 3. Publish to Hugging Face

```bash
hf auth login                    # a token with write access
qrd publish --data-dir prepared --repo-id <owner>/quant-research-dataset            # dry run
qrd publish --data-dir prepared --repo-id <owner>/quant-research-dataset --tag v2025.12 --yes
```

* Only datasets with `publish: true` are uploaded, unless you pass `--dataset`.
* The repo is created **private**. Test it with `QRD_REPO_ID=<owner>/quant-research-dataset`.
* To open it to approved users, switch it to public and turn on
  **gated access with manual approval** in the repo settings. The access form
  fields come from the dataset card (`extra_gated_fields`).
* Clients can pin a release with `qrd.configure(revision="v2025.12")`.

## 4. Release the package

Releases use PyPI trusted publishing from GitHub Actions (`.github/workflows/release.yml`),
so no API token is stored anywhere.

One-time setup, on both https://test.pypi.org and https://pypi.org: add a *pending
publisher* with owner `Hardy-Z`, repository `quant-research-dataset`, workflow
`release.yml`, and environment `testpypi` (TestPyPI) or `pypi` (PyPI).

```bash
# bump src/quant_research_dataset/_version.py and CHANGELOG.md, commit, then:
gh workflow run release.yml -f target=testpypi     # test release
git tag v0.1.0 && git push origin v0.1.0           # real release (tag must match the version)
```
