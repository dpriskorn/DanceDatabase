import logging
from typing import Optional

import questionary
from rapidfuzz import fuzz, process

from src.models.dancedb_client import DancedbClient
from src.models.danslogen.maps import VENUE_QID_MAP, fuzzy_match_qid

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85


class VenueMatcher:
    """Resolves venue names to QIDs with coordinate matching.

    Raises KeyboardInterrupt on abort (user skips coords).
    """

    def __init__(
        self,
        client: Optional[DancedbClient] = None,
        byg_venues: Optional[dict[str, dict]] = None,
        db_venues: Optional[dict[str, dict]] = None,
    ):
        self.client = client
        self.byg_venues = byg_venues or {}
        self.db_venues = db_venues or {}

    def resolve(self, venue_name: str, ort: str = "") -> Optional[str]:
        """Resolve venue name to QID.

        Flow:
        1. Exact match against static map
        2. Fuzzy match against static map
        3. Exact match against bygdegardarna
        4. Fuzzy match against bygdegardarna
        5. Exact match against DanceDB venues
        6. Fuzzy match against DanceDB venues
        7. Create new venue if coords available (from bygdegardarna or prompt)

        Returns QID or None if not found.
        Raises KeyboardInterrupt if user skips/aborts.
        """
        if not venue_name:
            venue_name = ort

        if not venue_name:
            return None

        qid = self._find_in_static_map(venue_name)
        if qid:
            return qid

        qid = self._find_in_bygdegardarna(venue_name)
        if qid:
            return qid

        qid = self._find_in_dancedb(venue_name)
        if qid:
            return qid

        if self.client is None:
            return None

        return self._create_if_needed(venue_name, ort)

    def _find_in_static_map(self, venue_name: str) -> Optional[str]:
        """Find in static map (exact or fuzzy)."""
        exact = next(
            (qid for key, qid in VENUE_QID_MAP.items()
             if key.lower() == venue_name.lower()),
            None
        )
        if exact:
            return exact

        fuzzy = fuzzy_match_qid(venue_name, VENUE_QID_MAP)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.info("Fuzzy matched venue '%s' to '%s' (score=%d)", venue_name, matched_key, score)
            return qid

        return None

    def _find_in_bygdegardarna(self, venue_name: str) -> Optional[str]:
        """Find in bygdegardarna venues (exact or fuzzy)."""
        if not self.byg_venues:
            return None

        exact = next(
            (v.get("qid") for title, v in self.byg_venues.items()
             if title.lower() == venue_name.lower() and v.get("qid")),
            None
        )
        if exact:
            return exact

        venues_with_qid = {v.get("title", ""): v.get("qid", "")
                     for v in self.byg_venues.values() if v.get("qid")}
        fuzzy = fuzzy_match_qid(venue_name, venues_with_qid)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.info("Fuzzy matched venue '%s' to bygdegardarna '%s' (score=%d)",
                     venue_name, matched_key, score)
            return qid

        return None

    def _find_in_dancedb(self, venue_name: str) -> Optional[str]:
        """Find in DanceDB venues (exact or fuzzy)."""
        if not self.db_venues:
            return None

        exact = next(
            (qid for qid, data in self.db_venues.items()
             if data.get("label", "").lower() == venue_name.lower()),
            None
        )
        if exact:
            return exact

        labels = {data.get("label", ""): qid for qid, data in self.db_venues.items()}
        fuzzy = fuzzy_match_qid(venue_name, labels)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.info("Fuzzy matched venue '%s' to DanceDB '%s' (score=%d)",
                     venue_name, matched_key, score)
            return qid

        return None

    def _create_if_needed(self, venue_name: str, ort: str) -> Optional[str]:
        """Create venue if coordinates available.

        Gets coords from bygdegardarna, or prompts user.
        Aborts if no coords available.
        """
        lat, lng = self._get_coords_from_bygdegardarna(venue_name)

        if lat is None or lng is None:
            venue_full = f"{venue_name}, {ort}" if ort else venue_name
            try:
                coord_str = questionary.text(
                    f"Enter coordinates for '{venue_full}' (lat,lng or 'skip' to abort)"
                ).ask()
            except KeyboardInterrupt:
                raise KeyboardInterrupt()

            if coord_str.lower() == 'skip':
                logger.error("Aborting: venue '%s' requires coordinates", venue_full)
                raise KeyboardInterrupt()

            if coord_str:
                try:
                    parts = [p.strip() for p in coord_str.split(',')]
                    lat = float(parts[0])
                    lng = float(parts[1])
                except (ValueError, IndexError) as e:
                    logger.error("Invalid coordinate format '%s': %s", coord_str, e)
                    raise KeyboardInterrupt()

        if lat is None or lng is None:
            return None

        try:
            qid = self.client.create_venue_from_mapping(venue_name, ort, lat, lng)
            if qid:
                logger.info("Created venue '%s' -> %s", venue_name, qid)
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