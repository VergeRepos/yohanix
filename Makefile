.PHONY: setup run start stop test backtest check status install-service clean help

ifeq ($(OS),Windows_NT)
    PYTHON = .venv\Scripts\python.exe
    PYTEST = .venv\Scripts\pytest.exe
    UVICORN = .venv\Scripts\uvicorn.exe
else
    PYTHON = .venv/bin/python
    PYTEST = .venv/bin/pytest
    UVICORN = .venv/bin/uvicorn
endif

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up the project (venv, deps, config)
	@python stockpulse/utils/setup_helper.py

run: ## Run a one-shot scan
	@$(PYTHON) run.py scan

start: ## Start the scheduler (background scanning)
	@$(PYTHON) run.py schedule

stop: ## Stop the scheduler service
	@systemctl --user stop stockpulse 2>/dev/null || echo "Service not running"

test: ## Run the test suite
	@$(PYTEST) tests/ -v

backtest: ## Run a backtest (default: last 6 months)
	@$(PYTHON) run.py backtest

check: ## Validate your setup (API keys, connections)
	@$(PYTHON) -m stockpulse.utils.validate_setup

status: ## Show scheduler and service status
	@systemctl --user status stockpulse 2>/dev/null || echo "Service not installed."

api: ## Start the FastAPI backend on port 18000
	@$(UVICORN) stockpulse.api.server:app --host 0.0.0.0 --port 18000 --reload

ui: ## Start both backend and frontend
	@cd stockpulse-ui && npm run dev

clean: ## Remove outputs, cache, and generated files
	@python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('outputs').glob('*')]"
	@echo "Cleaned all outputs"

enter: ## Enter a position (usage: make enter TICKER=GOOGL)
	@$(PYTHON) run.py enter --ticker $(TICKER)
