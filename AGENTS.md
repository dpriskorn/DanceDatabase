# Agent Guidelines

## Coverage Requirements

**Target: 95% code coverage for all Python source files**

When modifying Python code:
1. Run coverage checks: `coverage run -m pytest && coverage report --include="src/**"`
2. If coverage drops below 95%, add tests to improve coverage
3. Focus on covering:
   - New functionality added
   - Error handling paths
   - Edge cases
   - Utility methods

All files must maintain 95%+ coverage at all times.

When modifying Python code:
1. Run coverage checks: `coverage run -m pytest && coverage report --include="src/**"`
2. If coverage drops below 80%, add tests to improve coverage
3. Focus on covering:
   - New functionality added
   - Error handling paths
   - Edge cases
   - Utility methods

## Code Style

- Follow existing patterns in the codebase
- Use Pydantic for data models
- Use Click for CLI prompts/interactions
- Add type hints where possible
- Keep functions small and focused

## Testing

- Tests go in `tests/` directory
- Use `pytest` framework
- Use `unittest.mock.patch` for mocking
- Name test methods: `test_<method>_<scenario>`

## Commit Messages

Use conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `test:` for test changes
- `docs:` for documentation
- `chore:` for maintenance
