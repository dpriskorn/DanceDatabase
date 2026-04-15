.PHONY: lint test coverage clean lint-fix

lint:
	ruff check .

lint-fix:
	ruff check . --fix

test:
	pytest

coverage:
	coverage run -m pytest
	coverage report --include="src/**"