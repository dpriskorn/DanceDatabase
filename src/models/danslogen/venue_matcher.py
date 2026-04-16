import logging
import sys
from typing import Optional

import questionary

import config
from src.models.dancedb.client import DancedbClient
from src.models.danslogen.fuzzy import fuzzy_match_qid
from src.models.danslogen.venue_mapper import VenueMapper
from src.utils.coords import parse_coords
from src.utils.venue_resolver import UnifiedVenueResolver, VenueSourceData

logger = logging.getLogger(__name__)


class VenueMatcher:
    """Resolves venue names to QIDs with coordinate matching.

    This class is now a compatibility wrapper around UnifiedVenueResolver.
    Raises KeyboardInterrupt on abort (user skips coords).
    """

    def __init__(
        self,
        client: Optional[DancedbClient] = None,
        byg_venues: Optional[dict[str, dict]] = None,
        folketshus_venues: Optional[dict[str, dict]] = None,
        db_venues: Optional[dict[str, dict]] = None,
        interactive: bool = True,
    ):
        self.client = client
        self.byg_venues = byg_venues or {}
        self.folketshus_venues = folketshus_venues or {}
        self.db_venues = db_venues or {}
        self.interactive = interactive
        self._venue_mapper = VenueMapper(client=client)
        self._resolver: Optional[UnifiedVenueResolver] = None

    def _get_resolver(self) -> UnifiedVenueResolver:
        if self._resolver is None:
            byg_list = list(self.byg_venues.values())
            folk_list = list(self.folketshus_venues.values())
            data = VenueSourceData(
                dancedb=self.db_venues,
                bygdegardarna=byg_list,
                folketshus=folk_list,
            )
            self._resolver = UnifiedVenueResolver(
                data=data,
                client=self.client,
                interactive=self.interactive,
            )
        return self._resolver

    def resolve(self, venue_name: str, ort: str = "") -> Optional[str]:
        """Resolve venue name to QID.

        Flow:
        1. Exact match against DanceDB venues (dynamic)
        2. Exact match against bygdegardarna
        3. Exact match against folketshus
        4. Fuzzy match against DanceDB venues
        5. Fuzzy match against bygdegardarna
        6. Fuzzy match against folketshus
        7. Create new venue if coords available (from bygdegardarna/folketshus or prompt)

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

        return self._get_resolver().resolve(venue_name, ort)