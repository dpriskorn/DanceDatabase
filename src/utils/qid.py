from pydantic import ConfigDict

from src.models.base import DanceBaseModel


class Qid(DanceBaseModel):
    """Represents a DanceDB wikibase entity ID with URL generation."""

    qid: str

    BASE_URL: str = "https://dance.wikibase.cloud"

    @property
    def url(self) -> str:
        return f"{self.BASE_URL}/wiki/Item:{self.qid}"

    model_config = ConfigDict(extra="forbid", frozen=True)