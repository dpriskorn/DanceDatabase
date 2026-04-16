from pydantic import BaseModel


class Qid(BaseModel):
    """Represents a DanceDB wikibase entity ID with URL generation."""

    qid: str

    BASE_URL: str = "https://dance.wikibase.cloud"

    @property
    def url(self) -> str:
        return f"{self.BASE_URL}/wiki/Item:{self.qid}"

    model_config = {"frozen": True}