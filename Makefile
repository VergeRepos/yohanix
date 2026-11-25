.PHONY: setup all run start stop test backtest check status install-service clean help

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
	@python3 stockpulse/utils/setup_helper.py 2>/dev/null || python stockpulse/utils/setup_helper.py 2>/dev/null || python3.12 stockpulse/utils/setup_helper.py

all: setup ## Complete automated setup (Python venv + Node UI deps)
	@if [ -d stockpulse-ui ]; then \
		echo "Installing UI dependencies (npm install)..."; \
		cd stockpulse-ui && npm install; \
	fi
	@echo "Yohanix setup complete!"

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

install-service: ## Install system service (systemd or Gentoo OpenRC init script)
	@if [ -d /run/systemd/system ]; then \
		echo "Installing systemd user service..."; \
		mkdir -p ~/.config/systemd/user; \
		echo "[Unit]" > ~/.config/systemd/user/yohanix.service; \
		echo "Description=Yohanix Market Intelligence" >> ~/.config/systemd/user/yohanix.service; \
		echo "[Service]" >> ~/.config/systemd/user/yohanix.service; \
		echo "ExecStart=$$(pwd)/$(PYTHON) run.py schedule" >> ~/.config/systemd/user/yohanix.service; \
		echo "Restart=always" >> ~/.config/systemd/user/yohanix.service; \
		echo "[Install]" >> ~/.config/systemd/user/yohanix.service; \
		echo "WantedBy=default.target" >> ~/.config/systemd/user/yohanix.service; \
		systemctl --user daemon-reload; \
		systemctl --user enable yohanix; \
		echo "Systemd user service installed and enabled."; \
	elif command -v rc-service >/dev/null 2>&1 || [ -d /etc/init.d ]; then \
		echo "Gentoo OpenRC environment detected."; \
		echo "Creating OpenRC init script template (yohanix.initd)..."; \
		echo '#!/sbin/openrc-run' > yohanix.initd; \
		echo 'description="Yohanix Market Intelligence Scheduler"' >> yohanix.initd; \
		echo 'pidfile="/run/yohanix.pid"' >> yohanix.initd; \
		echo 'command="$$(pwd)/$(PYTHON)"' >> yohanix.initd; \
		echo 'command_args="run.py schedule"' >> yohanix.initd; \
		echo 'directory="$$(pwd)"' >> yohanix.initd; \
		echo 'command_background="true"' >> yohanix.initd; \
		echo 'depend() { need net; }' >> yohanix.initd; \
		chmod +x yohanix.initd; \
		echo "OpenRC service template created at ./yohanix.initd."; \
		echo "To install on Gentoo: sudo cp yohanix.initd /etc/init.d/yohanix && sudo rc-update add yohanix default"; \
	else \
		echo "Linux init system not matched automatically. Use 'make start' to run scheduler."; \
	fi

api: ## Start the FastAPI backend on port 18000
	@$(UVICORN) stockpulse.api.server:app --host 0.0.0.0 --port 18000 --reload --reload-dir stockpulse

ui: ## Start both backend and frontend
	@cd stockpulse-ui && npm run dev

clean: ## Remove outputs, cache, and generated files
	@python3 -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('outputs').glob('*')]" 2>/dev/null || python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('outputs').glob('*')]"
	@echo "Cleaned all outputs"

enter: ## Enter a position (usage: make enter TICKER=GOOGL)
	@$(PYTHON) run.py enter --ticker $(TICKER)
