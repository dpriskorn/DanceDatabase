# ---- Validation script ----
import json
from pathlib import Path
from pydantic import ValidationError  # ✅ correct import (not from _pydantic_core)

from src.models.dance_event import DanceEvent

data_folder = Path("../data")

# ✅ include subfolders recursively and match json files correctly
json_files = list(data_folder.rglob("*.json"))

for file_path in json_files:
    print(f"Validating {file_path}...")
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # ✅ handle either a list or a single event object
        if isinstance(data, list):
            for i, item in enumerate(data, start=1):
                try:
                    DanceEvent(**item)
                except ValidationError as e:
                    print(f"❌ {file_path} (item #{i}) is invalid!")
                    print(e)
                    break
            else:
                print(f"✅ {file_path} (list of {len(data)}) is valid.")
        else:
            DanceEvent(**data)
            print(f"✅ {file_path} is valid.")

    except (ValidationError, json.JSONDecodeError) as e:
        print(f"❌ {file_path} is invalid!")
        print(e)
