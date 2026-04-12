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
- Use questionary for CLI prompts/interactions (NOT click)
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

## DanceDB Venue Matching Workflow

When adding a new venue scraper (e.g., bygdegardarna.se), follow this workflow:

### 1. Scrape venues
- `scrape_venues_from_dancedb.py` → fetches venue QIDs from DanceDB wikibase via SPARQL
- `data/dancedb/venues/YYYY-MM-DD.json` → DanceDB venues with labels + coordinates

### 2. Run scraper
- `python scrape_<source>.py` → fetches source venues
- `data/<source>/YYYY-MM-DD.json` → raw venue data

### 3. Match to DanceDB
- `python scrape_<source>_match.py --skip-prompts` → auto-match exact + fuzzy ≥85
- Without `--skip-prompts` → interactive prompts with questionary
- Output:
  - `data/<source>/enriched/YYYY-MM-DD.json` → matched venues with QIDs
  - `data/<source>/unmatched/YYYY-MM-DD.json` → unmatched for manual review

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

### Prompts
Use `questionary` for interactive prompts:
- `questionary.confirm("Accept match?").ask()` → yes/no
- `questionary.rawselect("Select:", choices=[...]).ask()` → menu selection
