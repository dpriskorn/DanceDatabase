.PHONY: lint test coverage clean check

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