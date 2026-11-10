# Helper commands for the Garmin Home Assistant repository.
#
# The most important targets are:
#
#     make install     install the development tools
#     make test        run every test suite
#     make lint        run the linters and the type checker
#     make watch-check run the Connect IQ source checks
#     make image       build the container image of the bridge

PYTHON ?= python3
VENV ?= .venv
BRIDGE_VENV ?= $(VENV)
UV ?= uv

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(VENV):
	$(UV) venv $(VENV) --python 3.13

.PHONY: install
install: $(VENV) ## Install the development tools.
	$(UV) pip install --python $(VENV)/bin/python \
		"fastapi>=0.110" "uvicorn>=0.27" "aiohttp>=3.9" "pydantic>=2.6" \
		"pytest>=8.0" "pytest-asyncio>=0.23" "httpx>=0.27" "ruff>=0.4" "mypy>=1.10"

.PHONY: test
test: test-bridge test-ha ## Run every test suite.

.PHONY: test-bridge
test-bridge: ## Run the tests of the bridge.
	cd bridge && ../$(VENV)/bin/python -m pytest tests -q

.PHONY: test-ha
test-ha: ## Run the tests of the Home Assistant integration.
	$(VENV)/bin/python -m pytest custom_components/garmin_homeassistant/tests -q

.PHONY: lint
lint: ## Run the linters and the type checker.
	$(VENV)/bin/python -m ruff check bridge/src bridge/tests custom_components scripts
	$(VENV)/bin/python -m ruff format --check bridge/src bridge/tests custom_components scripts
	cd bridge && ../$(VENV)/bin/python -m mypy src
	$(VENV)/bin/python -m mypy custom_components scripts

.PHONY: format
format: ## Format the sources.
	$(VENV)/bin/python -m ruff format bridge/src bridge/tests custom_components scripts
	$(VENV)/bin/python -m ruff check --fix bridge/src bridge/tests custom_components scripts

.PHONY: watch-check
watch-check: ## Run the static checks of the Connect IQ sources.
	$(PYTHON) scripts/check_ciq.py

.PHONY: watch-icon
watch-icon: ## Regenerate the launcher icon of the watch app.
	$(PYTHON) watch/tools/make_launcher_icon.py

.PHONY: brand
brand: ## Regenerate the brand images.
	$(PYTHON) scripts/make_brand_icon.py

.PHONY: image
image: ## Build the container image of the bridge.
	docker build -t garmin-homeassistant-bridge:latest .

.PHONY: clean
clean: ## Remove the build artefacts.
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
