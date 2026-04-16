import json
import logging
import sys
from pathlib import Path
from typing import Optional

import questionary

import config
from src.models.dancedb.client import DancedbClient
from src.utils.coords import parse_coords
from src.utils.fuzzy import is_false_fuzzy_match, normalize_for_fuzzy
from src.utils.fuzzy_models import FuzzyMatchResultQid
from src.utils.geodb import get_ship_coordinates
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class VenueSourceData:
    """Container for venue data from different sources."""

    def __init__(
        self,
        dancedb: Optional[dict[str, dict]] = None,
        bygdegardarna: Optional[list[dict]] = None,
        folketshus: Optional[list[dict]] = None,
    ):
        self.dancedb = dancedb or {}
        self.bygdegardarna = bygdegardarna or []
        self.folketshus = folketshus or []


class UnifiedVenueResolver:
    """Unified venue resolver combining DanceDB, Bygdegardarna, and Folketshus.

    Resolution flow:
    1. Exact match against DanceDB venues
    2. Exact match against bygdegardarna
    3. Exact match against folketshus
    4. Fuzzy match against DanceDB venues
    5. Fuzzy match against bygdegardarna
    6. Fuzzy match against folketshus
    7. Create new venue if coords available (interactive mode only)

    Usage:
        resolver = UnifiedVenueResolver(data_dir="data")
        qid = resolver.resolve("Stora Gatan 5", ort="Umeå")

        # Or with custom data:
        resolver = UnifiedVenueResolver(
            data=data,
            client=client,
            interactive=True
        )
    """

    def __init__(
        self,
        data_dir: str = "data",
        data: Optional[VenueSourceData] = None,
        client: Optional[DancedbClient] = None,
        interactive: bool = True,
    ):
        self.data_dir = Path(data_dir)
        self._data = data
        self.client = client
        self.interactive = interactive

    def _ensure_data_loaded(self) -> VenueSourceData:
        if self._data is not None:
            return self._data

        self._data = VenueSourceData(
            dancedb=self._load_dancedb_venues(),
            bygdegardarna=self._load_bygdegardarna_venues(),
            folketshus=self._load_folketshus_venues(),
        )
        return self._data

    def _load_dancedb_venues(self) -> dict[str, dict]:
        """Load venues from local DanceDB JSON cache."""
        venues_file = self.data_dir / "dancedb/venues"
        if not venues_file.exists():
            return {}

        latest = sorted(venues_file.glob("*.json"), reverse=True)
        if not latest:
            return {}

        venues = json.loads(latest[0].read_text())
        logger.info(f"Loaded {len(venues)} venues from DanceDB cache ({latest[0].name})")
        return venues

    def _load_bygdegardarna_venues(self) -> list[dict]:
        """Load venues from Bygdegardarna JSON."""
        bygdegard_file = self.data_dir / "bygdegardarna"
        if not bygdegard_file.exists():
            return []

        latest = sorted(bygdegard_file.glob("*.json"), reverse=True)
        if not latest:
            return []

        venues = json.loads(latest[0].read_text())
        logger.info(f"Loaded {len(venues)} venues from Bygdegardarna ({latest[0].name})")
        return venues

    def _load_folketshus_venues(self) -> list[dict]:
        """Load venues from Folketshus enriched JSON."""
        folketshus_file = self.data_dir / "folketshus/enriched"
        if not folketshus_file.exists():
            return []

        latest = sorted(folketshus_file.glob("*.json"), reverse=True)
        if not latest:
            return []

        venues = json.loads(latest[0].read_text())
        logger.info(f"Loaded {len(venues)} venues from Folketshus ({latest[0].name})")
        return venues

    def resolve(self, venue_name: str, ort: str = "") -> Optional[str]:
        """Resolve venue name to QID.

        Returns QID or None if not found.
        Raises KeyboardInterrupt if user skips/aborts in interactive mode.
        """
        if not venue_name:
            venue_name = ort
        if not venue_name:
            return None

        data = self._ensure_data_loaded()

        qid = self._exact_match_dancedb(venue_name, data)
        if qid:
            return qid

        qid = self._exact_match_bygdegardarna(venue_name, data)
        if qid:
            return qid

        qid = self._exact_match_folketshus(venue_name, data)
        if qid:
            return qid

        if self.client is None:
            return None

        qid = self._fuzzy_match_dancedb(venue_name, data)
        if qid:
            return qid

        qid = self._fuzzy_match_bygdegardarna(venue_name, data)
        if qid:
            return qid

        qid = self._fuzzy_match_folketshus(venue_name, data)
        if qid:
            return qid

        return self._create_if_needed(venue_name, ort, data)

    def _exact_match_dancedb(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Exact match against DanceDB venues."""
        if not data.dancedb:
            return None

        venue_lower = venue_name.lower()
        for qid, v in data.dancedb.items():
            label = v.get("label", "").lower()
            if venue_lower == label:
                logger.debug("Exact match DanceDB: '%s' -> %s", venue_name, qid)
                return qid
            for alias in v.get("aliases", []):
                if venue_lower == alias.lower():
                    logger.debug("Exact match DanceDB alias: '%s' -> %s", venue_name, qid)
                    return qid
        return None

    def _exact_match_bygdegardarna(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Exact match against bygdegardarna venues."""
        if not data.bygdegardarna:
            return None

        venue_lower = venue_name.lower()
        for v in data.bygdegardarna:
            title = v.get("title", "").lower()
            if venue_lower == title:
                qid = v.get("qid")
                if qid:
                    logger.debug("Exact match bygdegardarna: '%s' -> %s", venue_name, qid)
                    return qid
        return None

    def _exact_match_folketshus(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Exact match against folketshus venues."""
        if not data.folketshus:
            return None

        venue_lower = venue_name.lower()
        for v in data.folketshus:
            name = v.get("name", "").lower()
            if venue_lower == name:
                qid = v.get("qid")
                if qid:
                    logger.debug("Exact match folketshus: '%s' -> %s", venue_name, qid)
                    return qid
        return None

    def _fuzzy_match_dancedb(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Fuzzy match against DanceDB venues."""
        if not data.dancedb:
            return None

        qid_map = {v.get("label", ""): qid for qid, v in data.dancedb.items() if v.get("label")}
        result = self._do_fuzzy_match(venue_name, qid_map, config.FUZZY_REMOVE_TERMS_DANSLOGEN)
        if result:
            logger.info(
                "Fuzzy matched venue '%s' to DanceDB '%s' (cleaned='%s', %.1f%%)%s",
                venue_name, result.matched_label, result.cleaned_input, result.score,
                " ⚠️ FALSE FRIEND" if result.false_friend else "",
            )
            return result.qid
        return None

    def _fuzzy_match_bygdegardarna(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Fuzzy match against bygdegardarna venues."""
        if not data.bygdegardarna:
            return None

        qid_map = {v.get("title", ""): v.get("qid", "") for v in data.bygdegardarna if v.get("title") and v.get("qid")}
        result = self._do_fuzzy_match(venue_name, qid_map, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA)
        if result:
            logger.info(
                "Fuzzy matched venue '%s' to bygdegardarna '%s' (cleaned='%s', %.1f%%)%s",
                venue_name, result.matched_label, result.cleaned_input, result.score,
                " ⚠️ FALSE FRIEND" if result.false_friend else "",
            )
            return result.qid
        return None

    def _fuzzy_match_folketshus(self, venue_name: str, data: VenueSourceData) -> Optional[str]:
        """Fuzzy match against folketshus venues."""
        if not data.folketshus:
            return None

        qid_map = {v.get("name", ""): v.get("qid", "") for v in data.folketshus if v.get("name") and v.get("qid")}
        result = self._do_fuzzy_match(venue_name, qid_map, config.FUZZY_REMOVE_TERMS_FOLKETSHUS)
        if result:
            logger.info(
                "Fuzzy matched venue '%s' to folketshus '%s' (cleaned='%s', %.1f%%)%s",
                venue_name, result.matched_label, result.cleaned_input, result.score,
                " ⚠️ FALSE FRIEND" if result.false_friend else "",
            )
            return result.qid
        return None

    def _do_fuzzy_match(
        self, venue_name: str, qid_map: dict[str, str], remove_terms: list[str]
    ) -> Optional[FuzzyMatchResultQid]:
        """Perform fuzzy matching using token_set_ratio."""
        threshold = config.FUZZY_THRESHOLD_VENUE_DANSLOGEN
        if not venue_name:
            return None

        normalized_input = normalize_for_fuzzy(venue_name, remove_terms)
        normalized_map = {normalize_for_fuzzy(k, remove_terms): (k, qid) for k, qid in qid_map.items()}

        result = process.extractOne(normalized_input, normalized_map.keys(), scorer=fuzz.token_set_ratio)
        if result and result[1] >= threshold:
            original_key = normalized_map[result[0]][0]
            cleaned_label = result[0]
            false_friend = is_false_fuzzy_match(normalized_input, cleaned_label, remove_terms)
            return FuzzyMatchResultQid(
                matched_label=original_key,
                qid=qid_map[original_key],
                score=result[1],
                cleaned_input=normalized_input,
                false_friend=false_friend,
            )
        return None

    def _create_if_needed(self, venue_name: str, ort: str, data: VenueSourceData) -> Optional[str]:
        """Create venue if coordinates available.

        Gets coords from bygdegardarna/folketshus, or prompts user.
        If not interactive, returns None instead of prompting.
        """
        lat, lng = self._get_coords_bygdegardarna(venue_name, data)
        if lat is None or lng is None:
            lat, lng = self._get_coords_folketshus(venue_name, data)

        if lat is None or lng is None:
            if not self.interactive:
                return None

            venue_full = f"{venue_name}, {ort}" if ort else venue_name
            try:
                coord_str = questionary.text(f"Enter coordinates for '{venue_full}' (lat,lng or 'skip' to abort)").ask()
            except KeyboardInterrupt:
                raise KeyboardInterrupt()

            if coord_str.lower() == "skip":
                logger.error("Aborting: venue '%s' requires coordinates", venue_full)
                raise KeyboardInterrupt()

            if coord_str:
                coords = parse_coords(coord_str)
                if coords:
                    lat = coords["lat"]
                    lng = coords["lng"]
                else:
                    logger.error("Invalid coordinate format '%s'", coord_str)
                    raise KeyboardInterrupt()

        if lat is None or lng is None:
            ship_coords = get_ship_coordinates(venue_name)
            if ship_coords:
                lat = ship_coords["lat"]
                lng = ship_coords["lng"]
                logger.info("Matched '%s' to ship pattern, using default coordinates", venue_name)

        if lat is None or lng is None:
            return None

        if not self.interactive:
            return None

        label = f"{venue_name}, {ort}" if ort else venue_name
        print(f'\nCreate venue: "{label}" at ({lat}, {lng})')

        confirm = questionary.select("Upload to DanceDB?", choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]).ask()

        if confirm == "Skip":
            logger.info("Skipping venue '%s'", label)
            return None
        elif confirm == "Skip all":
            logger.info("Skipping all remaining venues...")
            return "SKIP_ALL"
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            qid = self.client.create_venue_from_mapping(venue_name, ort, lat, lng)
            if qid:
                logger.info("Created venue '%s' -> %s", venue_name, qid)
                print(f"Uploaded: https://dance.wikibase.cloud/wiki/Item:{qid}")
            return qid
        except Exception as e:
            logger.error("Could not create venue '%s': %s", venue_name, e)
            raise

    def _get_coords_bygdegardarna(self, venue_name: str, data: VenueSourceData) -> tuple[Optional[float], Optional[float]]:
        """Get coordinates from bygdegardarna for venue."""
        if not data.bygdegardarna:
            return None, None

        venue_lower = venue_name.lower()
        for v in data.bygdegardarna:
            if v.get("title", "").lower() == venue_lower:
                pos = v.get("position", {})
                return pos.get("lat"), pos.get("lng")
        return None, None

    def _get_coords_folketshus(self, venue_name: str, data: VenueSourceData) -> tuple[Optional[float], Optional[float]]:
        """Get coordinates from folketshus for venue."""
        if not data.folketshus:
            return None, None

        venue_lower = venue_name.lower()
        for v in data.folketshus:
            if v.get("name", "").lower() == venue_lower:
                lat = v.get("lat")
                lng = v.get("lng")
                if lat and lng:
                    return lat, lng
        return None, None
