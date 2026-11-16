"""Pydantic request/response shapes."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ContentHtml = Annotated[str, Field(max_length=2_000_000)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str


class DocSummary(BaseModel):
    id: int
    title: str
    owner: UserOut
    updated_at: datetime


class DocOut(DocSummary):
    content_html: str
    created_at: datetime
    is_owner: bool
    shared_with: list[UserOut]


class DocList(BaseModel):
    owned: list[DocSummary]
    shared: list[DocSummary]


class DocCreate(BaseModel):
    title: Title = "Untitled document"
    content_html: ContentHtml = ""


class DocUpdate(BaseModel):
    title: Title | None = None
    content_html: ContentHtml | None = None


class ShareIn(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=255)]
