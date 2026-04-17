.PHONY: lint test coverage clean check cli-help cli-commands sync-all sync-danslogen sync-bygdegardarna sync-onbeat sync-cogwork sync-folketshus

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