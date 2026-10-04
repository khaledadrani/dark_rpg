.DEFAULT_GOAL := help
.PHONY: install lint format typecheck test coverage coverage-gate check simulate run build clean help

install: ## Sync dev environment via uv
	uv sync --dev

lint: ## Ruff check (same scope as CI)
	uv run ruff check src tests scripts run.py

format: ## Ruff format -- NOT in CI/check yet (would reformat most files; needs its own reviewed commit)
	uv run ruff format src tests scripts run.py

typecheck: ## mypy over src/dark_rpg
	uv run mypy

test: ## pytest (unit + headless e2e/scenario tests)
	uv run pytest

coverage: ## True coverage: lines AND branches, missing lines shown (report only)
	uv run coverage run -m pytest; rc=$$?; uv run coverage report; exit $$rc

coverage-gate: ## Floor 70% total (fail_under) + changed code vs base needs >= 80% lines AND branches (base=<ref> to override)
	uv run coverage run -m pytest -q
	uv run coverage report --skip-covered
	uv run coverage json -q -o coverage.json
	uv run python scripts/diff_coverage.py --base $(or $(base),master) --min-lines 80 --min-branches 80

check: lint typecheck coverage-gate ## lint + typecheck + tests + coverage gates -- run this, not just pytest, before calling anything done

simulate: ## Balance simulation, both modes (compare win rates before/after combat changes)
	uv run python scripts/simulate.py --runs 200 --policy smart --all-modes

run: ## Play from the checkout
	uv run python run.py

build: ## Build wheel + sdist
	uv build

clean: ## Remove build/test artifacts
	rm -rf build dist .coverage coverage.json .pytest_cache .mypy_cache .ruff_cache

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-15s %s\n", $$1, $$2}'
