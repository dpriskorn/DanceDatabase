#!/usr/bin/env python3
"""Validate all JSON files in data/ against the DanceEvent schema."""

import json
import sys
from pathlib import Path

import jsonschema
import yaml


def load_schema():
    schema_path = Path(__file__).parent / "schema" / "dancedb-event-1.0.0.yml"
    with open(schema_path) as f:
        return yaml.safe_load(f)


def validate_file(file_path: Path, schema: dict) -> tuple[bool, str]:
    """Validate a single JSON file against schema. Returns (is_valid, message)."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for i, item in enumerate(data, start=1):
                try:
                    jsonschema.validate(item, schema)
                except jsonschema.ValidationError as e:
                    return False, f"Item #{i}: {e.message}"
            return True, f"Valid list of {len(data)} events"
        else:
            try:
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                return False, f"Validation error: {e.message}"
            return True, "Valid single event"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    schema = load_schema()
    data_dirs = sorted(Path("data").glob("*"))
    all_valid = True
    total_files = 0

    for data_dir in data_dirs:
        if not data_dir.is_dir():
            continue
        print(f"\n=== {data_dir.name} ===")
        json_files = sorted(data_dir.glob("*.json"))
        if not json_files:
            print("  No JSON files found")
            continue

        for json_file in json_files:
            total_files += 1
            is_valid, msg = validate_file(json_file, schema)
            if is_valid:
                print(f"  [OK] {json_file.name}: {msg}")
            else:
                print(f"  [FAIL] {json_file.name}: {msg}")
                all_valid = False

    print(f"\n=== Summary ===")
    print(f"Total files checked: {total_files}")
    if all_valid:
        print("All files are valid!")
        sys.exit(0)
    else:
        print("Some files have issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()
