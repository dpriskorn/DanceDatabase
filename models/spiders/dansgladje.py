import scrapy
import re
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
CET = timezone(timedelta(hours=1))


class Dansgladje(scrapy.Spider):
    name = "dansgladje_all_in_one"
    start_urls = ["https://dans.se/tools/calendar/?org=dansgladje&restrict=dansgladje"]

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return (
            text.replace("\xa0", " ")  # Unicode non-breaking space
            .replace(" ", " ")  # HTML entity
            .replace("\\n", "\n")
            .strip()
        )

    def parse(self, response):
        # Extract event URLs from the calendar
        event_links = response.css('table.calendar td.date a::attr(href)').getall()
        event_links += response.css('table.calendar td.headline a::attr(href)').getall()
        event_links = list(set(event_links))

        self.logger.info(f"Found {len(event_links)} event URLs")

        for url in event_links:
            yield scrapy.Request(url=url, callback=self.parse_event)

    def parse_event(self, response):
        label_sv = response.css("h1::text").get(default="").strip()

        ical_url = response.css("a.cwIconCal::attr(href)").get()
        if not ical_url:
            self.logger.warning(f"No iCal link found for {response.url}")
            return

        yield scrapy.Request(
            url=ical_url,
            callback=self.parse_ical,
            meta={"source_url": response.url, "label_sv": label_sv},
        )

    def parse_ical(self, response):
        text = response.text

        def get_value(key):
            pattern = rf"^{key}:(.*)$"
            m = re.search(pattern, text, re.MULTILINE)
            return m.group(1).strip() if m else ""

        dtstart = get_value("DTSTART")
        dtend = get_value("DTEND")
        location = get_value("LOCATION")
        description = get_value("DESCRIPTION")
        description_clean = self.clean_text(description)

        # Map to DanceDatabase venue QID
        venue_qid_map = {
            "Galaxy i Vallentuna": "Q19",
            "Sägnernas Hus": "Q21",
            "Sala Folkets Park": "Q22",
        }

        venue_qid = ""
        for key, qid in venue_qid_map.items():
            if key in description_clean:
                venue_qid = qid
                break

        def parse_ical_datetime(raw):
            if not raw:
                return None
            raw = raw.replace("\n", "").replace("\r", "").strip()
            fmt = "%Y%m%dT%H%M%S" if "T" in raw else "%Y%m%d"
            return datetime.strptime(raw, fmt).replace(tzinfo=CET)

        start_dt = parse_ical_datetime(dtstart)
        end_dt = parse_ical_datetime(dtend)

        event_id = response.url.split("id=")[-1]
        now = datetime.now().replace(microsecond=0).isoformat()

        event = {
            "id": event_id,  # modeled as P25 in DD
            "label": {"sv": self.clean_text(response.meta["label_sv"])},
            "description": {"sv": self.clean_text(description)},
            "coordinates": None,
            "schedule": {},
            "last_update": now,
            "start_time": start_dt.isoformat() if start_dt else None,
            "end_time": end_dt.isoformat() if end_dt else None,
            "registration_opens": None,
            "registration_closes": None,
            "organizer": {"description": "Dansglädje", "official_website": "https://dansgladje.nu"},
            "facebook_link": "",
            "official_website": response.meta["source_url"],
            "registration_website": "",
            "schedule_website": "",
            "venue_website": "",
            "location": location,
            "image": "",
            "price_early": "",
            "price_normal": "",
            "price_late": "",
            "cancelled": False,
            "fully_booked": False,
            "weekly_recurring": False,
            "identifiers": {
                "dancedatabase": {
                    "venue": venue_qid,
                    "dance_style": "Q23",
                    "organizer": "Q24"
                }
            }
        }

        # Save JSON file
        outdir = Path("data/events")
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / f"{event_id}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(event, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ Saved event {outfile}")
        yield event
