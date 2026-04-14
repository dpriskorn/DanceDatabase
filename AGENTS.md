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

## Code Style

- Follow existing patterns in the codebase
- Use Pydantic for data models
- Use questionary for CLI prompts/interactions (NOT click)
- Add type hints where possible
- Keep functions small and focused
- No comments unless requested

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

## CLI Usage

All operations go through `cli.py`:

```bash
poetry run python cli.py --help
```

### DanceDB Workflow

#### Danslogen
```bash
# 1. Scrape venues with coordinates
poetry run python cli.py scrape-bygdegardarna

# 2. Scrape danslogen events
poetry run python cli.py scrape-danslogen -m april -y 2026

# 3. Match venues to DanceDB
poetry run python cli.py match-venues --skip-prompts

# 4. Upload events (prompts for each)
poetry run python cli.py upload-events --limit 10

# Or full workflow
poetry run python cli.py run-all --dry-run
```

#### Onbeat
```bash
poetry run python cli.py onbeat-scrape
poetry run python cli.py onbeat-ensure-venues
poetry run python cli.py onbeat-upload
```

#### Cogwork
```bash
poetry run python cli.py scrape-cogwork
poetry run python cli.py upload-cogwork
```

## Event Upload Flow

All uploads follow this pattern:
1. Parse events from source
2. For each event: print details
3. Prompt: Yes/Skip/Skip all/Abort
4. If confirmed → upload to DanceDB with WBI
5. Set properties: P1 (event), P5 (start), P6 (end), P7 (venue), P43 (status)

## Event Status Detection

Events are automatically scanned for cancellation status:
- Search terms: "inställt", "avbokat", "ställt in", "inställda"
- If found → status = Q567 (cancelled/inställt)
- Default → status = Q566 (planned/planerat)
- Logs INFO when cancelled detected

## Venue Matching (Legacy)

The venue matching workflow is handled automatically by the CLI. For reference:

### SPARQL for DanceDB
When querying DanceDB wikibase, use these prefixes:
```sparql
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?item ?itemLabel WHERE {
  ?item ddt:P1 dd:Q20 .  -- instance of venue
  OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
}
```

## DanceDB Properties

| Property | Description | Values |
|-----------|-------------|--------|
| P1 | Instance of | Q20 (venue), Q2 (event) |
| P4 | Coordinates | lat/lng |
| P5 | Start time | timestamp |
| P6 | End time | timestamp |
| P7 | Venue | venue QID |
| P43 | Status | Q566 (planned), Q567 (cancelled) |