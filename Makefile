.PHONY: help setup lint test generate classify down test.schemas test.schemas.json test.all demo.generate demo.run

help: ## Show available commands
	@echo "Common commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make lint        - run ruff lint locally (poetry run)"
	@echo "  make test        - run pytest locally (poetry run)"
	@echo "  make test.schemas - run JSON Schema test harness (writes JUnit XML)"
	@echo "  make test.schemas.json - run JSON Schema test harness (writes JSON)"
	@echo "  make test.all    - run all checks: lint + unit tests + schema harness (CI parity)"
	@echo ""
	@echo "Demo:"
	@echo "  make demo.generate - generate tiny demo schema/examples/raw inputs"
	@echo "  make demo.run    - generate demo and run the harness against it"
	@echo ""
	@echo "Pipeline:"
	@echo "  make generate    - create a sample log in local_pipeline/in"
	@echo "  make classify    - run docker-compose pipeline (in -> out)"
	@echo "  make down        - stop/cleanup docker-compose services"
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
	@poetry run pytest -q tests/generator/test_determinism.py

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
	@poetry run python3 data/generator/main.py -d $(Domain) -o $(Output_dir) -c $(Count) -f $(Fields) -s $(Seed) -n $(name) -args $(Arguments)
# 	@mkdir -p local_pipeline/in local_pipeline/out
# 	@date > local_pipeline/in/example.log
# 	@echo "hello, ulog" >> local_pipeline/in/example.log
# 	@echo "Wrote local_pipeline/in/example.log"

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
