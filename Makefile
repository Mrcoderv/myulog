.PHONY: help setup lint test generate classify down

help: ## Show available commands
	@echo "Common commands:"
	@echo "  make setup       - install local dev tools (ruff, pytest) (optional)"
	@echo "  make lint        - run ruff lint locally"
	@echo "  make test        - run pytest locally"
	@echo "  make test.schemas - run JSON Schema test harness (two-phase flow)"
	@echo "  make generate    - create a sample log in local_pipeline/in"
	@echo "  make classify    - run docker-compose pipeline (in -> out)"
	@echo "  make down        - stop/cleanup docker-compose services"

setup: ## Install local tools (optional; CI installs its own)
	@python3 -m pip install --upgrade pip || true
	@pip3 install ruff pytest || true

lint: ## Lint with ruff
	@ruff check .

test: ## Run tests
	@pytest -q

test.schemas: ## Run JSON Schema test harness with two-phase flow (writes JUnit XML to tests/reports/)
	@poetry run python3 tests/harness/run_harness.py --format junit --output tests/reports/schema_results.xml

generate: ## Create a sample input file
	@mkdir -p local_pipeline/in local_pipeline/out
	@date > local_pipeline/in/example.log
	@echo "hello, ulog" >> local_pipeline/in/example.log
	@echo "Wrote local_pipeline/in/example.log"

classify: ## Run local pipeline (docker compose)
	@cd local_pipeline && docker compose up --build --abort-on-container-exit

down: ## Stop services and remove containers
	@cd local_pipeline && docker compose down --remove-orphans
