# Build and Packaging

ULog produces three distribution artifacts plus checksums. All builds are **reproducible** - identical source produces identical checksums.

## Quick Start

```bash
# Build all artifacts
make build    # or ./scripts/build.sh

# Alias for 'make build' (produces dist/* + SHA256SUMS)
make package  # alias to 'make build'

# Verify reproducibility (two clean builds → identical checksums)
make build.verify

# Clean local artifacts
make clean
```

**Output:** `dist/ulog-0.1.0-py3-none-any.whl`, `dist/ulog-cli-0.1.0.tar.gz`, `dist/classifier_lambda.zip`, `dist/SHA256SUMS`

**Note:** `make build` (and its alias `make package`) automatically generates checksums as the final step.

**Verify checksums:**
```bash
./scripts/verify_checksums.sh
# or manually: cd dist/ && shasum -a 256 -c SHA256SUMS
```

---

## Artifacts

### 1. Python Wheel (`ulog-<version>-py3-none-any.whl`) - ~39KB

Standard Python package for pip installation.

**Install:**
```bash
pip install dist/ulog-0.1.0-py3-none-any.whl
ulog --help
```

**Use cases:** Virtual environments, PyPI distribution, Python projects

---

### 2. CLI Bundle (`ulog-cli-<version>.tar.gz`) - ~1.3MB

Standalone portable distribution with all dependencies. Requires Python 3.12 on target system.

**Structure:**
```
ulog-cli-0.1.0/
├── bin/ulog          # Wrapper script
└── lib/python/       # All dependencies bundled
```

**Install:**
```bash
tar -xzf dist/ulog-cli-0.1.0.tar.gz
./ulog-cli-0.1.0/bin/ulog --help

# Optional: add to PATH or move to /opt
export PATH="$PWD/ulog-cli-0.1.0/bin:$PATH"
```

**Use cases:** Server deployments, portable installations, no pip/venv required

---

### 3. Lambda ZIP (`classifier_lambda.zip`) - ~1.5MB

AWS Lambda deployment package (direct function, not layer) with Python 3.12 runtime.

**Structure:** All dependencies at root level (not in `python/` subdirectory)
```
classifier_lambda.zip
├── handler.py               # Lambda handler at root (temporary)
├── ulog/                    # Main package
├── jsonschema/              # Dependencies at root
├── click/
├── schemas/                 # Runtime data
├── vocab/
└── rules/
```

**Handler:** `handler.handler`

> **Note:** Ticket 2.2 will replace the temporary `handler.py` with `lambda_adapter/` module containing the full classifier implementation.

**Event format:**
```json
{
  "logs": [
    {"@timestamp": "2024-01-01T00:00:00Z", "@message": "log line"}
  ],
  "domain": "core_api"
}
```

**Deploy:**
```bash
# AWS CLI
aws lambda create-function \
  --function-name ulog-classifier \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler handler.handler \
  --zip-file fileb://dist/classifier_lambda.zip

# Update existing function
aws lambda update-function-code \
  --function-name ulog-classifier \
  --zip-file fileb://dist/classifier_lambda.zip

# Note: Update --handler to lambda_adapter.handler when ticket 2.2 lands
```

**Use cases:** Serverless log processing, event-driven architectures, scalable deployments

---

## Reproducible Builds

Builds use deterministic timestamps (`SOURCE_DATE_EPOCH` from git), pinned dependencies, and sorted file operations.

**Verify locally:**
```bash
make build.verify
```

This builds twice from scratch and compares checksums. Expected output:
```
✓ SUCCESS: Builds are reproducible!
  Both builds produced identical checksums.
```

**CI verification:** Every PR and push to `main` runs two jobs:
1. **Build and Upload Artifacts** - Builds once, uploads to GitHub
2. **Verify Build Reproducibility** - Builds twice, compares checksums

Check both jobs pass in the Actions tab.

---

## Download from CI

1. Go to **Actions** → **Build and Package Artifacts**
2. Click successful workflow run
3. Download `ulog-artifacts-<commit-sha>.zip` from Artifacts section
4. Extract and verify: `shasum -a 256 -c SHA256SUMS`

**Retention:** 90 days

---

## Common Tasks

### Development Install
```bash
python -m venv venv
source venv/bin/activate
pip install dist/ulog-0.1.0-py3-none-any.whl
```

### Production Server Deployment
```bash
# Copy and verify
scp dist/ulog-cli-0.1.0.tar.gz dist/SHA256SUMS server:/tmp/
ssh server "cd /tmp && shasum -a 256 -c SHA256SUMS"

# Install
ssh server "cd /tmp && tar -xzf ulog-cli-0.1.0.tar.gz && sudo mv ulog-cli-0.1.0 /opt/ulog"
```

### Test CLI Without Installing
```bash
tar -xzf dist/ulog-cli-0.1.0.tar.gz
echo '{"@timestamp":"2024-01-01T00:00:00Z","@message":"test"}' | ./ulog-cli-0.1.0/bin/ulog parse
```

---

## Troubleshooting

**Checksums don't match after download**
- Re-download (file corrupted)
- Verify commit SHA matches
- Extract from clean download

**CLI bundle: "python3: command not found"**
- Install Python 3.12: `brew install python@3.12` (macOS) or `apt install python3.12` (Ubuntu)

**Docker build slow**
- First build: 2-5 min (downloads base images)
- Cached builds: 30-60 sec

---

## Reference

### File Sizes
| Artifact | Size |
|----------|------|
| Python Wheel | ~39KB |
| CLI Bundle | ~1.3MB (gzipped) |
| Lambda ZIP | ~1.5MB |
| SHA256SUMS | ~240B |

### Scripts
| Script | Command |
|--------|---------|
| Build all | `./scripts/build.sh` or `make build` |
| Build wheel only | `./scripts/build_wheel.sh` |
| Build CLI bundle | `./scripts/build_cli_bundle.sh` |
| Build Lambda ZIP | `./scripts/build_lambda.sh` |
| Generate checksums | `./scripts/generate_checksums.sh` |
| Verify checksums | `./scripts/verify_checksums.sh` |
| Verify reproducibility | `./scripts/verify_reproducible_build.sh` or `make build.verify` |

All scripts are in `scripts/`, executable, use Docker for reproducibility, and support macOS/Linux.

### Make Targets
- `make build` - Build all distribution artifacts (wheel, CLI, Lambda ZIP, checksums)
- `make build.verify` - Verify build reproducibility
- `make package` - Alias for 'make build' (produces dist/* + SHA256SUMS)
- `make clean` - Remove `./dist` (no Docker pruning)
- `make help` - Show all available targets

### Requirements
- **Docker** - For reproducible builds
- **Python 3.12** - Runtime requirement (>= 3.12, < 3.13)
- **Git** - For deterministic timestamps

---

## See Also
- [Main README](../../README.md)
- [Dockerfile.build](../../Dockerfile.build)
- [Build Artifacts Workflow](./build_artifacts.yml)
- [Contributing Guide](../../docs/CONTRIBUTING.md)
