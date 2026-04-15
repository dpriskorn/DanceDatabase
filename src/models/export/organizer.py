import json
from pathlib import Path

from pydantic import BaseModel


class Organizer(BaseModel):
    json_output_folder: Path

    # === Export ===
    def export_to_json(self):
        from datetime import date

        Path(self.json_output_folder).mkdir(parents=True, exist_ok=True)
        today_str = date.today().strftime("%Y-%m-%d")
        file_path = Path(self.json_output_folder) / f"{today_str}.json"
        # Convert each Pydantic model to a plain dict
        data = [event.model_dump(mode="json") for event in self.events]

        # Serialize to JSON (Pydantic already handles datetimes nicely)
        json_data = json.dumps(data, indent=2, ensure_ascii=False)

        file_path.write_text(json_data, encoding="utf-8")
        print(f"Exported {len(self.events)} events to {file_path}")
