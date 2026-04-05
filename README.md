# Dance Database

For project vision, use cases, and goals, see [DANCE_DATABASE.md](./DANCE_DATABASE.md).

## Setup

```bash
poetry install
cp config_sample.py config.py
# Edit config.py with your credentials
```

## Import Scripts

Scrapers for various dance event sources:

| Source | Script |
|--------|--------|
| Dansgladje | `src/models/scrapers/dansgladje.py` |
| BDK | `src/models/scrapers/bdk.py` |
| Altira | `src/models/scrapers/altira.py` |
| Forsfox | `src/models/scrapers/forsfox.py` |
| Fox Unlimited | `src/models/scrapers/foxunlimited.py` |
| Fox4u | `src/models/scrapers/fox4u.py` |
| Fmsab | `src/models/scrapers/fmsab.py` |
| Wannadance | `src/models/scrapers/wannadance.py` |
| Nimbusdk | `src/models/scrapers/nimbusdk.py` |
| Gasasteget | `src/models/scrapers/gasasteget.py` |
| Onbeat | `src/models/onbeat/organizers.py` |

Scripts in `scripts/` process data from Dancehaps.

## Running

```bash
poetry run python main.py
```

Output goes to `data/YYYYMMDD/` with JSON files per source.

## Validate

```bash
poetry run python validate_data.py
```

Validates all JSON files in `data/` against the schema.

## License

All code is under GPLv3 and all data in `data/` is licensed CC0.
