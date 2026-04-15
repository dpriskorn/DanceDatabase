from pydantic import BaseModel


class DanslogenEvent(BaseModel):
    organizer_qid: str = ""
