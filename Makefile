.PHONY: lint test coverage clean

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check .

test:
	pytest

coverage:
	coverage run -m pytest
	coverage report --include="src/**"