import logging
import sys
from typing import Optional

import questionary

import config
from src.models.dancedb.client import DancedbClient
from src.models.danslogen.fuzzy import fuzzy_match_qid
from src.models.danslogen.venue_mapper import VenueMapper
from src.utils.coords import parse_coords

logger = logging.getLogger(__name__)


class VenueMatcher:
    """Resolves venue names to QIDs with coordinate matching.

    Raises KeyboardInterrupt on abort (user skips coords).
    """

    def __init__(
        self,
        client: Optional[DancedbClient] = None,
        byg_venues: Optional[dict[str, dict]] = None,
        db_venues: Optional[dict[str, dict]] = None,
        interactive: bool = True,
    ):
        self.client = client
        self.byg_venues = byg_venues or {}
        self.db_venues = db_venues or {}
        self.interactive = interactive
        self._venue_mapper = VenueMapper(client=client)

    def resolve(self, venue_name: str, ort: str = "") -> Optional[str]:
        """Resolve venue name to QID.

        Flow:
        1. Exact match against DanceDB venues (dynamic)
        2. Exact match against bygdegardarna
        3. Fuzzy match against DanceDB venues
        4. Fuzzy match against bygdegardarna
        5. Create new venue if coords available (from bygdegardarna or prompt)

        Returns QID or None if not found.
        Raises KeyboardInterrupt if user skips/aborts.
        """
        if not venue_name:
            venue_name = ort

        if not venue_name:
            return None

        qid = self._venue_mapper.resolve(venue_name)
        if qid:
            return qid

        qid = self._find_in_bygdegardarna(venue_name)
        if qid:
            return qid

        if self.client is None:
            return None

        return self._create_if_needed(venue_name, ort)

    def _find_in_bygdegardarna(self, venue_name: str) -> Optional[str]:
        """Find in bygdegardarna venues (exact or fuzzy)."""
        if not self.byg_venues:
            return None

        exact = next((v.get("qid") for title, v in self.byg_venues.items() if title.lower() == venue_name.lower() and v.get("qid")), None)
        if exact:
            return exact

        venues_with_qid = {v.get("title", ""): v.get("qid", "") for v in self.byg_venues.values() if v.get("qid")}
        fuzzy = fuzzy_match_qid(venue_name, venues_with_qid, remove_terms=config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA)
        if fuzzy:
            ff_warn = " ⚠️ FALSE FRIEND" if fuzzy.false_friend else ""
            logger.info("Fuzzy matched venue '%s' to bygdegardarna '%s' (cleaned='%s', %.1f%%)%s", venue_name, fuzzy.matched_label, fuzzy.cleaned_input, fuzzy.score, ff_warn)
            return fuzzy.qid

        return None

    def _create_if_needed(self, venue_name: str, ort: str) -> Optional[str]:
        """Create venue if coordinates available.

        Gets coords from bygdegardarna, or prompts user.
        If not interactive, returns None instead of prompting.
        """
        lat, lng = self._get_coords_from_bygdegardarna(venue_name)

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
            return None

        if not self.interactive:
            return None

        label = f"{venue_name}, {ort}" if ort else venue_name
        print(f'\nCreate venue: "{label}" at ({lat}, {lng})')

        confirm = questionary.rawselect("Upload to DanceDB?", choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]).ask()

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

    def _get_coords_from_bygdegardarna(self, venue_name: str) -> tuple[Optional[float], Optional[float]]:
        """Get coordinates from bygdegardarna for venue."""
        if not self.byg_venues:
            return None, None

        for title, v in self.byg_venues.items():
            if title.lower() == venue_name.lower():
                pos = v.get("position", {})
                return pos.get("lat"), pos.get("lng")

        return None, None
