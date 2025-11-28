# Merge Checklist: feat/2.5newValidationRunner → main

## Pre-Merge Verification

### Code Quality
- [ ] Run `make lint` - all checks pass
- [ ] Run `make test` - all existing tests pass
- [ ] Run `make e2e.test` - E2E tests pass
- [ ] Run `make test.schemas` - schema tests pass

### Compatibility
- [ ] No breaking changes to existing APIs
- [ ] All imports resolve correctly
- [ ] Environment variables properly configured
- [ ] CI workflow runs successfully

### File Structure
- [ ] New files follow existing patterns
- [ ] Path handling uses environment variables
- [ ] No hardcoded absolute paths
- [ ] All required dependencies in pyproject.toml

### Documentation
- [ ] README.md updated with E2E info
- [ ] VALIDATION_RUNNER.md created
- [ ] Code comments and docstrings complete
- [ ] Configuration examples provided

## Branch Status Checks

### Local Machine
\`\`\`bash
# Checkout feature branch
git checkout feat/2.5newValidationRunner

# Run all tests
make lint
make test
make e2e.test
make test.schemas

# Verify environment
export ULOG_SCHEMAS_DIR=./schemas
export ULOG_RULES_PATH=./rules/rules.json
export ULOG_VOCAB_PATH=./vocab/controlled_vocabulary.json
python -m src.ulog --domain all --samples 20
\`\`\`

### GitHub Actions
- [ ] All workflow jobs pass
- [ ] E2E validation tests pass
- [ ] No new warnings introduced
- [ ] Artifact upload successful

## Merge Steps

1. **Create Pull Request**
   \`\`\`bash
   git push origin feat/2.5newValidationRunner
   \`\`\`
   - Title: "Feat: Add E2E Validation Runner (Ticket 2.5)"
   - Description: Reference ticket #2.5

2. **Wait for CI**
   - GitHub Actions runs all checks
   - Review workflow results
   - Address any failures

3. **Code Review**
   - Ensure code follows project standards
   - Verify compatibility with main branch
   - Check performance impact

4. **Merge**
   \`\`\`bash
   # Option A: Squash merge (recommended for feature branches)
   git checkout main
   git pull origin main
   git merge --squash feat/2.5newValidationRunner
   git commit -m "Feat: Add E2E Validation Runner (Ticket 2.5)"
   git push origin main
   
   # Option B: Regular merge
   git checkout main
   git pull origin main
   git merge --no-ff feat/2.5newValidationRunner
   git push origin main
   \`\`\`

5. **Post-Merge Verification**
   \`\`\`bash
   git checkout main
   git pull origin main
   
   # Verify everything still works
   make lint
   make test
   make e2e.test
   
   # Check branch can be deleted safely
   git branch -d feat/2.5newValidationRunner
   \`\`\`

## Known Issues & Resolutions

### Issue: FileNotFoundError for schemas

**Solution:** Ensure `ULOG_SCHEMAS_DIR` is set:
\`\`\`bash
export ULOG_SCHEMAS_DIR=./schemas
\`\`\`

### Issue: ImportError in tests

**Solution:** Run from repo root and ensure path is set:
\`\`\`bash
cd /path/to/myulog
export PYTHONPATH=./src:./tests
\`\`\`

### Issue: CI workflow fails

**Solution:** Check GitHub Actions logs and verify:
- Python 3.12 is installed
- Dependencies installed via poetry
- Environment variables configured in workflow

## Ticket 2.5 Acceptance

✓ E2E validation runner executes parse → validate → classify → annotate pipeline
✓ Tests cover all 4 domains (Core/API, LLM, Agentic, CV)
✓ Outputs per-domain metrics (parse rate, schema valid rate, classification rate)
✓ Produces JUnit/JSON artifacts in tests/reports/
✓ CI job executes on PR and main branch
✓ Documentation complete and clear
✓ No breaking changes to existing codebase
✓ All environment variables properly handled
✓ Ready for production merge
