import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CMSWindowBase(BaseModel):
    slot_id: str | None = Field(None, max_length=50)
    slug: str = Field(..., min_length=2, max_length=160)
    title: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, max_length=80)
    summary: str = Field(..., min_length=5)
    problem: str | None = None
    solution: str | None = None
    metrics: list[Any] = Field(default_factory=list)
    tags: list[Any] = Field(default_factory=list)
    is_published: bool = True


class CMSWindowCreate(CMSWindowBase):
    model_config = ConfigDict(extra="ignore")


class CMSWindowUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slot_id: str | None = None
    slug: str | None = Field(None, min_length=2, max_length=160)
    title: str | None = Field(None, min_length=2, max_length=200)
    category: str | None = Field(None, min_length=2, max_length=80)
    summary: str | None = Field(None, min_length=5)
    problem: str | None = None
    solution: str | None = None
    metrics: list[Any] | None = None
    tags: list[Any] | None = None
    is_published: bool | None = None


class CMSWindowResponse(CMSWindowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    updated_at: datetime
