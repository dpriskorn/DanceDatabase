from typing import Optional

from bs4 import Tag
from pydantic import BaseModel, field_validator


class DanslogenArtistRow(BaseModel):
    name: str
    website: str = ""
    facebook: str = ""
    spelplan_id: str = ""

    @field_validator('name', mode='before')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @classmethod
    def from_row(cls, row: Tag) -> Optional['DanslogenArtistRow']:
        cells = row.find_all('td')
        if len(cells) < 4:
            return None

        name = cells[0].get_text(strip=True)
        if not name:
            return None

        website = cls._extract_link(cells[1]) if len(cells) > 1 else ""
        facebook = cls._extract_link(cells[2]) if len(cells) > 2 else ""
        spelplan_id = cls._extract_spelplan_id(cells[3]) if len(cells) > 3 else ""

        return cls(
            name=name,
            website=website,
            facebook=facebook,
            spelplan_id=spelplan_id,
        )

    @staticmethod
    def _extract_link(cell: Tag) -> str:
        a = cell.find('a')
        if a and a.get('href'):
            return a.get('href')
        return ""

    @staticmethod
    def _extract_spelplan_id(cell: Tag) -> str:
        a = cell.find('a')
        if a and a.get('href'):
            href = a.get('href')
            if '/dansband/spelplan/' in href:
                return href.split('/dansband/spelplan/')[-1]
        return ""