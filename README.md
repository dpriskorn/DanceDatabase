# Dance Database

For project vision, use cases, and goals, see [DANCE_DATABASE.md](./DANCE_DATABASE.md).

## Setup

```bash
poetry install
cp deprecated/config_sample.py config.py
# Edit config.py with your credentials
```

## CLI Usage

The main entry point is `cli.py`:

```bash
poetry run python cli.py --help
```

### Commands

| Command | Description |
|---------|-------------|
| `scrape-bygdegardarna` | Fetch venues with coordinates from bygdegardarna.se |
| `scrape-danslogen` | Fetch event rows from danslogen.se |
| `scrape-dancedb-venues` | Fetch existing venues from DanceDB |
| `match-venues` | Match bygdegardarna venues to DanceDB |
| `ensure-venues` | Ensure danslogen venues exist in DanceDB |
| `upload-events` | Upload danslogen events to DanceDB (+ confirmation) |
| `scrape-onbeat` | Fetch events from onbeat.dance |
| `upload-onbeat` | Upload onbeat events to DanceDB (+ confirmation) |
| `scrape-cogwork` | Fetch events from all cogwork sources |
| `upload-cogwork` | Upload cogwork events to DanceDB (+ confirmation) |
| `run-all` | Full workflow: scrape → match → upload |

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--date YYYY-MM-DD` | Date for venue matching | today |
| `--month MMMM` | Month name | april |
| `--year YYYY` | Year | 2026 |
| `--dry-run` | Preview only, no uploads | - |
| `--limit N` | Limit number of rows | - |
| `--skip-prompts` | Auto-match without prompts | - |

### Examples

```bash
# Full workflow (dry-run)
poetry run python cli.py run-all --dry-run

# Upload events (will prompt for each)
poetry run python cli.py upload-events --limit 10

# Venue matching
poetry run python cli.py scrape-bygdegardarna
poetry run python cli.py match-venues --skip-prompts
```

## Event Status Detection

Events are automatically scanned for cancellation status:
- Search terms: "inställt", "avbokat", "ställt in", "inställda"
- If found → status = Q567 (cancelled)
- Default → status = Q566 (planned)

## File Structure

```
cli.py                    # CLI entry point
config.py                # Configuration (credentials)
deprecated/             # Old scripts (kept for reference)
src/models/
├── dancedb/             # CLI modules
│   ├── config.py
│   ├── cli.py
│   ├── status.py         # Event status detection
│   ├── venue_ops.py
│   ├── event_ops.py
│   ├── onbeat_ops.py
│   └── cogwork_ops.py
├── danslogen/            # Danslogen modules
│   ├── data_loader.py
│   ├── venue_matcher.py
│   ├── band_mapper.py
│   ├── row_parser.py
│   └── uploader.py
├── cogwork/             # Cogwork scrapers
│   └── scrapers/
└── onbeat/              # Onbeat module
```

## Validate

```bash
poetry run make lint
poetry run make test
```

## License

All code is under GPLv3 and all data in `data/` is licensed CC0.