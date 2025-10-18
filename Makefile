.PHONY: help setup lint test generate classify down test.schemas test.schemas.json test.all demo.generate demo.run

help: ## Show available commands
	@echo "Common commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make lint        - run ruff lint locally (poetry run)"
	@echo "  make test        - run pytest locally (poetry run)"
	@echo "  make test.schemas - run JSON Schema test harness (writes JUnit XML)"
	@echo "  make test.schemas.json - run JSON Schema test harness (writes JSON)"
	@echo "  make test.determinism
	@echo "  make test.all    - run all checks: lint + unit tests + schema harness (CI parity)"
	@echo ""
	@echo "Rules:"
	@echo "  make rules.validate - validate rules.json against rules.schema.json"
	@echo "  make rules.test  - run unit tests for rules examples"
	@echo "  make rules.check - validate rules and run tests"
	@echo ""
	@echo "Demo:"
	@echo "  make demo.generate - generate tiny demo schema/examples/raw inputs"
	@echo "  make demo.run    - generate demo and run the harness against it"
	@echo ""
	@echo "Pipeline:"
	@echo "  make generate    - create a sample log in local_pipeline/in"
	@echo "  make classify    - run docker-compose pipeline (in -> out)"
	@echo "  make down        - stop/cleanup docker-compose services"
	@echo "Synthetic Data:"
	@echo "  make data.generate - Generate normalized synthetic JSONL (per domain)"
	@echo "  make data.generate.raw - Generate raw-line mirrors for round-trip tests (per domain)"
	@echo ""
	@echo "Setup:"
	@echo "  make setup       - install local dev tools (ruff, pytest) (optional)"

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

test.determinism: ## Run determinism tests for data generators
# 	@poetry run pytest -q tests/generator/test_determinism.py
	@poetry run pytest -q data/generator/test_determinism.py


test.all: ## Run all checks: lint, unit tests, and schema harness (CI parity)
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) test.schemas
	@$(MAKE) test.schemas.json
	@$(MAKE) test.determinism

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
.PHONY: lint-vocab format-vocab
lint-vocab:
	@poetry run python tests/vocab/lint_vocab.py

format-vocab:
	@poetry run python tests/vocab/format_vocab.py

# --- Rules validation and testing ---
.PHONY: rules.validate rules.test rules.check

rules.validate: ## Validate rules.json against rules.schema.json
	@poetry run pytest -q tests/rules/test_rules_doc.py::test_rules_schema_validates tests/rules/test_rules_doc.py::test_rule_ids_unique

rules.test: ## Run unit tests for rules examples
	@echo "Testing rules against examples..."
	@poetry run pytest -q tests/rules/test_rules_examples.py

rules.check: ## Run both rules validation and tests
	@$(MAKE) rules.validate
	@$(MAKE) rules.test
	@echo "✓ All rules checks passed"




# --- Synthetic Data Generators ---
.PHONY: data.generate generate.raw 


data.generate: ## Generate synthetic JSONL (per domain)
	@poetry run python3 data/generator/main.py -d agentic -n log_agentic
	@poetry run python3 data/generator/main.py -d cv -n log_cv
	@poetry run python3 data/generator/main.py -d api -n log_api
	@poetry run python3 data/generator/main.py -d llm -n log_llm

# 	@poetry run python3 data/generator/main.py -d $(Domain) -o $(Output_dir) -c $(Count) -f $(Fields) -s $(Seed) -n $(name) -args $(Arguments)
#  	@poetry run python3 data/generator/main.py -d $(Domain) -o $(Output_dir) -c $(Count)  -s $(Seed) -n $(name) -args $(Arguments)

data.generate.raw: ## Generate raw-line mirrors for round-trip tests
	@poetry run python3 data/generator/main.py -d agentic -n agentic --raw-mirror
	@poetry run python3 data/generator/main.py -d cv -n cv --raw-mirror
	@poetry run python3 data/generator/main.py -d api -n api  --raw-mirror
	@poetry run python3 data/generator/main.py -d llm -n llm --raw-mirror

# --- Round-trip test ---
.PHONY: test.roundtrip

test.roundtrip:
	@poetry run pytest -q data/generator/test_roundtrip.py
