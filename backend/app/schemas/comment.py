import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class CommentAuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class CommentRead(BaseModel):
    id: int
    author: CommentAuthorRead
    body: str
    created_at: dt.datetime
    status_change_from: str | None
    status_change_to: str | None
