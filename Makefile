# Use bash for nicer behavior
SHELL := /bin/bash

.PHONY: help setup lint test test.schemas test.schemas.json test.all \
        demo.generate demo.run \
        lint-vocab format-vocab \
        rules.validate rules.test rules.check \
        generate normalize classify down \
        http.up http.down http.logs http.test http.smoke \
        coverage test.determinism \
        build build.verify package clean \
		parity.check

help: ## Show available commands
	@echo "Common commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make lint                      - run ruff lint locally (poetry run)"
	@echo "  make test                      - run pytest locally (poetry run)"
	@echo "  make coverage                  - run tests with coverage and write docs/coverage.svg"
	@echo "  make test.schemas              - run JSON Schema test harness (writes JUnit XML)"
	@echo "  make test.schemas.json         - run JSON Schema test harness (writes JSON)"
	@echo "  make test.determinism          - run determinism tests for data generators"
	@echo "  make test.roundtrip            - run roundtrip test for data generators"
	@echo "  make test.all                  - run all checks: lint + unit tests + schema harness (CI parity)"
	@echo ""
	@echo "Rules:"
	@echo "  make rules.validate            - validate rules.json against rules.schema.json"
	@echo "  make rules.test                - run unit tests for rules examples"
	@echo "  make rules.check               - validate rules and run tests"
	@echo ""
	@echo "Demo:"
	@echo "  make demo.generate             - generate tiny demo schema/examples/raw inputs"
	@echo "  make demo.run                  - generate demo and run the harness against it"
	@echo ""
	@echo "Pipeline:"
	@echo "  make generate         		    - create a sample log in local_pipeline/in"
	@echo "  make normalize        		    - normalize/parse logs from local_pipeline/in to local_pipeline/out"
	@echo "  make classify         		    - run docker-compose pipeline (in -> out)"
	@echo "  make down             		    - stop/cleanup docker-compose services"
	@echo ""
	@echo "HTTP Service:"
	@echo "  make http.up                   - start HTTP classifier service"
	@echo "  make http.down                 - stop HTTP classifier service"
	@echo "  make http.logs                 - view HTTP service logs"
	@echo "  make http.test                 - run smoke tests against HTTP service"
	@echo "  make http.smoke                - start service and run smoke tests"
	@echo "Build & Packaging:"
	@echo "  make build                     - build all distribution artifacts (wheel, CLI, Lambda ZIP)"
	@echo "  make build.verify              - verify build reproducibility (builds twice, compares checksums)"
	@echo "  make package                   - alias for 'make build' (produces dist/* + SHA256SUMS)"
	@echo "  make clean                     - remove ./dist (no Docker pruning)"
	@echo ""
	@echo "Vocabulary:"
	@echo "  make lint-vocab                - lint the controlled vocabulary"
	@echo "  make format-vocab              - auto-format the vocabulary JSON"
	@echo "Synthetic Data:"
	@echo "  make data.generate             - Generate normalized synthetic JSONL (per domain)"
	@echo "  make data.generate.raw         - Generate raw-line mirrors for round-trip tests (per domain)"
	@echo "  make data.generate.baseline    - Generate paired raw+parsed JSONL and labels (200 total; 50/domain)"
	@echo "  make data.validate.baseline    - Validate baseline: round-trip counts, label alignment, minima"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - install local dev tools (ruff, pytest) (optional)"

setup: ## Install local tools (optional; CI installs its own)
	@python3 -m pip install --upgrade pip || true
	@pip3 install ruff pytest || true

yamllint: ## Lint YAML with 4-space indentation
	@pipx install yamllint >/dev/null 2>&1 || true
	@yamllint .

lint: ## Lint with ruff
	@poetry run ruff check .

test: ## Run tests
	@poetry run pytest -q

test.unit: ## Run unit tests for rules and provenance
	@mkdir -p tests/reports
	@poetry run pytest tests/unit/ -v --tb=short \
	--junit-xml=tests/reports/rules_unit_results.xml \
	--json-report \
	--json-report-file=tests/reports/rules_unit_results.json \
	--json-report-indent=2
	@echo "Unit test results: tests/reports/rules_unit_results.xml and tests/reports/rules_unit_results.json"

test.schemas: ## Run JSON Schema test harness with two-phase flow (writes JUnit XML to tests/reports/)
	@poetry run python tests/harness/run_harness.py --format junit --output tests/reports/schema_results.xml

test.schemas.json: ## Run JSON Schema test harness with two-phase flow (writes JSON to tests/reports/)
	@poetry run python tests/harness/run_harness.py --format json --output tests/reports/schema_results.json

test.determinism: ## Run determinism tests for data generators
	@poetry run pytest -q data/generator/test_determinism.py

test.determinism.golden: ## Run golden set determinism tests
	@echo "Running golden set determinism tests..."
	@poetry run pytest tests/determinism/test_golden_determinism.py -v


test.all: ## Run all checks: lint, unit tests, and schema harness (CI parity)
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) test.unit
	@$(MAKE) test.schemas
	@$(MAKE) test.schemas.json
	@$(MAKE) test.determinism
	@$(MAKE) test.determinism.golden

coverage: ## Run tests with coverage and generate docs/coverage.svg
	@mkdir -p docs
	@poetry run pytest --cov=src --cov-report=term-missing --cov-report=xml
	@poetry run python -m pip install --disable-pip-version-check -q coverage-badge
	@poetry run python -m coverage_badge -o docs/coverage.svg -f
	@echo "Coverage report: coverage.xml, badge: docs/coverage.svg"

demo.generate: ## Create tiny demo schema, examples and raw inputs for the harness
	@poetry run python tests/harness/generate_demo.py

demo.run: ## Generate demo and run the harness against it (writes JUnit XML)
	@$(MAKE) demo.generate
	@poetry run python tests/harness/run_harness.py --format junit --output tests/reports/demo_schema_results.xml

generate: ## Create a sample input file
	@mkdir -p local_pipeline/in local_pipeline/out
	@date > local_pipeline/in/example.log
	@echo "hello, ulog" >> local_pipeline/in/example.log
	@echo "Wrote local_pipeline/in/example.log"

normalize: ## Normalize/parse logs from local_pipeline/in to local_pipeline/out
	@mkdir -p local_pipeline/in local_pipeline/out
	@for file in local_pipeline/in/*.jsonl; do \
		if [ -f "$$file" ]; then \
			basename=$$(basename "$$file"); \
			echo "Normalizing $$basename..."; \
			cat "$$file" | poetry run ulog parse > "local_pipeline/out/$${basename%.jsonl}.normalized.jsonl"; \
			echo "  → local_pipeline/out/$${basename%.jsonl}.normalized.jsonl"; \
		fi \
	done
	@echo "Normalization complete."

classify: ## Run local pipeline (docker compose)
	@cd local_pipeline && docker compose up --build --abort-on-container-exit

down: ## Stop services and remove containers
	@cd local_pipeline && docker compose down --remove-orphans

# --- HTTP Service ---
http.up: ## Start HTTP classifier service
	@cd local_pipeline && docker compose up -d classifier-http
	@echo "HTTP service starting at http://localhost:$${PORT:-8080}"
	@echo "Health: curl http://localhost:$${PORT:-8080}/health"

http.down: ## Stop HTTP classifier service
	@cd local_pipeline && (docker compose stop classifier-http || true)
	@cd local_pipeline && (docker compose rm -f classifier-http || true)

http.logs: ## View HTTP service logs
	@cd local_pipeline && docker compose logs -f classifier-http

http.test: ## Run smoke tests against HTTP service
	@./scripts/smoke_http.sh "http://localhost:$${PORT:-8080}"

http.smoke: ## Start service and run smoke tests
	@$(MAKE) http.up
	@echo "Waiting for service..."
	@bash -c 'for i in $$(seq 1 30); do curl -fsS http://localhost:$${PORT:-8080}/health >/dev/null && exit 0; sleep 1; done; exit 1'
	@$(MAKE) http.test

http.screens: ## Capture fresh screenshots into docs/screenshots/
	@./scripts/capture_screenshots.sh
	
# --- Build & Packaging ---
build: ## Build all distribution artifacts (wheel, CLI, Lambda ZIP)
	@./scripts/build.sh

build.verify: ## Verify build reproducibility (two clean builds → identical checksums)
	@./scripts/verify_reproducible_build.sh

package: build ## Alias for build (produces dist/* + SHA256SUMS)

clean: ## Remove local build artifacts
	@rm -rf dist/

# --- Vocabulary helpers ---
lint-vocab:
	@poetry run python tests/vocab/lint_vocab.py

format-vocab:
	@poetry run python tests/vocab/format_vocab.py

# --- Rules validation and testing ---
rules.validate: ## Validate rules.json against rules.schema.json
	@poetry run pytest -q tests/rules/test_rules_doc.py::test_rules_schema_validates tests/rules/test_rules_doc.py::test_rule_ids_unique

rules.test: ## Run unit tests for rules examples
	@echo "Testing rules against examples..."
	# Legacy location (may be empty)
	@poetry run pytest -q tests/rules/test_rules_examples.py
	# New acceptance tests for Ticket 2.1 (structure + rules/examples)
	@poetry run pytest -q tests/rules/test_rules.py

rules.check: ## Run both rules validation and tests
	@$(MAKE) rules.validate
	@$(MAKE) rules.test
	@echo "✓ All rules checks passed"


# --- Synthetic Data Generators ---
.PHONY: data.generate data.generate.raw test.roundtrip data.generate.baseline data.validate.baseline

data.generate: ## Generate synthetic JSONL (per domain)
	@poetry run python data/generator/main.py -d agentic -n log_agentic
	@poetry run python data/generator/main.py -d cv -n log_cv
	@poetry run python data/generator/main.py -d api -n log_api
	@poetry run python data/generator/main.py -d llm -n log_llm

# @poetry run python data/generator/main.py -d $(Domain) -o $(Output_dir) -c $(Count) -s $(Seed) -n $(name) -args $(Arguments)

data.generate.raw: ## Generate raw-line mirrors for round-trip tests
	@poetry run python data/generator/main.py -d agentic -n agentic --raw-mirror
	@poetry run python data/generator/main.py -d cv -n cv --raw-mirror
	@poetry run python data/generator/main.py -d api -n api --raw-mirror
	@poetry run python data/generator/main.py -d llm -n llm --raw-mirror

# --- Round-trip test ---
test.roundtrip:
	@poetry run pytest -q data/generator/test_roundtrip.py


# --- Baseline dataset (Ticket 2.3) ---

data.generate.baseline: ## Generate paired raw+parsed JSONL and labels (200 total; 50/domain)
	@poetry run python data/generator/generate_baseline.py --seed 42 --count-per-domain 50

data.validate.baseline: ## Validate baseline integrity and alignment
	@poetry run python data/generator/validate_baseline.py
# --- Parity check: CLI vs local pipeline app ---
parity.check: ## Compare CLI vs pipeline outputs for all files in local_pipeline/in/*.jsonl
	@bash scripts/parity_check.sh
