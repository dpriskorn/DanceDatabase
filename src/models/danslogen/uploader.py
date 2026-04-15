import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from src.models.dancedb.client import DancedbClient
from src.models.danslogen.band_mapper import BandMapper
from src.models.danslogen.data_loader import DanslogenDataLoader
from src.models.danslogen.row_parser import RowParser
from src.models.danslogen.venue_matcher import VenueMatcher

logger = logging.getLogger(__name__)


class DanslogenUploader:
    """Main orchestrator for uploading danslogen events to DanceDB."""

    def __init__(
        self,
        filename: str,
        date_str: Optional[str] = None,
        month: str = "april",
        limit: Optional[int] = None,
    ):
        self.filename = filename
        self.date_str = date_str or date.today().strftime("%Y-%m-%d")
        self.month = month
        self.limit = limit

        self.loader = DanslogenDataLoader()
        self.client: Optional[DancedbClient] = None

    def run(self, dry_run: bool = False) -> tuple[int, int, int]:
        """Run the upload process.

        Returns: tuple[processed, events_count, skipped]
        """
        if self.limit:
            print(f"(Limited to {self.limit} rows)")
        print(f"Processing rows from {self.filename}")

        if dry_run:
            print("DRY RUN - no changes will be made to DanceDB")

        byg_venues = self.loader.load_bygdegardarna_venues(self.date_str)
        db_venues = self.loader.load_dancedb_venues(self.date_str)
        print(f"Loaded {len(byg_venues)} bygdegardarna venues, {len(db_venues)} DanceDB venues")

        if not dry_run:
            self.client = DancedbClient()

        venue_matcher = VenueMatcher(
            client=self.client,
            byg_venues=byg_venues,
            db_venues=db_venues,
            interactive=not dry_run,
        )
        band_mapper = BandMapper(client=self.client)
        parser = RowParser(venue_matcher=venue_matcher, band_mapper=band_mapper)

        rows = self.loader.load_rows(self.filename)
        if not rows:
            print(f"Error: No rows loaded from {self.filename}")
            return 0, 0, 0

        print(f"Processing {len(rows)} rows from {self.filename}")

        if self.limit:
            rows = rows[:self.limit]
            print(f"(Limited to {self.limit} rows)")

        events = []
        skipped = 0

        for i, row in enumerate(rows):
            try:
                event = parser.parse(row, self.month)
                if event:
                    events.append(event)
                else:
                    skipped += 1
            except KeyboardInterrupt:
                print("\nAborted by user.")
                sys.exit(1)
            except Exception as e:
                logger.warning("Error processing row %d: %s", i, e)
                skipped += 1

            if (i + 1) % 50 == 0:
                print(f"Processed {i + 1}/{len(rows)} rows... "
                       f"{len(events)} events, {skipped} skipped")

        print(f"\nDone! Processed {len(rows)} rows -> {len(events)} events, {skipped} skipped")

        if events:
            output_file = Path(self.filename).with_suffix('.events.json')
            import json
            with open(output_file, 'w') as f:
                json.dump([e.model_dump(mode='json') for e in events], f,
                         ensure_ascii=False, indent=2)
            print(f"Wrote events to {output_file}")

        if dry_run:
            print("\nDry run complete. Run without --dry-run to upload.")

        return len(rows), len(events), skipped