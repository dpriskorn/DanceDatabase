.PHONY: lint test coverage clean

lint:
	ruff check .
	black --check .
	mypy .
	isort --check .

test:
	pytest

coverage:
	coverage run -m pytest
	coverage report --include="src/**"