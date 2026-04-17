.PHONY: help lint test coverage clean check cli-help cli-commands sync-all sync-danslogen sync-bygdegardarna sync-onbeat sync-cogwork sync-folketshus

help:
	@echo "Available targets:"
	@echo "  lint             - Run ruff, black, isort"
	@echo "  test             - Run pytest"
	@echo "  coverage        - Run tests with coverage"
	@echo "  clean            - Remove cache files"
	@echo "  check            - Check DanceDB connection"
	@echo "  cli-help         - Show CLI help"
	@echo "  cli-commands    - List CLI commands"
	@echo "  sync-all         - Run full sync workflow"
	@echo "  sync-danslogen   - Sync danslogen events"
	@echo "  sync-bygdegardarna - Sync bygdegardarna venues"
	@echo "  sync-onbeat      - Sync onbeat events"
	@echo "  sync-cogwork    - Sync cogwork events"
	@echo "  sync-folketshus - Sync folketshus venues"

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check .

test:
	pytest

coverage:
	coverage run -m pytest
	coverage report --include="src/**"

check:
	poetry run python cli.py check-dancedb

cli-help:
	poetry run python cli.py --help

cli-commands:
	poetry run python cli.py -l

sync-all:
	poetry run python cli.py sync-all

sync-danslogen:
	poetry run python cli.py sync-danslogen

sync-bygdegardarna:
	poetry run python cli.py sync-bygdegardarna

sync-onbeat:
	poetry run python cli.py sync-onbeat

sync-cogwork:
	poetry run python cli.py sync-cogwork

sync-folketshus:
	poetry run python cli.py sync-folketshus