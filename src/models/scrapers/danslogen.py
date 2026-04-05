import logging
import sys
from datetime import datetime
from typing import List, Optional

import click
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, AnyUrl, Field

sys.path.insert(0, str(__file__).rsplit('/', 1)[0] + '/../../')

import config
from config import CET
from src.models.dance_event import (
    DanceEvent,
    EventLinks,
    Identifiers,
    DanceDatabaseIdentifiers,
    Organizer,
    Registration,
)
from scripts.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)


class DanslogenEvent(BaseModel):
    organizer_qid: str = ""  # Danslogen is an aggregator, no QID
    band_qid_map: dict[str, str] = Field({
        "Allstars": "Q226",
        "Alvenfors": "Q227",
        "Ankies": "Q228",
        "Avant": "Q229",
        "BarraBazz": "Q230",
        "Black Jack": "Q231",
        "Blender": "Q232",
        "Blixterz": "Q233",
        "Boogart": "Q234",
        "Bottleneck John": "Q235",
        "Callinaz": "Q236",
        "Canyons": "Q237",
        "Casanovas": "Q238",
        "Danzerz": "Q239",
        "Date": "Q240",
        "Donaldz": "Q241",
        "Donnez": "Q242",
        "Eloge": "Q243",
        "Engdahls": "Q244",
        "Excess": "Q245",
        "Expanders": "Q246",
        "Extract": "Q247",
        "Fernandoz": "Q248",
        "Frippez": "Q249",
        "Gideons": "Q250",
        "Guns Rosor": "Q251",
        "Headline blues band": "Q252",
        "Hedenskogs": "Q253",
        "Hedins": "Q254",
        "Highlights": "Q255",
        "Högtryck": "Q256",
        "Holéns": "Q257",
        "Holidays": "Q258",
        "Hollyz": "Q259",
        "Jannes Svänggäng": "Q260",
        "Jannez": "Q261",
        "Jive": "Q262",
        "Junix": "Q263",
        "King Edwards Jr": "Q264",
        "Kjellez": "Q265",
        "Klackrent": "Q266",
        "Kollijox": "Q267",
        "Lars Erikssons": "Q268",
        "Larz-Kristerz": "Q269",
        "Lasse Stefanz": "Q270",
        "Leif Kronlunds orkester": "Q271",
        "Lövgrens": "Q272",
        "Martinez": "Q273",
        "Matz Bladhs": "Q274",
        "Matz Rogers": "Q275",
        "Micke Ahlgrens": "Q276",
        "Mickes": "Q277",
        "Ola & Jag": "Q278",
        "Pär Norlings": "Q279",
        "Perikles": "Q280",
        "PH:s": "Q281",
        "Playtones": "Q282",
        "Samzons": "Q283",
        "Sandbergs": "Q284",
        "Sandins": "Q285",
        "Sannex": "Q286",
        "Shake": "Q287",
        "Shine": "Q288",
        "Sounders": "Q289",
        "Streaplers": "Q290",
        "Thor Görans": "Q291",
        "Titanix": "Q292",
        "Tomas & co": "Q293",
        "Voize": "Q294",
        "Wahlströms": "Q295",
        "Xplays": "Q296",
    })
    venue_qid_map: dict[str, str] = Field({
        "Umeå Folkets Hus": "Q17",
        "Galaxy": "Q19",
        "Sägnernas Hus": "Q21",
        "Sala Folkets Park": "Q22",
        "7:ans mötesplats": "Q37",
        "Adventuremine Äventyrsgruvan": "Q38",
        "Aerobicsalen, Kristiansborgshallen": "Q39",
        "Alingsåsparken": "Q40",
        "Altorp": "Q41",
        "Alviks kulturhus Bromma": "Q42",
        "Arboga Folkets Park": "Q43",
        "Arbygården": "Q44",
        "Arena Rotebro": "Q45",
        "Åslidens dansloge": "Q46",
        "AYSE Holistiska HälsoHuset": "Q47",
        "Bällstabergsskolan": "Q48",
        "Barva": "Q49",
        "Bergnäsgården": "Q50",
        "Birkagården": "Q51",
        "Bistro at the Park": "Q52",
        "BokaNerja": "Q53",
        "Borensbergs Folkets Park": "Q54",
        "Borgen": "Q55",
        "Borghamn Strand": "Q56",
        "Bosön": "Q57",
        "Brännaberget": "Q58",
        "Bredsele Loge": "Q59",
        "Broby Dans": "Q60",
        "Brunna Danssportklubb": "Q61",
        "Brunnsparken": "Q62",
        "Brux AB": "Q63",
        "Bultgatan 18": "Q64",
        "Bygdens Danshöla": "Q65",
        "Ceylon": "Q66",
        "Chicago swing dance studio": "Q67",
        "DansAmore": "Q68",
        "Dansförening Boogie Lovers": "Q69",
        "Dansglada fötter Kiruna": "Q70",
        "Dansklubben Altira": "Q71",
        "Dansklubben Buggie": "Q72",
        "Dansklubben Glada Hudik": "Q73",
        "Dansklubben Klacken": "Q74",
        "Dansklubben Rock You 2": "Q75",
        "Dansklubben Spinnrockarna": "Q76",
        "DansRävarna": "Q77",
        "DuD Katrineholm": "Q78",
        "EBBA Dansklubb": "Q79",
        "Elite Stadshotellet Luleå": "Q80",
        "Englagård": "Q81",
        "Epic Studios": "Q82",
        "Ersboda Folkets Hus": "Q83",
        "Estraden Gävle": "Q84",
        "First Hotel Dragonen": "Q85",
        "Folkan Matfors": "Q86",
        "Folkets hus": "Q87",
        "Folkets Hus Alingsås": "Q88",
        "Folkets Hus Kusmark": "Q89",
        "Folkets hus Östersund": "Q90",
        "Folkparken Skellefteå": "Q91",
        "FTI Station": "Q92",
        "Furuparken": "Q93",
        "Fyris Park": "Q94",
        "Galejan": "Q95",
        "Gammlia dansbana": "Q96",
        "Garphyttans Folketspark": "Q97",
        "Gavlehovshallen": "Q98",
        "Gillestugan i Kyrkbyn": "Q99",
        "Gräsbergs Folkets Hus": "Q100",
        "Gräsmyr Loge": "Q101",
        "Gröna Lund": "Q102",
        "Gullvalla bygdegård": "Q103",
        "Hågelbyparken": "Q104",
        "Hallunda Folkets Hus": "Q105",
        "Hamboringens lokal sal 2": "Q106",
        "Haninge Kulturhus": "Q107",
        "Hantverkargatan 3K": "Q108",
        "Hemgården": "Q109",
        "Hjortnäs Brygga": "Q110",
        "Hjortvallen": "Q111",
        "Hockeyhallen i Hallsberg": "Q112",
        "Hörvik-Krokås Hembygdsförening": "Q113",
        "Hurmio": "Q114",
        "Innervik Byagård": "Q115",
        "Jakobsalen": "Q116",
        "Jakobsbergs folkhögskola": "Q117",
        "Jönköpings Roddsällskap": "Q118",
        "Karinhaaran kansantalo": "Q119",
        "Kärrasands Camping Urshult": "Q120",
        "KFUM Umeå": "Q121",
        "Klemensnäs Folkets Hus": "Q122",
        "Klossen, Folkuniversitetet": "Q123",
        "Knutby": "Q124",
        "Kühlers Dansskola": "Q125",
        "Kulturcentrum Ebeneser": "Q126",
        "Kulturfabriken NBV": "Q127",
        "Kulturföreningen DuD": "Q128",
        "Kulturhuset Bollnäs": "Q129",
        "Kulturhuset Möllan": "Q130",
        "Kulturhuset Stadsteatern": "Q131",
        "Kulturhuset Svanen i Borlänge": "Q132",
        "Kumla Folkets Hus": "Q133",
        "Kvarngården, Knivsta": "Q134",
        "Kvarnkullen": "Q135",
        "Kvarntorpsgården": "Q136",
        "Laduholmen": "Q137",
        "Las Playitas": "Q138",
        "Liljekonvaljeholmen": "Q139",
        "Lilltorpet": "Q140",
        "Limhamn Folkets Hus": "Q141",
        "Ljungsbro Folkets Park": "Q142",
        "Ljusdals Folkpark": "Q143",
        "Logen Käcktjärn": "Q144",
        "Lomma Dansrotunda": "Q145",
        "Lorry": "Q146",
        "Lövångergården": "Q147",
        "Lundegård Camping & Stugby": "Q148",
        "Lundgrens Loge": "Q149",
        "Mälarsalen": "Q150",
        "Malmö Dansakademi": "Q151",
        "Mannes Loge": "Q152",
        "Medborgarhus Måttsund": "Q153",
        "Midsommargården": "Q154",
        "Molidens dansbana": "Q155",
        "Mölndals Dansskola": "Q156",
        "Mörrum Folkets Hus o Park": "Q157",
        "Mötesplats Åker, Folkets Hus": "Q158",
        "Musköten": "Q159",
        "Nässjö Sportdansklubb": "Q160",
        "Nimbus dansklubb": "Q161",
        "Norra Ugglarps Bygdegård": "Q162",
        "Norrfjärdens Folketshus": "Q163",
        "Norrköpings Sportdansare": "Q164",
        "Nusnäs Bygdegård": "Q165",
        "Nyarpsstugan": "Q166",
        "Orbaden": "Q167",
        "Öresunds Dansförening": "Q168",
        "Orrskogen": "Q169",
        "Östnors Bygdegårdsförening": "Q170",
        "Parkhallen": "Q171",
        "Piteå Folketshusförening": "Q172",
        "Piteswänget": "Q173",
        "Quality Hotel Friends": "Q174",
        "Restaurang Seagram": "Q175",
        "Rockrullarna": "Q176",
        "Rönninge by": "Q177",
        "Rosendalsskolan södra": "Q178",
        "Rotan": "Q179",
        "Royal": "Q180",
        "Sägnernas hus": "Q181",
        "Säterdalen": "Q183",
        "Sinclairs Göteborg": "Q184",
        "Sjöstugan Almösund": "Q185",
        "Skälby loge": "Q186",
        "Skåvsjöholm konferens & möten": "Q187",
        "Skeer": "Q188",
        "Skepparholmen Nacka": "Q189",
        "Skultunalagårn": "Q190",
        "Sliperiet": "Q191",
        "Snäckan": "Q192",
        "Sockenstugan": "Q193",
        "Solvarbo Bystuga": "Q195",
        "Spegelsalen": "Q196",
        "Spekeröd Bygdegård": "Q197",
        "Sports Club Vallentuna": "Q198",
        "Sprallen": "Q199",
        "Stadsöskolans Aula": "Q200",
        "Stala Bygdegård": "Q201",
        "Stockholm Salsa Dance": "Q202",
        "Stockholm Tango": "Q203",
        "Stora Skuggans Dansbana": "Q204",
        "Storfors Folketshus": "Q205",
        "Strandpaviljongen Tällberg": "Q206",
        "Sundsvall Stadshus": "Q207",
        "Sunlight Hotel Conference & Spa": "Q208",
        "SVEA-Salen": "Q209",
        "Täfteå Logen": "Q210",
        "Tånga Heds Camping": "Q211",
        "Tansvallen": "Q212",
        "Tempelriddarsalen": "Q213",
        "Tofta Bygdegård": "Q214",
        "Träffen, Folketspark": "Q215",
        "Tyllsnäs Udde": "Q216",
        "U&ME Dance": "Q217",
        "Ulvsätra Loge": "Q218",
        "Umeå Dansimperium": "Q219",
        "Vallentuna Folkets Hus": "Q221",
        "Vallentuna Padel": "Q222",
        "Väsby Dansklubb": "Q223",
        "Vretstorp Folketspark": "Q224",
        "Hällesåkersgården": "Q487",
        "Matfors folkets hus": "Q488",
        "Danslogen på Norra berget": "Q489",
        "Quality Hotel Strawberry Arena": "Q490",
        "Fågelskolans Gymnastiksal B": "Q494",
        "Gåsalyckan": "Q495",
        "Johannesbergs slott": "Q504",
        "Trafikgatan 54": "Q505",
        "Vallsta bygdegård": "Q508",
        "Kulturhuset i Bollnäs": "Q509",
        "Byagården Runemo": "Q510",
        "Tonhallen": "Q511",
        "Tellushallen": "Q513",
        "Attarpshallen": "Q514",
        "Kulturhus tio14": "Q518",
        "Hälsans Hus": "Q519",
        "Gnistan Folkets Hus": "Q520",
        "Talavidskolan": "Q521",
        "Bollsta Folkets Hus": "Q522",
    })
    model_config = {"arbitrary_types_allowed": True}

    soup: Optional[BeautifulSoup] = None
    month: str = ""


class Danslogen:
    baseurl: str = "https://www.danslogen.se"
    event_class: type[DanslogenEvent] = DanslogenEvent

    def __init__(self, month: str = "april"):
        self.month = month.lower()
        self.events: List[DanceEvent] = []
        self.dancedb_client = DancedbClient()

    def fetch_month(self, month: str) -> None:
        url = f"{self.baseurl}/dansprogram/{month}"
        response = requests.get(url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched page: %s", url)

    def map_band_qid(self, band_name: str) -> Optional[str]:
        try:
            return next((qid for key, qid in self.event_class.band_qid_map.items()
                         if key.lower() == band_name.lower()), None)
        except Exception as e:
            logger.warning("Error looking up band '%s' in band_qid_map: %s", band_name, e)
            return None

    def map_venue_qid(self, venue_name: str) -> Optional[str]:
        return next((qid for key, qid in self.event_class.venue_qid_map.items()
                     if key.lower() in venue_name.lower()), None)

    def add_venue_qid(self, venue_name: str, qid: str) -> None:
        self.event_class.venue_qid_map[venue_name] = qid
        logger.info("Added venue mapping: %s -> %s", venue_name, qid)

    def parse_weekday_day(self, text: str) -> tuple[str, str]:
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return text, ""

    def parse_time_range(self, time_str: str) -> tuple[str, str]:
        if not time_str or time_str.strip() == "":
            return "", ""
        if "-" in time_str:
            start, end = time_str.split("-", 1)
            return start.strip(), end.strip()
        return time_str.strip(), ""

    def parse_date(self, day: str, month: str, year: int = 2026) -> Optional[datetime]:
        try:
            month_map = {
                "januari": 1, "februari": 2, "mars": 3, "april": 4,
                "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
                "september": 9, "oktober": 10, "november": 11, "december": 12
            }
            month_num = month_map.get(month.lower(), 1)
            return datetime.strptime(f"{year}-{month_num:02d}-{int(day):02d}", "%Y-%m-%d").replace(tzinfo=CET)
        except Exception as e:
            logger.warning("Failed to parse date %s %s: %s", day, month, e)
            return None

    def parse_row(self, row: Tag, month: str) -> Optional[DanceEvent]:
        cells = row.find_all("td")
        if len(cells) < 8:
            return None

        row_class = row.get("class") or []
        is_r7166 = "r7166" in row_class

        weekday_day = cells[0].get_text(strip=True)
        weekday, day = self.parse_weekday_day(weekday_day)

        time_text = cells[1].get_text(strip=True)
        start_time, end_time = self.parse_time_range(time_text)

        if is_r7166:
            band = cells[3].get_text(strip=True)
            venue = cells[5].get_text(strip=True) if cells[5].get_text(strip=True) else cells[6].get_text(strip=True)
            ort = cells[6].get_text(strip=True)
            kommun = cells[7].get_text(strip=True)
            lan = ""
            ovrigt = ""
        else:
            band = cells[3].get_text(strip=True)
            venue = cells[4].get_text(strip=True)
            ort = cells[5].get_text(strip=True)
            kommun = cells[6].get_text(strip=True)
            lan = cells[7].get_text(strip=True)
            ovrigt = cells[8].get_text(strip=True) if len(cells) > 8 else ""

        if not band or not band.strip():
            logger.debug("Skipping row with empty band")
            return None

        if not venue or not venue.strip():
            venue = ort

        band_qid = self.map_band_qid(band)
        if not band_qid:
            try:
                band_qid = self.dancedb_client.get_or_create_band(band)
            except (click.Abort, KeyboardInterrupt):
                logger.info("Aborted by user")
                raise
            except Exception as e:
                logger.warning("Could not get/create band '%s': %s. Skipping event.", band, e)
                return None
            if band_qid:
                self.event_class.band_qid_map[band] = band_qid
                logger.info("Added band mapping: %s -> %s", band, band_qid)

        venue_qid = self.map_venue_qid(venue)
        if not venue_qid:
            venue_full = f"{venue}, {ort}" if ort else venue
            try:
                new_qid = click.prompt(f"Unknown venue: '{venue_full}'\nEnter new QID for venue (or 'skip' to skip event)")
            except (click.Abort, KeyboardInterrupt):
                logger.info("Aborted by user")
                raise
            if new_qid.lower() == 'skip':
                logger.warning("Skipping event with unknown venue: %s", venue_full)
                return None
            venue_qid = new_qid
            self.event_class.venue_qid_map[venue] = venue_qid
            logger.info("Added venue mapping: %s -> %s", venue, venue_qid)

        date = self.parse_date(day, month)
        if not date:
            return None

        start_dt = None
        end_dt = None
        if date and start_time:
            try:
                start_dt = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
                if end_time:
                    end_dt = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            except Exception as e:
                logger.warning("Failed to parse datetime: %s", e)

        organizer = Organizer(
            description="Danslogen",
            official_website=f"{self.baseurl}/dansprogram/{month}",
        )

        event_id = f"danslogen-{month}-{day}-{band.lower().replace(' ', '-')}"

        dance_event = DanceEvent(
            id=event_id,
            label={"sv": f"{band} på {venue}"},
            description={"sv": ovrigt},
            location=venue,
            start_timestamp=start_dt,
            end_timestamp=end_dt,
            schedule={},
            price_normal=0,
            event_type="dance",
            price_reduced=None,
            links=EventLinks(
                official_website=AnyUrl(f"{self.baseurl}/dansprogram/{month}"),
                sources=[AnyUrl(f"{self.baseurl}/dansprogram/{month}")]
            ),
            organizer=organizer,
            registration=Registration(
                cancelled=False,
                fully_booked=False,
                registration_opens=None,
                registration_closes=None,
                advance_registration_required=False,
                registration_open=False
            ),
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    source="",
                    venue=venue_qid,
                    dance_styles=[],
                    event_series="",
                    organizer="",
                    event=""
                )
            ),
            last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
            price_late=None,
            price_early=None,
            coordinates=None,
            weekly_recurring=False,
            number_of_occasions=1
        )
        return dance_event

    def parse_month(self, month: str) -> List[DanceEvent]:
        self.fetch_month(month)
        events: List[DanceEvent] = []

        table = self.soup.find("table", class_="danceprogram")
        if not table:
            logger.warning("No danceprogram table found for month: %s", month)
            return events

        rows = table.select("tr[class^='r']")
        logger.info("Found %d rows for month %s", len(rows), month)

        for row in rows:
            try:
                event = self.parse_row(row, month)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning("Failed to parse row: %s (type: %s)", e, type(e).__name__)
                continue

        logger.info("Parsed %d events for %s", len(events), month)
        return events

    def scrape_month(self, month: str = "april") -> List[DanceEvent]:
        self.events = self.parse_month(month)
        return self.events


def scrape_month(month: str = "april") -> List[DanceEvent]:
    scraper = Danslogen(month)
    return scraper.scrape_month(month)
