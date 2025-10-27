# Use bash for nicer behavior
SHELL := /bin/bash

.PHONY: help setup lint test test.schemas test.schemas.json test.all \
        demo.generate demo.run \
        lint-vocab format-vocab \
        rules.validate rules.test rules.check \
        generate classify down \
        coverage test.determinism \
        build build.verify package clean

help: ## Show available commands
	@echo "Common commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make lint        - run ruff lint locally (poetry run)"
	@echo "  make test        - run pytest locally (poetry run)"
	@echo "  make coverage    - run tests with coverage and write docs/coverage.svg"
	@echo "  make test.schemas - run JSON Schema test harness (writes JUnit XML)"
	@echo "  make test.schemas.json - run JSON Schema test harness (writes JSON)"
	@echo "  make test.determinism - run determinism tests for data generators"
	@echo "  make test.all    - run all checks: lint + unit tests + schema harness (CI parity)"
	@echo ""
	@echo "Rules:"
	@echo "  make rules.validate     - validate rules.json against rules.schema.json"
	@echo "  make rules.test         - run unit tests for rules examples"
	@echo "  make rules.check        - validate rules and run tests"
	@echo ""
	@echo "Demo:"
	@echo "  make demo.generate      - generate tiny demo schema/examples/raw inputs"
	@echo "  make demo.run           - generate demo and run the harness against it"
	@echo ""
	@echo "Pipeline:"
	@echo "  make generate           - create a sample log in local_pipeline/in"
	@echo "  make classify           - run docker-compose pipeline (in -> out)"
	@echo "  make down               - stop/cleanup docker-compose services"
	@echo ""
	@echo "Build & Packaging:"
	@echo "  make build              - build all distribution artifacts (wheel, CLI, Lambda ZIP)"
	@echo "  make build.verify       - verify build reproducibility (builds twice, compares checksums)"
	@echo "  make package            - alias for 'make build' (produces dist/* + SHA256SUMS)"
	@echo "  make clean              - remove ./dist (no Docker pruning)"
	@echo ""
	@echo "Vocabulary:"
	@echo "  make lint-vocab         - lint the controlled vocabulary"
	@echo "  make format-vocab       - auto-format the vocabulary JSON"
	@echo "Synthetic Data:"
	@echo "  make data.generate - Generate normalized synthetic JSONL (per domain)"
	@echo "  make data.generate.raw - Generate raw-line mirrors for round-trip tests (per domain)"
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

test.schemas: ## Run JSON Schema test harness with two-phase flow (writes JUnit XML to tests/reports/)
	@poetry run python tests/harness/run_harness.py --format junit --output tests/reports/schema_results.xml

test.schemas.json: ## Run JSON Schema test harness with two-phase flow (writes JSON to tests/reports/)
	@poetry run python tests/harness/run_harness.py --format json --output tests/reports/schema_results.json

test.determinism: ## Run determinism tests for data generators
	@poetry run pytest -q data/generator/test_determinism.py


test.all: ## Run all checks: lint, unit tests, and schema harness (CI parity)
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) test.schemas
	@$(MAKE) test.schemas.json
	@$(MAKE) test.determinism

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

classify: ## Run local pipeline (docker compose)
	@cd local_pipeline && docker compose up --build --abort-on-container-exit

down: ## Stop services and remove containers
	@cd local_pipeline && docker compose down --remove-orphans

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
.PHONY: data.generate data.generate.raw test.roundtrip

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
