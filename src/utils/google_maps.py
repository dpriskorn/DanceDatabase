from pydantic import ConfigDict, computed_field
from urllib.parse import quote

from src.models.base import DanceBaseModel


class GoogleMaps(DanceBaseModel):
    """Google Maps URL generator."""

    address: str = ""
    lat: float | None = None
    lng: float | None = None

    BASE_URL: str = "https://www.google.com/maps/search/"
    COORDS_URL: str = "https://www.google.com/maps/@"

    @computed_field
    @property
    def url(self) -> str:
        if self.lat is not None and self.lng is not None:
            return f"{self.COORDS_URL}{self.lat},{self.lng},15z"
        if self.address:
            return f"{self.BASE_URL}{quote(self.address)}"
        return ""

    model_config = ConfigDict(extra="forbid", frozen=True)