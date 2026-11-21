# Maintainer guide

## 1. Build the prepared dataset

Raw vendor files stay where they are; the build only reads them.

```bash
qrd -v build --source "<raw data root>" --out prepared --version 2025.12
qrd verify --data-dir prepared
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
huggingface-cli login                    # a token with write access
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

```bash
# bump src/quant_research_dataset/_version.py and CHANGELOG.md
python -m build
twine upload dist/*
```
