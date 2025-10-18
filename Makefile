# Use bash for nicer behavior
SHELL := /bin/bash

.PHONY: help setup lint test test.schemas test.schemas.json test.all \
        demo.generate demo.run \
        lint-vocab format-vocab \
        rules.validate rules.test rules.check \
        generate classify down

help: ## Show available commands
	@echo "Common commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make lint               - run ruff lint locally (poetry run)"
	@echo "  make test               - run pytest locally (poetry run)"
	@echo "  make test.schemas       - run JSON Schema test harness (writes JUnit XML)"
	@echo "  make test.schemas.json  - run JSON Schema test harness (writes JSON)"
	@echo "  make test.all           - run all checks: lint + unit tests + schema harness (CI parity)"
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
	@echo "Vocabulary:"
	@echo "  make lint-vocab         - lint the controlled vocabulary"
	@echo "  make format-vocab       - auto-format the vocabulary JSON"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - install local dev tools (ruff, pytest) (optional)"

setup: ## Install local tools (optional; CI installs its own)
	@python3 -m pip install --upgrade pip || true
	@pip3 install ruff pytest || true

lint: ## Lint with ruff
	@poetry run ruff check .

test: ## Run tests
	@poetry run pytest -q

test.schemas: ## Run JSON Schema test harness with two-phase flow (writes JUnit XML to tests/reports/)
	@poetry run python3 tests/harness/run_harness.py --format junit --output tests/reports/schema_results.xml

test.schemas.json: ## Run JSON Schema test harness with two-phase flow (writes JSON to tests/reports/)
	@poetry run python3 tests/harness/run_harness.py --format json --output tests/reports/schema_results.json

test.all: ## Run all checks: lint, unit tests, and schema harness (CI parity)
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) test.schemas

demo.generate: ## Create tiny demo schema, examples and raw inputs for the harness
	@poetry run python3 tests/harness/generate_demo.py

demo.run: ## Generate demo and run the harness against it (writes JUnit XML)
	@$(MAKE) demo.generate
	@poetry run python3 tests/harness/run_harness.py --format junit --output tests/reports/demo_schema_results.xml

generate: ## Create a sample input file
	@mkdir -p local_pipeline/in local_pipeline/out
	@date > local_pipeline/in/example.log
	@echo "hello, ulog" >> local_pipeline/in/example.log
	@echo "Wrote local_pipeline/in/example.log"

classify: ## Run local pipeline (docker compose)
	@cd local_pipeline && docker compose up --build --abort-on-container-exit

down: ## Stop services and remove containers
	@cd local_pipeline && docker compose down --remove-orphans

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
	@poetry run pytest -q tests/rules/test_rules_examples.py

rules.check: ## Run both rules validation and tests
	@$(MAKE) rules.validate
	@$(MAKE) rules.test
	@echo "✓ All rules checks passed"
