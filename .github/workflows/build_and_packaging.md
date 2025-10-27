# Build and Packaging (Reproducible)

This repository produces **three artifacts** plus checksums:

- Wheel: `dist/ulog-<version>-py3-none-any.whl`
- CLI bundle: `dist/ulog-cli-<version>.tar.gz`
- Lambda ZIP: `dist/classifier_lambda.zip`
- Checksums: `dist/SHA256SUMS`

## Quick Start

```bash
make build        # or: ./scripts/build.sh
make build.verify # builds twice and compares SHA256SUMS
make clean
```

**Verify checksums**
```bash
./scripts/verify_checksums.sh
# or: (cd dist && shasum -a 256 -c SHA256SUMS)
```

## Artifacts

### 1) Python Wheel
Install & test:
```bash
pip install dist/ulog-*.whl
ulog --help
```

### 2) CLI Bundle
Portable tarball; requires Python 3.12 on target host.
Structure:
```
ulog-cli-<ver>/
├─ bin/ulog
└─ lib/python/...
```

Use:
```bash
tar -xzf dist/ulog-cli-*.tar.gz
./ulog-cli-*/bin/ulog --help
```

### 3) Lambda ZIP
- **Handler:** `ulog.classifier.handler.lambda_handler` (already implemented)
- Content: code + dependencies at ZIP root (not a layer)
- Deploy:
```bash
aws lambda create-function \
  --function-name ulog-classifier \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler ulog.classifier.handler.lambda_handler \
  --zip-file fileb://dist/classifier_lambda.zip
```

## Reproducible Builds

We set `SOURCE_DATE_EPOCH` from git and sort/normalize timestamps.  
Local proof:
```bash
make build.verify
```

CI runs:
1. **Build and Upload Artifacts** — outputs `/dist/*` as GitHub artifacts.
2. **Verify Build Reproducibility** — builds twice and compares checksums.

## Scripts

- `./scripts/build.sh` – orchestrates everything
- `./scripts/build_wheel.sh` – wheel via Docker
- `./scripts/build_cli_bundle.sh` – CLI tar.gz via Docker
- `./scripts/build_lambda.sh` – Lambda ZIP via Docker (uses existing handler)
- `./scripts/generate_checksums.sh` – writes `dist/SHA256SUMS`
- `./scripts/verify_checksums.sh` – verifies SHA256SUMS
- `./scripts/verify_reproducible_build.sh` – builds twice & diffs

## Requirements

- Docker (incl. Buildx)
- Git (for timestamps)
- Python 3.12 at runtime (for CLI usage)
