from typing import Literal

from pydantic import BaseModel

SearchResultType = Literal["activity", "milestone", "team", "tag", "user"]


class SearchResult(BaseModel):
    type: SearchResultType
    id: int
    label: str
    subtitle: str | None = None
